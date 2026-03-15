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