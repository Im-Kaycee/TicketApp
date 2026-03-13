from django.db import transaction
from .models import Order, OrderItem, Ticket
from .qr import generate_qr_signature
from .paystack import initialize_transaction


class CapacityExceededError(Exception):
    pass


class InvalidQuantityError(Exception):
    pass


def initiate_purchase(*, user, event, quantity: int):
    """
    Phase 1 — validate capacity, create PENDING order, initialize Paystack payment.
    Tickets are NOT generated yet. Returns the order and Paystack payment URL.
    """
    if quantity < 1:
        raise InvalidQuantityError("Quantity must be at least 1.")

    with transaction.atomic():
        from events.models import Event as EventModel
        event = EventModel.objects.select_for_update().get(pk=event.pk)

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

        order = Order.objects.create(
            buyer=user,
            event=event,
            quantity=quantity,
            total_price=event.price * quantity,
            status=Order.Status.PENDING,
        )

    # Outside the transaction — no need to hold the DB lock during the API call
    payment_data = initialize_transaction(
        email=user.email,
        amount_naira=order.total_price,
        reference=order.id,
        subaccount_code=event.created_by.paystack_subaccount_code,
        platform_fee_percent=event.platform_fee_percent,
    )

    return order, payment_data["authorization_url"]


def complete_purchase(*, order):
    """
    Phase 2 — called by the webhook after Paystack confirms payment.
    This is where tickets are actually generated.
    """
    tickets = []
    order_items = []

    for _ in range(order.quantity):
        ticket = Ticket(
            event=order.event,
            owner=order.buyer,
            status=Ticket.Status.VALID,
        )
        ticket.qr_signature = generate_qr_signature(ticket.id)
        tickets.append(ticket)

    Ticket.objects.bulk_create(tickets)

    for ticket in tickets:
        order_items.append(
            OrderItem(order=order, ticket=ticket, price=order.event.price)
        )

    OrderItem.objects.bulk_create(order_items)

    order.status = Order.Status.COMPLETED
    order.save(update_fields=["status"])