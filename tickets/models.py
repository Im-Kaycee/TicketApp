from django.db import models

# Create your models here.
class Ticket(models.Model):

    STATUS_CHOICES = [
        ("VALID", "Valid"),
        ("CHECKED_IN", "Checked In"),
        ("LISTED_FOR_SALE", "Listed For Sale"),
        ("CANCELLED", "Cancelled"),
    ]

    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    owner = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="VALID"
    )

    qr_signature = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Ticket {self.id} for {self.event.title} owned by {self.owner.username}"
    
class Order(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    buyer = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} by {self.buyer.username}"
    
class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"Order Item {self.id} for {self.ticket}"
    
class CheckInLog(models.Model):

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE
    )

    scanned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True
    )

    scanned_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Ticket scanned by {self.scanned_by}"