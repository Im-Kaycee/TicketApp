from rest_framework import serializers
from .models import *
from accounts.models import User
class EventCreationSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.username', read_only=True)
    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'venue', 'event_date', 'capacity', 'created_by']
        read_only_fields = ['id', 'created_by']

class EventRoleSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)
    event = serializers.CharField(source='event.title', read_only=True)
    class Meta:
        model = EventRole
        fields = ['id', 'user', 'event', 'role', 'assigned_at']
        read_only_fields = ['id', 'user', 'event', 'assigned_at']