"""
validators.py — Guards called by the marketplace app before listing a ticket.

Usage in your marketplace app:

    from tickets.validators import assert_ticket_listable

    def create_listing(ticket, seller):
        assert_ticket_listable(ticket)  # raises if not allowed
        # ... proceed with listing
"""
from rest_framework.exceptions import ValidationError

from .models import Ticket


class TicketNotListableError(ValidationError):
    pass


def assert_ticket_listable(ticket: Ticket) -> None:
    """
    Raise TicketNotListableError if the ticket may not be listed for resale.
    Call this from the marketplace app before creating any listing.
    """
    if ticket.status == Ticket.Status.CHECKED_IN:
        raise TicketNotListableError(
            {"detail": "A ticket that has already been used cannot be listed for sale."}
        )
    if ticket.status == Ticket.Status.CANCELLED:
        raise TicketNotListableError(
            {"detail": "A cancelled ticket cannot be listed for sale."}
        )
    if ticket.status == Ticket.Status.LISTED_FOR_SALE:
        raise TicketNotListableError(
            {"detail": "This ticket is already listed for sale."}
        )
    if ticket.status != Ticket.Status.VALID:
        raise TicketNotListableError(
            {"detail": f"Ticket status '{ticket.status}' is not eligible for listing."}
        )