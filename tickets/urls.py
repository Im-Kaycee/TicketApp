from django.urls import path
from .views import (
    CheckInView,
    MyTicketsView,
    PaystackWebhookView,
    PurchaseTicketsView,
    TicketDetailView,
    VerifyTicketView,
)

urlpatterns = [
    path("purchase/", PurchaseTicketsView.as_view(), name="ticket-purchase"),
    path("my-tickets/", MyTicketsView.as_view(), name="my-tickets"),
    path("verify/<uuid:ticket_id>/", VerifyTicketView.as_view(), name="ticket-verify"),
    path("payment/webhook/", PaystackWebhookView.as_view(), name="paystack-webhook"),
    path("<uuid:ticket_id>/", TicketDetailView.as_view(), name="ticket-detail"),
    path("<uuid:ticket_id>/checkin/", CheckInView.as_view(), name="ticket-checkin"),
]