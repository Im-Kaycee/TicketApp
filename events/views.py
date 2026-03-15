from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction

from accounts.models import User
from .models import Event, EventRole, TicketType
from .serializers import *
from django.db.models import Sum, Count
from django.utils import timezone
from tickets.models import Ticket, Order, CheckInLog

class EventCreateView(generics.CreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventCreationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if not self.request.user.paystack_subaccount_code:
            raise PermissionDenied(
                "You must complete bank account onboarding before creating an event."
            )
        event = serializer.save(created_by=self.request.user)
        EventRole.objects.create(
            user=self.request.user, event=event, role="ORGANIZER"
        )


class AddTicketTypeView(APIView):
    """
    POST /events/<event_id>/ticket-types/
    Organizer adds multiple ticket tiers to their event in one request.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)

        if not EventRole.objects.filter(
            user=request.user, event=event, role="ORGANIZER"
        ).exists():
            raise PermissionDenied("Only the organizer can add ticket types.")

        serializer = BulkTicketTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ticket_types_data = serializer.validated_data["ticket_types"]

        # Check for name conflicts with existing ticket types on this event
        existing_names = set(
            event.ticket_types.values_list("name", flat=True)
        )
        incoming_names = {tt["name"] for tt in ticket_types_data}
        conflicts = existing_names & incoming_names

        if conflicts:
            raise PermissionDenied(
                f"Ticket type(s) already exist for this event: {', '.join(conflicts)}"
            )

        with transaction.atomic():
            created = TicketType.objects.bulk_create([
                TicketType(
                    event=event,
                    name=tt["name"],
                    price=tt["price"],
                    quantity=tt["quantity"],
                )
                for tt in ticket_types_data
            ])

        return Response(
            TicketTypeSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class AddStaffView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id, user_id):
        event = get_object_or_404(Event, id=event_id)
        if not EventRole.objects.filter(
            user=request.user, event=event, role="ORGANIZER"
        ).exists():
            return Response(
                {"error": "Only the organizer can add staff."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user_to_add = get_object_or_404(User, id=user_id)
        if EventRole.objects.filter(user=user_to_add, event=event).exists():
            return Response(
                {"error": "User already has a role in this event."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        EventRole.objects.create(user=user_to_add, event=event, role="STAFF")
        return Response(
            {"message": "Staff added successfully."}, status=status.HTTP_201_CREATED
        )


class RemoveStaffView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, event_id, user_id):
        event = get_object_or_404(Event, id=event_id)
        if not EventRole.objects.filter(
            user=request.user, event=event, role="ORGANIZER"
        ).exists():
            return Response(
                {"error": "Only the organizer can remove staff."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user_to_remove = get_object_or_404(User, id=user_id)
        role = get_object_or_404(
            EventRole, user=user_to_remove, event=event, role="STAFF"
        )
        role.delete()
        return Response(
            {"message": "Staff removed successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


class EventStaffView(generics.ListAPIView):
    serializer_class = EventRoleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        event_id = self.kwargs["event_id"]
        event = get_object_or_404(Event, id=event_id)
        return EventRole.objects.filter(event=event, role__in=["STAFF", "ORGANIZER"])
    
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.utils import timezone


class EventPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class EventDiscoveryView(generics.ListAPIView):
    """
    GET /events/
    Public endpoint. Browse and search events with filters.

    Query params:
        search        — searches title and description
        event_type    — ONLINE or OFFLINE
        date_from     — ISO date string e.g. 2026-12-01
        date_to       — ISO date string e.g. 2026-12-31
        price_min     — minimum ticket price
        price_max     — maximum ticket price
        available     — true to only show events with tickets remaining
        page          — page number
        page_size     — results per page (max 100, default 20)
    """
    serializer_class = EventDiscoverySerializer
    permission_classes = []
    pagination_class = EventPagination

    def get_queryset(self):
        params = self.request.query_params
        now = timezone.now()

        queryset = (
            Event.objects.filter(event_date__gte=now)
            .prefetch_related("ticket_types")
            .order_by("event_date")
        )

        # Search
        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        # Event type filter
        event_type = params.get("event_type", "").upper()
        if event_type in ("ONLINE", "OFFLINE"):
            queryset = queryset.filter(event_type=event_type)

        # Date range filter
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if date_from:
            queryset = queryset.filter(event_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(event_date__date__lte=date_to)

        # Price range filter — filter by ticket type prices
        price_min = params.get("price_min")
        price_max = params.get("price_max")
        if price_min:
            queryset = queryset.filter(ticket_types__price__gte=price_min)
        if price_max:
            queryset = queryset.filter(ticket_types__price__lte=price_max)

        # Availability filter — only show events with tickets remaining
        available = params.get("available", "").lower()
        if available == "true":
            queryset = [e for e in queryset if e.capacity > 0 and any(
                tt.available() > 0 for tt in e.ticket_types.all()
            )]

        return queryset

class EventDashboardMixin:
    """
    Shared helper to get event and verify organizer access.
    """
    def get_event_and_assert_organizer(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        if not EventRole.objects.filter(
            user=request.user, event=event, role="ORGANIZER"
        ).exists():
            raise PermissionDenied("Only the organizer can view this dashboard.")
        return event

    def get_date_filters(self, request):
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        filters = {}
        if date_from:
            filters["created_at__date__gte"] = date_from
        if date_to:
            filters["created_at__date__lte"] = date_to
        return filters


class EventDashboardSummaryView(EventDashboardMixin, APIView):
    """
    GET /events/<event_id>/dashboard/summary/
    Total sold, net revenue, attendance rate.
    Organizer only.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = self.get_event_and_assert_organizer(request, event_id)
        date_filters = self.get_date_filters(request)

        orders = Order.objects.filter(
            event=event,
            status=Order.Status.COMPLETED,
            **date_filters,
        )

        total_tickets_sold = orders.aggregate(
            total=Sum("quantity")
        )["total"] or 0

        gross_revenue = orders.aggregate(
            total=Sum("total_price")
        )["total"] or 0

        net_revenue = gross_revenue * (1 - event.platform_fee_percent / 100)

        total_checked_in = Ticket.objects.filter(
            event=event,
            status=Ticket.Status.CHECKED_IN,
        ).count()

        attendance_rate = (
            round((total_checked_in / total_tickets_sold) * 100, 2)
            if total_tickets_sold > 0
            else 0
        )

        return Response({
            "event": event.title,
            "total_tickets_sold": total_tickets_sold,
            "gross_revenue": gross_revenue,
            "net_revenue": round(net_revenue, 2),
            "platform_fee_percent": event.platform_fee_percent,
            "total_checked_in": total_checked_in,
            "attendance_rate": f"{attendance_rate}%",
            "capacity": event.capacity,
        })


class EventDashboardTicketTypesView(EventDashboardMixin, APIView):
    """
    GET /events/<event_id>/dashboard/ticket-types/
    Sold and remaining per tier.
    Organizer only.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = self.get_event_and_assert_organizer(request, event_id)

        ticket_types = event.ticket_types.all()
        data = []

        for tt in ticket_types:
            sold = tt.sold_count()
            available = tt.available()
            gross = tt.price * sold
            net = gross * (1 - event.platform_fee_percent / 100)

            data.append({
                "id": tt.id,
                "name": tt.name,
                "price": tt.price,
                "quantity": tt.quantity,
                "sold": sold,
                "available": available,
                "gross_revenue": gross,
                "net_revenue": round(net, 2),
            })

        return Response(data)


class EventDashboardOrdersView(EventDashboardMixin, APIView):
    """
    GET /events/<event_id>/dashboard/orders/
    Recent orders with buyer details.
    Supports date range filtering.
    Organizer only.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = EventPagination

    def get(self, request, event_id):
        event = self.get_event_and_assert_organizer(request, event_id)
        date_filters = self.get_date_filters(request)

        orders = (
            Order.objects.filter(
                event=event,
                status=Order.Status.COMPLETED,
                **date_filters,
            )
            .select_related("buyer", "ticket_type")
            .order_by("-created_at")
        )

        data = []
        for order in orders:
            net = order.total_price * (1 - event.platform_fee_percent / 100)
            data.append({
                "order_id": str(order.id),
                "buyer_name": order.buyer.get_full_name() or order.buyer.username,
                "buyer_email": order.buyer.email,
                "ticket_type": order.ticket_type.name if order.ticket_type else "N/A",
                "quantity": order.quantity,
                "total_paid": order.total_price,
                "net_earnings": round(net, 2),
                "purchased_at": order.created_at,
            })

        # Paginate
        paginator = EventPagination()
        page = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(page)


class EventDashboardAttendanceView(APIView):
    """
    GET /events/<event_id>/dashboard/attendance/
    Check-in stats and recent scans.
    Organizer and staff.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)

        # Allow organizer or staff
        has_access = EventRole.objects.filter(
            user=request.user,
            event=event,
            role__in=["ORGANIZER", "STAFF"],
        ).exists()

        if not has_access:
            raise PermissionDenied("You do not have access to this event's attendance.")

        total_sold = Ticket.objects.filter(
            event=event,
            status__in=[
                Ticket.Status.VALID,
                Ticket.Status.CHECKED_IN,
                Ticket.Status.LISTED_FOR_SALE,
            ],
        ).count()

        total_checked_in = Ticket.objects.filter(
            event=event,
            status=Ticket.Status.CHECKED_IN,
        ).count()

        remaining = total_sold - total_checked_in

        attendance_rate = (
            round((total_checked_in / total_sold) * 100, 2)
            if total_sold > 0
            else 0
        )

        recent_checkins = (
            CheckInLog.objects.filter(ticket__event=event)
            .select_related("ticket__owner", "ticket__ticket_type", "scanned_by")
            .order_by("-scanned_at")[:20]
        )

        checkin_data = [
            {
                "ticket_id": str(log.ticket.id),
                "owner_name": log.ticket.owner.get_full_name() or log.ticket.owner.username,
                "owner_email": log.ticket.owner.email,
                "ticket_type": log.ticket.ticket_type.name if log.ticket.ticket_type else "N/A",
                "scanned_by": log.scanned_by.username,
                "scanned_at": log.scanned_at,
            }
            for log in recent_checkins
        ]

        return Response({
            "total_sold": total_sold,
            "total_checked_in": total_checked_in,
            "remaining": remaining,
            "attendance_rate": f"{attendance_rate}%",
            "recent_checkins": checkin_data,
        })


class OrganizerOverviewView(EventDashboardMixin, APIView):
    """
    GET /events/dashboard/overview/
    Totals across all organizer's events.
    Supports date range filtering.
    Organizer only.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_filters = self.get_date_filters(request)

        # Get all events this user organizes
        organized_event_ids = EventRole.objects.filter(
            user=request.user,
            role="ORGANIZER",
        ).values_list("event_id", flat=True)

        events = Event.objects.filter(id__in=organized_event_ids)

        orders = Order.objects.filter(
            event__in=events,
            status=Order.Status.COMPLETED,
            **date_filters,
        ).select_related("event")

        total_tickets_sold = orders.aggregate(
            total=Sum("quantity")
        )["total"] or 0

        total_events = events.count()

        # Net revenue per event (each event may have different platform fee)
        total_net_revenue = sum(
            float(order.total_price) * (1 - float(order.event.platform_fee_percent) / 100)
            for order in orders
        )

        total_checked_in = Ticket.objects.filter(
            event__in=events,
            status=Ticket.Status.CHECKED_IN,
        ).count()

        # Per event breakdown
        event_breakdown = []
        for event in events:
            event_orders = orders.filter(event=event)
            event_gross = event_orders.aggregate(
                total=Sum("total_price")
            )["total"] or 0
            event_net = float(event_gross) * (
                1 - float(event.platform_fee_percent) / 100
            )
            event_sold = event_orders.aggregate(
                total=Sum("quantity")
            )["total"] or 0

            event_breakdown.append({
                "event_id": event.id,
                "event_title": event.title,
                "event_date": event.event_date,
                "tickets_sold": event_sold,
                "net_revenue": round(event_net, 2),
            })

        return Response({
            "total_events": total_events,
            "total_tickets_sold": total_tickets_sold,
            "total_net_revenue": round(total_net_revenue, 2),
            "total_checked_in": total_checked_in,
            "events": event_breakdown,
        })