import hashlib
import hmac
import json

from datetime import timedelta

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CheckInLog, Order, Ticket
from .qr import verify_qr_signature
from .serializers import (
    OrderSerializer,
    PurchaseInputSerializer,
    TicketSerializer,
    VerifyTicketSerializer,
)
from .services import (
    CapacityExceededError,
    InvalidQuantityError,
    complete_purchase,
    initiate_purchase,
)


class PurchaseTicketsView(APIView):
    """
    POST /tickets/purchase/
    Creates a PENDING order and returns a Paystack payment URL.
    Tickets are not generated until payment is confirmed via webhook.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PurchaseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from events.models import Event
        event = get_object_or_404(Event, pk=serializer.validated_data["event_id"])

        if not event.created_by.paystack_subaccount_code:
            return Response(
                {"detail": "This event is not available for purchase yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order, payment_url = initiate_purchase(
                user=request.user,
                event=event,
                quantity=serializer.validated_data["quantity"],
            )
        except CapacityExceededError as exc:
            raise ValidationError({"detail": str(exc)})
        except InvalidQuantityError as exc:
            raise ValidationError({"detail": str(exc)})

        return Response(
            {"order_id": str(order.id), "payment_url": payment_url},
            status=status.HTTP_201_CREATED,
        )


class MyTicketsView(APIView):
    """
    GET /tickets/my-tickets/
    Returns all tickets owned by the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tickets = (
            Ticket.objects.filter(owner=request.user)
            .select_related("event")
            .order_by("-created_at")
        )
        return Response(TicketSerializer(tickets, many=True).data)


class TicketDetailView(APIView):
    """
    GET /tickets/<ticket_id>/
    Returns a single ticket. Only the owner can view it.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        ticket = get_object_or_404(
            Ticket.objects.select_related("event", "owner"), pk=ticket_id
        )
        if ticket.owner != request.user:
            raise PermissionDenied("You do not own this ticket.")
        return Response(TicketSerializer(ticket).data)


class VerifyTicketView(APIView):
    """
    GET /tickets/verify/<ticket_id>?sig=<signature>
    Public endpoint that QR codes point to.
    Validates the signature and confirms the ticket is valid for entry.
    """
    permission_classes = []

    def get(self, request, ticket_id):
        ticket = get_object_or_404(
            Ticket.objects.select_related("event", "owner"), pk=ticket_id
        )

        provided_sig = request.query_params.get("sig", "")
        if not verify_qr_signature(str(ticket.id), provided_sig):
            return Response(
                {"detail": "Invalid QR signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_end = ticket.event.event_date + timedelta(hours=ticket.event.duration_hours)
        if timezone.now() > event_end:
            return Response(
                {"detail": "This event has ended."},
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

        data = {
            "ticket_id": str(ticket.id),
            "owner": ticket.owner.email,
            "event": ticket.event.title,
            "status": ticket.status,
            "signature_valid": True,
        }
        return Response(VerifyTicketSerializer(data).data)


class CheckInView(APIView):
    """
    POST /tickets/<ticket_id>/checkin/
    Staff or organizer checks in a ticket at the event.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        ticket = get_object_or_404(
            Ticket.objects.select_related("event"), pk=ticket_id
        )

        event_end = ticket.event.event_date + timedelta(hours=ticket.event.duration_hours)
        if timezone.now() > event_end:
            return Response(
                {"detail": "This event has ended."},
                status=status.HTTP_400_BAD_REQUEST,
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
        if user.is_staff:
            return
        from events.models import EventRole
        has_role = EventRole.objects.filter(
            event=event,
            user=user,
            role__in=["STAFF", "ORGANIZER"],
        ).exists()
        if not has_role:
            raise PermissionDenied("You are not staff or organizer for this event.")


@method_decorator(csrf_exempt, name="dispatch")
class PaystackWebhookView(APIView):
    """
    POST /tickets/payment/webhook/
    Paystack calls this after a payment succeeds.
    Verifies the signature, confirms the transaction, then generates tickets.
    """
    permission_classes = []

    def post(self, request):
        # Confirm the request is genuinely from Paystack
        paystack_signature = request.headers.get("x-paystack-signature", "")
        computed = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode(),
            request.body,
            hashlib.sha512,
        ).hexdigest()

        if not hmac.compare_digest(computed, paystack_signature):
            return Response({"detail": "Invalid signature."}, status=400)

        payload = json.loads(request.body)
        event_type = payload.get("event")

        if event_type != "charge.success":
            # Acknowledge but ignore other event types
            return Response(status=200)

        reference = payload["data"]["reference"]

        # Always verify independently — never trust the webhook payload alone
        from .paystack import verify_transaction
        transaction_data = verify_transaction(reference)

        if transaction_data["status"] != "success":
            return Response(status=200)

        try:
            order = Order.objects.get(id=reference, status=Order.Status.PENDING)
        except Order.DoesNotExist:
            # Already processed or doesn't exist — acknowledge and move on
            return Response(status=200)

        complete_purchase(order=order)
        return Response(status=200)