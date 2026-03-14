from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tickets.models import Ticket
from .models import MarketplaceListing
from .serializers import (
    CreateListingSerializer,
    MarketplaceListingSerializer,
    PurchaseListingSerializer,
)
from .services import (
    ListingNotActiveError,
    PriceCapExceededError,
    SellerBuyingOwnListingError,
    cancel_listing,
    complete_resale_purchase,
    create_listing,
    initiate_resale_purchase,
)


class MarketplaceListView(APIView):
    """
    GET /marketplace/
    Returns all active listings.
    No auth required — anyone can browse.
    """
    permission_classes = []

    def get(self, request):
        listings = (
            MarketplaceListing.objects.filter(status=MarketplaceListing.Status.ACTIVE)
            .select_related("ticket__event", "seller")
            .order_by("-created_at")
        )
        return Response(MarketplaceListingSerializer(listings, many=True).data)


class CreateListingView(APIView):
    """
    POST /marketplace/list/
    Authenticated user lists one of their tickets for resale.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateListingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ticket = get_object_or_404(
            Ticket.objects.select_related("event"),
            pk=serializer.validated_data["ticket_id"],
        )

        try:
            listing = create_listing(
                seller=request.user,
                ticket=ticket,
                price=serializer.validated_data["price"],
            )
        except PermissionError as exc:
            raise PermissionDenied(str(exc))
        except PriceCapExceededError as exc:
            raise ValidationError({"detail": str(exc)})
        except Exception as exc:
            raise ValidationError({"detail": str(exc)})

        return Response(
            MarketplaceListingSerializer(listing).data,
            status=status.HTTP_201_CREATED,
        )


class CancelListingView(APIView):
    """
    POST /marketplace/<listing_id>/cancel/
    Seller cancels their active listing. Ticket reverts to VALID.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, listing_id):
        listing = get_object_or_404(MarketplaceListing, pk=listing_id)

        try:
            cancel_listing(seller=request.user, listing=listing)
        except PermissionError as exc:
            raise PermissionDenied(str(exc))
        except ListingNotActiveError as exc:
            raise ValidationError({"detail": str(exc)})

        return Response({"detail": "Listing cancelled successfully."})


class PurchaseListingView(APIView):
    """
    POST /marketplace/purchase/
    Authenticated user initiates purchase of a listed ticket.
    Returns a Paystack payment URL.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PurchaseListingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        listing = get_object_or_404(
            MarketplaceListing.objects.select_related(
                "ticket__event", "seller"
            ),
            pk=serializer.validated_data["listing_id"],
        )

        try:
            payment_url = initiate_resale_purchase(
                buyer=request.user,
                listing=listing,
            )
        except ListingNotActiveError as exc:
            raise ValidationError({"detail": str(exc)})
        except SellerBuyingOwnListingError as exc:
            raise ValidationError({"detail": str(exc)})

        return Response(
            {"listing_id": listing.id, "payment_url": payment_url},
            status=status.HTTP_201_CREATED,
        )


'''class MarketplaceWebhookView(APIView):
    """
    POST /marketplace/webhook/
    Paystack calls this after a resale payment succeeds.
    Transfers ticket ownership to the buyer and marks listing as SOLD.
    """
    permission_classes = []

    def post(self, request):
        import hashlib
        import hmac
        import json
        from django.conf import settings
        from tickets.paystack import verify_transaction
        from django.contrib.auth import get_user_model

        User = get_user_model()

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
            return Response(status=200)

        reference = payload["data"]["reference"]

        # Only handle resale references
        if not reference.startswith("resale_"):
            return Response(status=200)

        transaction_data = verify_transaction(reference)
        if transaction_data["status"] != "success":
            return Response(status=200)

        listing_id = reference.replace("resale_", "")

        try:
            listing = MarketplaceListing.objects.select_related(
                "ticket", "seller"
            ).get(id=listing_id, status=MarketplaceListing.Status.ACTIVE)
        except MarketplaceListing.DoesNotExist:
            return Response(status=200)

        # Get buyer from the transaction email
        buyer_email = payload["data"]["customer"]["email"]
        try:
            buyer = User.objects.get(email=buyer_email)
        except User.DoesNotExist:
            return Response(status=200)

        complete_resale_purchase(listing=listing, buyer=buyer)
        return Response(status=200)'''