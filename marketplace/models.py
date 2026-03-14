from django.db import models


class MarketplaceListing(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SOLD = "SOLD", "Sold"
        CANCELLED = "CANCELLED", "Cancelled"

    ticket = models.OneToOneField(
        "tickets.Ticket",
        on_delete=models.CASCADE,
        related_name="listing",
    )
    seller = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="listings",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Listing {self.id} — {self.ticket} ({self.status})"