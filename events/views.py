from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction

from accounts.models import User
from .models import Event, EventRole, TicketType
from .serializers import (
    BulkTicketTypeSerializer,
    EventCreationSerializer,
    EventRoleSerializer,
    TicketTypeSerializer,
)


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