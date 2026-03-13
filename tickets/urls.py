from django.urls import path

from .views import (
    CheckInView,
    MyTicketsView,
    PurchaseTicketsView,
    TicketDetailView,
    VerifyTicketView,
)

urlpatterns = [
    # Purchase flow
    path("purchase/", PurchaseTicketsView.as_view(), name="ticket-purchase"),

    # Ticket owner views
    path("my-tickets/", MyTicketsView.as_view(), name="my-tickets"),
    path("<uuid:ticket_id>/", TicketDetailView.as_view(), name="ticket-detail"),

    # QR scan flow
    path("verify/<uuid:ticket_id>/", VerifyTicketView.as_view(), name="ticket-verify"),
    path("<uuid:ticket_id>/checkin/", CheckInView.as_view(), name="ticket-checkin"),
]