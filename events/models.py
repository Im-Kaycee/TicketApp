from django.db import models


class Event(models.Model):
    class EventType(models.TextChoices):
        ONLINE = "ONLINE", "Online"
        OFFLINE = "OFFLINE", "Offline"

    title = models.CharField(max_length=255)
    description = models.TextField()
    venue = models.CharField(max_length=255, blank=True)
    online_link = models.URLField(blank=True)
    image_url = models.URLField(blank=True)
    event_type = models.CharField(
        max_length=10,
        choices=EventType.choices,
        default=EventType.OFFLINE,
        db_index=True,
    )
    event_date = models.DateTimeField()
    duration_hours = models.PositiveIntegerField(default=4)
    platform_fee_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="events_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def capacity(self):
        return sum(tt.quantity for tt in self.ticket_types.all())

    def __str__(self):
        return self.title


class EventRole(models.Model):
    ROLE_CHOICES = [
        ("ORGANIZER", "Organizer"),
        ("STAFF", "Staff"),
    ]

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="roles")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "event")


class TicketType(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="ticket_types",
    )
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    class Meta:
        unique_together = ("event", "name")

    def __str__(self):
        return f"{self.name} — {self.event.title}"

    def sold_count(self):
        return self.tickets.filter(
            status__in=[
                "VALID",
                "CHECKED_IN",
                "LISTED_FOR_SALE",
            ]
        ).count()

    def available(self):
        return self.quantity - self.sold_count()