from decimal import Decimal
from django.db import transaction
from .models import Order, OrderItem, Ticket
from .qr import generate_qr_signature
from .paystack import initialize_transaction

MAX_TICKETS_PER_PURCHASE = 6


class CapacityExceededError(Exception):
    pass


class InvalidQuantityError(Exception):
    pass


class PurchaseLimitExceededError(Exception):
    pass


def initiate_purchase(*, user, ticket_type, quantity: int):
    """
    Phase 1 — validate capacity and purchase limit, create PENDING order,
    initialize Paystack payment. Tickets are NOT generated yet.
    """
    if quantity < 1:
        raise InvalidQuantityError("Quantity must be at least 1.")

    if quantity > MAX_TICKETS_PER_PURCHASE:
        raise PurchaseLimitExceededError(
            f"You cannot purchase more than {MAX_TICKETS_PER_PURCHASE} tickets at once."
        )

    with transaction.atomic():
        from events.models import TicketType as TicketTypeModel
        ticket_type = TicketTypeModel.objects.select_for_update().get(pk=ticket_type.pk)

        sold = Ticket.objects.filter(
            ticket_type=ticket_type,
            status__in=[
                Ticket.Status.VALID,
                Ticket.Status.CHECKED_IN,
                Ticket.Status.LISTED_FOR_SALE,
            ],
        ).count()

        available = ticket_type.quantity - sold
        if quantity > available:
            raise CapacityExceededError(
                f"Only {available} ticket(s) remaining for {ticket_type.name}."
            )

        order = Order.objects.create(
            buyer=user,
            event=ticket_type.event,
            ticket_type=ticket_type,
            quantity=quantity,
            total_price=ticket_type.price * quantity,
            status=Order.Status.PENDING,
        )

    payment_data = initialize_transaction(
        email=user.email,
        amount_naira=order.total_price,
        reference=order.id,
        subaccount_code=ticket_type.event.created_by.paystack_subaccount_code,
        platform_fee_percent=ticket_type.event.platform_fee_percent,
    )

    return order, payment_data["authorization_url"]


def complete_purchase(*, order):
    from .emails import send_purchase_confirmation, send_organizer_sale_alert
    import logging
    logger = logging.getLogger(__name__)

    tickets = []
    order_items = []

    for _ in range(order.quantity):
        ticket = Ticket(
            event=order.event,
            ticket_type=order.ticket_type,
            owner=order.buyer,
            status=Ticket.Status.VALID,
        )
        ticket.qr_signature = generate_qr_signature(ticket.id)
        tickets.append(ticket)

    Ticket.objects.bulk_create(tickets)

    for ticket in tickets:
        order_items.append(
            OrderItem(
                order=order,
                ticket=ticket,
                price=order.ticket_type.price,
            )
        )

    OrderItem.objects.bulk_create(order_items)

    order.status = Order.Status.COMPLETED
    order.save(update_fields=["status"])

    try:
        send_purchase_confirmation(order)
        send_organizer_sale_alert(order)
    except Exception as e:
        logger.error(f"Email failed: {e}", exc_info=True)