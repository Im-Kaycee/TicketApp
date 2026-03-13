from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CheckInLog, Ticket
from .qr import verify_qr_signature
from .serializers import (
    OrderSerializer,
    PurchaseInputSerializer,
    TicketSerializer,
    VerifyTicketSerializer,
)
from .services import CapacityExceededError, InvalidQuantityError, purchase_tickets
from django.utils import timezone
from datetime import timedelta


# ---------------------------------------------------------------------------
# POST /tickets/purchase
# ---------------------------------------------------------------------------

class PurchaseTicketsView(APIView):
    """
    Create an order and generate tickets for an event.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PurchaseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from events.models import Event  

        event = get_object_or_404(Event, pk=serializer.validated_data["event_id"])
        quantity = serializer.validated_data["quantity"]

        try:
            order = purchase_tickets(user=request.user, event=event, quantity=quantity)
        except CapacityExceededError as exc:
            raise ValidationError({"detail": str(exc)})
        except InvalidQuantityError as exc:
            raise ValidationError({"detail": str(exc)})

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# GET /tickets/my-tickets
# ---------------------------------------------------------------------------

class MyTicketsView(APIView):
    """
    List all tickets owned by the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tickets = (
            Ticket.objects.filter(owner=request.user)
            .select_related("event")
            .order_by("-created_at")
        )
        if not tickets.exists():
            return Response({"detail": "You have no tickets."}, status=status.HTTP_404_NOT_FOUND)
        return Response(TicketSerializer(tickets, many=True).data)
    


# ---------------------------------------------------------------------------
# GET /tickets/<ticket_id>
# ---------------------------------------------------------------------------

class TicketDetailView(APIView):
    """
    Retrieve a single ticket. Only the owner may view it.
    The QR code should be rendered client-side from id + qr_signature.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        ticket = get_object_or_404(
            Ticket.objects.select_related("event", "owner"), pk=ticket_id
        )
        if ticket.owner != request.user:
            raise PermissionDenied("You do not own this ticket.")

        return Response(TicketSerializer(ticket).data)


# ---------------------------------------------------------------------------
# GET /tickets/verify/<ticket_id>?sig=<signature>
# ---------------------------------------------------------------------------

class VerifyTicketView(APIView):
    """
    Public endpoint — QR codes open this URL.
    Validates the signature but does NOT check the ticket in.
    Check-in is a separate staff action.
    """

    def get(self, request, ticket_id):
        ticket = get_object_or_404(
            Ticket.objects.select_related("event", "owner"), pk=ticket_id
        )

        provided_sig = request.query_params.get("sig", "")
        sig_valid = verify_qr_signature(str(ticket.id), provided_sig)

        if not sig_valid:
            return Response(
                {"detail": "Invalid QR signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ticket.status in (Ticket.Status.CHECKED_IN, Ticket.Status.CANCELLED):
            return Response(
                {
                    "detail": f"Ticket is {ticket.status} and cannot be used for entry.",
                    "ticket_id": str(ticket.id),
                    "status": ticket.status,
                },
                status=status.HTTP_409_CONFLICT,
            )
        event_end = ticket.event.event_date + timedelta(hours=ticket.event.duration_hours)
        if timezone.now() > event_end:
            return Response(
                {"detail": "This event has ended."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = {
            "ticket_id": str(ticket.id),
            "owner": ticket.owner.email,
            "event": ticket.event.title,
            "status": ticket.status,
            "signature_valid": sig_valid,
        }
        return Response(VerifyTicketSerializer(data).data)


# ---------------------------------------------------------------------------
# POST /tickets/<ticket_id>/checkin
# ---------------------------------------------------------------------------

class CheckInView(APIView):
    """
    Staff/organizer presses Check In after scanning a QR code.
    Requires the user to be STAFF or ORGANIZER on the event.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        ticket = get_object_or_404(
            Ticket.objects.select_related("event"), pk=ticket_id
        )

        self._assert_can_check_in(request.user, ticket.event)

        if ticket.status == Ticket.Status.CHECKED_IN:
            return Response(
                {"detail": "Ticket has already been checked in."},
                status=status.HTTP_409_CONFLICT,
            )

        if ticket.status == Ticket.Status.CANCELLED:
            return Response(
                {"detail": "Cannot check in a cancelled ticket."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        event_end = ticket.event.event_date + timedelta(hours=ticket.event.duration_hours)
        if timezone.now() > event_end:
            return Response(
                {"detail": "This event has ended."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ticket.status = Ticket.Status.CHECKED_IN
        ticket.save(update_fields=["status"])

        CheckInLog.objects.create(ticket=ticket, scanned_by=request.user)

        return Response(
            {
                "detail": "Checked in successfully.",
                "ticket_id": str(ticket.id),
                "event": ticket.event.title,
            }
        )

    @staticmethod
    def _assert_can_check_in(user, event):
        """
        Verify that `user` is staff or organizer for `event`.
        Adjust the role lookup to match your events app's model.
        """
        
        if user.is_staff:
            return
        try:
            from events.models import EventRole  # noqa: PLC0415

            has_role = EventRole.objects.filter(
                event=event,
                user=user,
                role__in=["STAFF", "ORGANIZER"],
            ).exists()
        except ImportError:
            has_role = False

        if not has_role:
            raise PermissionDenied("You are not staff or organizer for this event.")