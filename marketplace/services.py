from django.db import transaction
from tickets.models import Ticket
from tickets.validators import assert_ticket_listable
from tickets.paystack import initialize_transaction
from .models import MarketplaceListing

RESALE_PRICE_CAP_PERCENT = 130
PLATFORM_FEE_PERCENT = 10


class ListingNotActiveError(Exception):
    pass


class PriceCapExceededError(Exception):
    pass


class SellerBuyingOwnListingError(Exception):
    pass


def create_listing(*, seller, ticket, price):
    """
    List a ticket for resale.
    Validates ticket is eligible, checks price cap, updates ticket status.
    """
    # Confirm ticket belongs to seller
    if ticket.owner != seller:
        raise PermissionError("You do not own this ticket.")

    # Use the validator from the tickets app
    assert_ticket_listable(ticket)

    # Enforce 130% price cap
    from decimal import Decimal

    max_price = ticket.event.price * (Decimal(RESALE_PRICE_CAP_PERCENT) / Decimal(100))
    if price > max_price:
        raise PriceCapExceededError(
            f"Listing price cannot exceed NGN {max_price:.2f} "
            f"({RESALE_PRICE_CAP_PERCENT}% of original price)."
        )

    with transaction.atomic():
        listing = MarketplaceListing.objects.create(
            ticket=ticket,
            seller=seller,
            price=price,
        )
        ticket.status = Ticket.Status.LISTED_FOR_SALE
        ticket.save(update_fields=["status"])

    return listing


def cancel_listing(*, seller, listing):
    """
    Cancel an active listing.
    Reverts ticket status back to VALID.
    """
    if listing.seller != seller:
        raise PermissionError("You do not own this listing.")

    if listing.status != MarketplaceListing.Status.ACTIVE:
        raise ListingNotActiveError("Only active listings can be cancelled.")

    with transaction.atomic():
        listing.status = MarketplaceListing.Status.CANCELLED
        listing.save(update_fields=["status"])

        listing.ticket.status = Ticket.Status.VALID
        listing.ticket.save(update_fields=["status"])

    return listing


def initiate_resale_purchase(*, buyer, listing):
    """
    Start a resale payment session.
    Returns a Paystack payment URL.
    Ownership transfer happens in complete_resale_purchase after webhook confirms payment.
    """
    if listing.status != MarketplaceListing.Status.ACTIVE:
        raise ListingNotActiveError("This listing is no longer available.")

    if listing.seller == buyer:
        raise SellerBuyingOwnListingError("You cannot buy your own listing.")

    payment_data = initialize_transaction(
        email=buyer.email,
        amount_naira=listing.price,
        reference=f"resale_{listing.id}",
        subaccount_code=listing.seller.paystack_subaccount_code,
        platform_fee_percent=PLATFORM_FEE_PERCENT,
    )

    return payment_data["authorization_url"]


def complete_resale_purchase(*, listing, buyer):
    """
    Called by the webhook after payment is confirmed.
    Transfers ticket ownership to the buyer and marks listing as SOLD.
    """
    with transaction.atomic():
        ticket = listing.ticket

        # Transfer ownership
        ticket.owner = buyer
        ticket.status = Ticket.Status.VALID
        ticket.save(update_fields=["owner", "status"])

        listing.status = MarketplaceListing.Status.SOLD
        listing.save(update_fields=["status"])

    return listing