from django.shortcuts import render

# Create your views here.
from .models import *
from .serializers import *
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from accounts.models import User


class EventCreateView(generics.CreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventCreationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if not self.request.user.paystack_subaccount_code:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                {"detail": "You must complete bank account onboarding before creating an event."}
            )
        event = serializer.save(created_by=self.request.user)
        EventRole.objects.create(user=self.request.user, event=event, role='ORGANIZER')

class AddStaffView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id, user_id):
        event = get_object_or_404(Event, id=event_id)
        # Check if request.user is organizer
        if not EventRole.objects.filter(user=request.user, event=event, role='ORGANIZER').exists():
            return Response({"error": "Only the organizer can add staff."}, status=status.HTTP_403_FORBIDDEN)
        
        user_to_add = get_object_or_404(User, id=user_id)
        # Check if already has a role
        if EventRole.objects.filter(user=user_to_add, event=event).exists():
            return Response({"error": "User already has a role in this event."}, status=status.HTTP_400_BAD_REQUEST)
        
        EventRole.objects.create(user=user_to_add, event=event, role='STAFF')
        return Response({"message": "Staff added successfully."}, status=status.HTTP_201_CREATED)


class RemoveStaffView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, event_id, user_id):
        event = get_object_or_404(Event, id=event_id)
        # Check if request.user is organizer
        if not EventRole.objects.filter(user=request.user, event=event, role='ORGANIZER').exists():
            return Response({"error": "Only the organizer can remove staff."}, status=status.HTTP_403_FORBIDDEN)
        
        user_to_remove = get_object_or_404(User, id=user_id)
        role = get_object_or_404(EventRole, user=user_to_remove, event=event, role='STAFF')
        role.delete()
        return Response({"message": "Staff removed successfully."}, status=status.HTTP_204_NO_CONTENT)
class EventStaffView(generics.ListAPIView):
    serializer_class = EventRoleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        event_id = self.kwargs['event_id']
        event = get_object_or_404(Event, id=event_id)
        return EventRole.objects.filter(event=event, role__in=['STAFF', 'ORGANIZER'])