import resend
from django.conf import settings


def send_purchase_confirmation(order):
    """
    Sent to the buyer after a successful purchase.
    Includes a link to view each ticket.
    """
    tickets = list(order.items.select_related("ticket__event", "ticket__ticket_type").all())
    ticket_rows = ""

    for item in tickets:
        ticket = item.ticket
        ticket_url = f"{settings.FRONTEND_URL}/tickets/{ticket.id}"
        ticket_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{ticket.ticket_type.name}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{ticket.event.title}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">
                <a href="{ticket_url}" style="color: #6c47ff;">View Ticket</a>
            </td>
        </tr>
        """

    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #6c47ff;">Your tickets are confirmed!</h2>
        <p>Hi {order.buyer.get_full_name() or order.buyer.username},</p>
        <p>Your purchase for <strong>{order.event.title}</strong> was successful.</p>

        <table style="width: 100%; border-collapse: collapse; margin: 24px 0;">
            <thead>
                <tr style="background: #f5f5f5;">
                    <th style="padding: 12px; text-align: left;">Ticket Type</th>
                    <th style="padding: 12px; text-align: left;">Event</th>
                    <th style="padding: 12px; text-align: left;">Link</th>
                </tr>
            </thead>
            <tbody>
                {ticket_rows}
            </tbody>
        </table>

        <p style="color: #666;">
            Total paid: <strong>NGN {order.total_price:,.2f}</strong>
        </p>

        <p style="color: #666; font-size: 14px;">
            Event date: {order.event.event_date.strftime("%B %d, %Y at %I:%M %p")}
        </p>

        {"<p><strong>Join link: </strong><a href='" + order.event.online_link + "'>" + order.event.online_link + "</a></p>" if order.event.event_type == "ONLINE" else "<p><strong>Venue: </strong>" + order.event.venue + "</p>"}

        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px;">
            If you have any issues with your tickets, please contact us.
        </p>
    </div>
    """

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": order.buyer.email,
        "subject": f"Your tickets for {order.event.title}",
        "html": html,
    })


def send_checkin_confirmation(ticket, scanned_by):
    """
    Sent to the ticket owner when they are checked in.
    """
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #6c47ff;">You're in! ✓</h2>
        <p>Hi {ticket.owner.get_full_name() or ticket.owner.username},</p>
        <p>You have been successfully checked in to <strong>{ticket.event.title}</strong>.</p>

        <div style="background: #f5f5f5; padding: 16px; border-radius: 8px; margin: 24px 0;">
            <p style="margin: 0;"><strong>Event:</strong> {ticket.event.title}</p>
            <p style="margin: 8px 0 0;"><strong>Ticket type:</strong> {ticket.ticket_type.name}</p>
            <p style="margin: 8px 0 0;"><strong>Checked in at:</strong> {ticket.checkin_logs.latest("scanned_at").scanned_at.strftime("%B %d, %Y at %I:%M %p")}</p>
        </div>

        <p style="color: #666;">Enjoy the event!</p>
    </div>
    """

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": ticket.owner.email,
        "subject": f"Checked in to {ticket.event.title}",
        "html": html,
    })


def send_organizer_sale_alert(order):
    """
    Sent to the event organizer when a ticket is purchased.
    """
    organizer = order.event.created_by

    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #6c47ff;">New ticket sale!</h2>
        <p>Hi {organizer.get_full_name() or organizer.username},</p>
        <p>Someone just purchased tickets for <strong>{order.event.title}</strong>.</p>

        <div style="background: #f5f5f5; padding: 16px; border-radius: 8px; margin: 24px 0;">
            <p style="margin: 0;"><strong>Buyer:</strong> {order.buyer.get_full_name() or order.buyer.username}</p>
            <p style="margin: 8px 0 0;"><strong>Ticket type:</strong> {order.ticket_type.name}</p>
            <p style="margin: 8px 0 0;"><strong>Quantity:</strong> {order.quantity}</p>
            <p style="margin: 8px 0 0;"><strong>Order total:</strong> NGN {order.total_price:,.2f}</p>
            <p style="margin: 8px 0 0;"><strong>Your earnings:</strong> NGN {order.total_price * (1 - order.event.platform_fee_percent / 100):,.2f}</p>
        </div>
    </div>
    """

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": organizer.email,
        "subject": f"New sale — {order.event.title}",
        "html": html,
    })