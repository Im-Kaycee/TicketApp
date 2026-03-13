from django.db import models

# Create your models here.
class MarketplaceListing(models.Model):

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("SOLD", "Sold"),
        ("CANCELLED", "Cancelled"),
    ]

    ticket = models.OneToOneField(
        "tickets.Ticket",
        on_delete=models.CASCADE
    )

    seller = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE"
    )

    created_at = models.DateTimeField(auto_now_add=True)