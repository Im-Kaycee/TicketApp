from rest_framework import serializers
from .models import MarketplaceListing


class MarketplaceListingSerializer(serializers.ModelSerializer):
    ticket_id = serializers.UUIDField(source="ticket.id", read_only=True)
    event_name = serializers.CharField(source="ticket.event.title", read_only=True)
    event_date = serializers.DateTimeField(source="ticket.event.event_date", read_only=True)
    seller_name = serializers.CharField(source="seller.username", read_only=True)
    original_price = serializers.DecimalField(
        source="ticket.event.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = MarketplaceListing
        fields = [
            "id",
            "ticket_id",
            "event_name",
            "event_date",
            "seller_name",
            "original_price",
            "price",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class CreateListingSerializer(serializers.Serializer):
    ticket_id = serializers.UUIDField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)


class PurchaseListingSerializer(serializers.Serializer):
    listing_id = serializers.IntegerField()