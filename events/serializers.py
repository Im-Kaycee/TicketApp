from rest_framework import serializers
from django.db import transaction
from .models import Event, EventRole, TicketType


class TicketTypeSerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()
    sold_count = serializers.SerializerMethodField()

    class Meta:
        model = TicketType
        fields = ["id", "name", "price", "quantity", "available", "sold_count"]

    def get_available(self, obj):
        return obj.available()

    def get_sold_count(self, obj):
        return obj.sold_count()


class TicketTypeInputSerializer(serializers.Serializer):
    """Used for creating ticket types — no read-only fields."""
    name = serializers.CharField(max_length=100)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    quantity = serializers.IntegerField(min_value=1)


class BulkTicketTypeSerializer(serializers.Serializer):
    """Accepts multiple ticket types in one request."""
    ticket_types = TicketTypeInputSerializer(many=True)

    def validate_ticket_types(self, value):
        if len(value) == 0:
            raise serializers.ValidationError("At least one ticket type is required.")
        # Check for duplicate names within the request itself
        names = [tt["name"] for tt in value]
        if len(names) != len(set(names)):
            raise serializers.ValidationError("Ticket type names must be unique.")
        return value


class EventCreationSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.username", read_only=True)
    ticket_types = TicketTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "venue",
            "online_link",
            "event_type",
            "event_date",
            "duration_hours",
            "platform_fee_percent",
            "created_by",
            "ticket_types",
        ]
        read_only_fields = ["id", "created_by"]

    def validate(self, data):
        event_type = data.get("event_type")
        venue = data.get("venue", "").strip()
        online_link = data.get("online_link", "").strip()

        if event_type == "OFFLINE" and not venue:
            raise serializers.ValidationError(
                {"venue": "Offline events require a venue."}
            )
        if event_type == "ONLINE" and not online_link:
            raise serializers.ValidationError(
                {"online_link": "Online events require a join link."}
            )
        return data


class EventRoleSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.username", read_only=True)
    event = serializers.CharField(source="event.title", read_only=True)

    class Meta:
        model = EventRole
        fields = ["id", "user", "event", "role", "assigned_at"]
        read_only_fields = ["id", "user", "event", "assigned_at"]