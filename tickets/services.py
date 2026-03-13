from django.db import transaction
from django.db.models import F

from .models import Order, OrderItem, Ticket
from .qr import generate_qr_signature


class CapacityExceededError(Exception):
    pass


class InvalidQuantityError(Exception):
    pass


def purchase_tickets(*, user, event, quantity: int) -> Order:

    if quantity < 1:
        raise InvalidQuantityError("Quantity must be at least 1.")

    with transaction.atomic():
        # Lock the event row — no other transaction can read-then-write it
        # until this block commits.
        from events.models import Event 

        event = Event.objects.select_for_update().get(pk=event.pk)

        tickets_sold = Ticket.objects.filter(
            event=event,
            status__in=[
                Ticket.Status.VALID,
                Ticket.Status.CHECKED_IN,
                Ticket.Status.LISTED_FOR_SALE,
            ],
        ).count()

        available = event.capacity - tickets_sold
        if quantity > available:
            raise CapacityExceededError(
                f"Only {available} ticket(s) remaining for this event."
            )

        # Create the order in PENDING state first.
        order = Order.objects.create(
            buyer=user,
            total_price=event.price * quantity,
            status=Order.Status.PENDING,
        )

        # Generate tickets and attach them to the order.
        tickets = []
        order_items = []

        for _ in range(quantity):
            ticket = Ticket(
                event=event,
                owner=user,
                status=Ticket.Status.VALID,
            )
            ticket.qr_signature = generate_qr_signature(ticket.id)
            tickets.append(ticket)

        Ticket.objects.bulk_create(tickets)

        for ticket in tickets:
            order_items.append(
                OrderItem(order=order, ticket=ticket, price=event.price)
            )

        OrderItem.objects.bulk_create(order_items)

        # Mark order complete only after everything succeeded.
        order.status = Order.Status.COMPLETED
        order.save(update_fields=["status"])

        return order