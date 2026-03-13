import uuid
from django.db import models
from django.conf import settings


class Ticket(models.Model):
    class Status(models.TextChoices):
        VALID = "VALID", "Valid"
        CHECKED_IN = "CHECKED_IN", "Checked In"
        LISTED_FOR_SALE = "LISTED_FOR_SALE", "Listed for Sale"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.PROTECT,
        related_name="tickets",
    )
    owner = models.ForeignKey(
    "accounts.User",
        on_delete=models.PROTECT,
        related_name="tickets",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.VALID,
        db_index=True,
    )
    qr_signature = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Ticket {self.id} — {self.event} ({self.status})"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.PROTECT,
        related_name="orders",
        default=1,
    )
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.id} — {self.buyer} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    ticket = models.OneToOneField(
        Ticket, on_delete=models.PROTECT, related_name="order_item"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"OrderItem: {self.ticket_id} in {self.order_id}"


class CheckInLog(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.PROTECT, related_name="checkin_logs"
    )
    scanned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="checkins_performed",
    )
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scanned_at"]

    def __str__(self):
        return f"CheckIn: {self.ticket_id} by {self.scanned_by.username} at {self.scanned_at}"