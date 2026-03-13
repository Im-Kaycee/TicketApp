from django.db import models
# Create your models here.
class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    venue = models.CharField(max_length=255)

    event_date = models.DateTimeField()

    capacity = models.IntegerField()

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="events_created"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.title
    
class EventRole(models.Model):

    ROLE_CHOICES = [
        ("ORGANIZER", "Organizer"),
        ("STAFF", "Staff"),
    ]

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE
    )

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="roles"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "event")