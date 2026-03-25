import resend
from django.conf import settings

BRAND_COLOR = '#C1FF72'
ORANGE = '#FF6B35'
BLACK = '#0A0A0A'
CARD = '#111111'
MUTED = '#888888'
WHITE = '#FFFFFF'
BORDER = '#222222'

def _header():
    return f"""
    <div style="background:{BLACK}; padding: 24px 32px; border-bottom: 1px solid {BORDER};">
        <span style="font-family: 'Trebuchet MS', Arial, sans-serif; font-weight: 800; font-size: 22px; color: {WHITE}; letter-spacing: -0.5px;">
            Gate<span style="color: {BRAND_COLOR};">pass</span>
        </span>
    </div>
    """

def _footer():
    return f"""
    <div style="background:{BLACK}; padding: 24px 32px; border-top: 1px solid {BORDER}; text-align: center;">
        <p style="font-family: Arial, sans-serif; color: {MUTED}; font-size: 12px; margin: 0 0 8px;">
            Gatepass · Your pass to everything
        </p>
        <a href="https://getgatepass.online" style="font-family: Arial, sans-serif; color: {MUTED}; font-size: 12px; text-decoration: none;">
            getgatepass.online
        </a>
    </div>
    """

def _wrapper(content: str) -> str:
    return f"""
    <div style="background: #0f0f0f; padding: 40px 20px; font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; background: {BLACK}; border: 1px solid {BORDER}; border-radius: 16px; overflow: hidden;">
            {_header()}
            <div style="padding: 32px;">
                {content}
            </div>
            {_footer()}
        </div>
    </div>
    """

def send_purchase_confirmation(order):
    tickets = list(order.items.select_related("ticket__event", "ticket__ticket_type").all())

    ticket_rows = ""
    for item in tickets:
        ticket = item.ticket
        ticket_url = f"{settings.FRONTEND_URL}/tickets/{ticket.id}"
        ticket_rows += f"""
        <tr>
            <td style="padding: 12px 0; border-bottom: 1px solid {BORDER}; color: {WHITE}; font-size: 14px;">
                {ticket.ticket_type.name}
            </td>
            <td style="padding: 12px 0; border-bottom: 1px solid {BORDER}; color: {MUTED}; font-size: 14px;">
                {ticket.event.title}
            </td>
            <td style="padding: 12px 0; border-bottom: 1px solid {BORDER}; text-align: right;">
                <a href="{ticket_url}" style="color: {BRAND_COLOR}; font-size: 13px; text-decoration: none; font-weight: bold;">
                    View ticket →
                </a>
            </td>
        </tr>
        """

    venue_or_link = ""
    if order.event.event_type == "ONLINE":
        venue_or_link = f"""
        <p style="color: {MUTED}; font-size: 14px; margin: 8px 0 0;">
            <strong style="color: {WHITE};">Join link:</strong>
            <a href="{order.event.online_link}" style="color: {BRAND_COLOR}; text-decoration: none;">
                {order.event.online_link}
            </a>
        </p>
        """
    else:
        venue_or_link = f"""
        <p style="color: {MUTED}; font-size: 14px; margin: 8px 0 0;">
            <strong style="color: {WHITE};">Venue:</strong> {order.event.venue}
        </p>
        """

    content = f"""
        <h2 style="font-family: 'Trebuchet MS', Arial, sans-serif; font-size: 24px; font-weight: 800; color: {WHITE}; margin: 0 0 8px; letter-spacing: -0.5px;">
            Your tickets are confirmed
        </h2>
        <p style="color: {MUTED}; font-size: 15px; margin: 0 0 32px;">
            Hi {order.buyer.get_full_name() or order.buyer.username}, your purchase was successful.
        </p>

        <table style="width: 100%; border-collapse: collapse; margin-bottom: 32px;">
            <thead>
                <tr style="background: {CARD};">
                    <th style="padding: 10px 0; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: {MUTED}; font-weight: 400;">
                        Ticket
                    </th>
                    <th style="padding: 10px 0; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: {MUTED}; font-weight: 400;">
                        Event
                    </th>
                    <th style="padding: 10px 0; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: {MUTED}; font-weight: 400;">
                    </th>
                </tr>
            </thead>
            <tbody>
                {ticket_rows}
            </tbody>
        </table>

        <div style="background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
            <p style="color: {WHITE}; font-size: 16px; font-weight: 700; margin: 0 0 8px; font-family: 'Trebuchet MS', Arial, sans-serif;">
                {order.event.title}
            </p>
            <p style="color: {MUTED}; font-size: 14px; margin: 0;">
                <strong style="color: {WHITE};">Date:</strong>
                {order.event.event_date.strftime("%B %d, %Y at %I:%M %p")}
            </p>
            {venue_or_link}
        </div>

        <div style="display: flex; justify-content: space-between; padding: 16px 0; border-top: 1px solid {BORDER};">
            <span style="color: {MUTED}; font-size: 14px;">Total paid</span>
            <span style="color: {BRAND_COLOR}; font-size: 18px; font-weight: 800; font-family: 'Trebuchet MS', Arial, sans-serif;">
                ₦{order.total_price:,.2f}
            </span>
        </div>
    """

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": order.buyer.email,
        "subject": f"Your tickets for {order.event.title}",
        "html": _wrapper(content),
    })


def send_checkin_confirmation(ticket, scanned_by):
    content = f"""
        <div style="text-align: center; padding: 16px 0 32px;">
            <div style="width: 64px; height: 64px; border-radius: 50%; background: rgba(193,255,114,0.1); border: 1px solid rgba(193,255,114,0.3); display: inline-flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                <span style="color: {BRAND_COLOR}; font-size: 28px;">✓</span>
            </div>
            <h2 style="font-family: 'Trebuchet MS', Arial, sans-serif; font-size: 24px; font-weight: 800; color: {WHITE}; margin: 0 0 8px; letter-spacing: -0.5px;">
                You&apos;re in!
            </h2>
            <p style="color: {MUTED}; font-size: 15px; margin: 0;">
                You have been successfully checked in.
            </p>
        </div>

        <div style="background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; padding: 20px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: {MUTED}; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">Event</td>
                    <td style="padding: 8px 0; color: {WHITE}; font-size: 14px; text-align: right;">{ticket.event.title}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: {MUTED}; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">Ticket type</td>
                    <td style="padding: 8px 0; color: {WHITE}; font-size: 14px; text-align: right;">{ticket.ticket_type.name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: {MUTED}; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">Checked in at</td>
                    <td style="padding: 8px 0; color: {WHITE}; font-size: 14px; text-align: right;">
                        {ticket.checkin_logs.latest("scanned_at").scanned_at.strftime("%B %d, %Y at %I:%M %p")}
                    </td>
                </tr>
            </table>
        </div>

        <p style="color: {MUTED}; font-size: 14px; text-align: center; margin: 24px 0 0;">
            Enjoy the event!
        </p>
    """

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": ticket.owner.email,
        "subject": f"Checked in — {ticket.event.title}",
        "html": _wrapper(content),
    })


def send_organizer_sale_alert(order):
    organizer = order.event.created_by
    net_earnings = order.total_price * (1 - order.event.platform_fee_percent / 100)

    content = f"""
        <h2 style="font-family: 'Trebuchet MS', Arial, sans-serif; font-size: 24px; font-weight: 800; color: {WHITE}; margin: 0 0 8px; letter-spacing: -0.5px;">
            New ticket sale
        </h2>
        <p style="color: {MUTED}; font-size: 15px; margin: 0 0 32px;">
            Hi {organizer.get_full_name() or organizer.username}, someone just bought tickets for your event.
        </p>

        <div style="background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: {MUTED}; font-size: 13px; border-bottom: 1px solid {BORDER};">Buyer</td>
                    <td style="padding: 8px 0; color: {WHITE}; font-size: 14px; text-align: right; border-bottom: 1px solid {BORDER};">
                        {order.buyer.get_full_name() or order.buyer.username}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: {MUTED}; font-size: 13px; border-bottom: 1px solid {BORDER};">Ticket type</td>
                    <td style="padding: 8px 0; color: {WHITE}; font-size: 14px; text-align: right; border-bottom: 1px solid {BORDER};">
                        {order.ticket_type.name}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: {MUTED}; font-size: 13px; border-bottom: 1px solid {BORDER};">Quantity</td>
                    <td style="padding: 8px 0; color: {WHITE}; font-size: 14px; text-align: right; border-bottom: 1px solid {BORDER};">
                        {order.quantity}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: {MUTED}; font-size: 13px; border-bottom: 1px solid {BORDER};">Order total</td>
                    <td style="padding: 8px 0; color: {WHITE}; font-size: 14px; text-align: right; border-bottom: 1px solid {BORDER};">
                        ₦{order.total_price:,.2f}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 12px 0 8px; color: {MUTED}; font-size: 13px;">Your earnings</td>
                    <td style="padding: 12px 0 8px; text-align: right;">
                        <span style="color: {BRAND_COLOR}; font-size: 20px; font-weight: 800; font-family: 'Trebuchet MS', Arial, sans-serif;">
                            ₦{net_earnings:,.2f}
                        </span>
                    </td>
                </tr>
            </table>
        </div>

        <p style="color: {MUTED}; font-size: 13px; text-align: center; margin: 0;">
            Revenue is sent directly to your connected bank account.
        </p>
    """

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": organizer.email,
        "subject": f"New sale — {order.event.title}",
        "html": _wrapper(content),
    })