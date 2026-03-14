from rest_framework import serializers

from .models import CheckInLog, Order, OrderItem, Ticket


class TicketSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source="event.title", read_only=True)
    event_type = serializers.CharField(source="event.event_type", read_only=True)
    online_link = serializers.SerializerMethodField()
    owner_email = serializers.CharField(source="owner.email", read_only=True)
    ticket_type_name = serializers.CharField(source="ticket_type.name", read_only=True)
    ticket_type_price = serializers.DecimalField(
        source="ticket_type.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Ticket
        fields = [
            "id",
            "event",
            "event_name",
            "event_type",
            "online_link",
            "ticket_type",
            "ticket_type_name",
            "ticket_type_price",
            "owner",
            "owner_email",
            "status",
            "qr_signature",
            "created_at",
        ]
        read_only_fields = fields

    def get_online_link(self, obj):
        if obj.event.event_type == "ONLINE":
            return obj.event.online_link
        return None
class OrderItemSerializer(serializers.ModelSerializer):
    ticket = TicketSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["ticket", "price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "buyer", "total_price", "status", "created_at", "items"]
        read_only_fields = fields


class PurchaseInputSerializer(serializers.Serializer):
    ticket_type_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=6)

class CheckInLogSerializer(serializers.ModelSerializer):
    scanned_by_email = serializers.CharField(source="scanned_by.email", read_only=True)

    class Meta:
        model = CheckInLog
        fields = ["id", "ticket", "scanned_by", "scanned_by_email", "scanned_at"]
        read_only_fields = fields


class VerifyTicketSerializer(serializers.Serializer):
    """Read-only shape returned from the verify endpoint."""
    ticket_id = serializers.UUIDField()
    owner = serializers.CharField()
    event = serializers.CharField()
    status = serializers.CharField()
    signature_valid = serializers.BooleanField()