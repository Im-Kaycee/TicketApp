from django.contrib import admin

# Register your models here.
from .models import *
admin.site.register(Event)


admin.site.register(EventRole)

admin.site.register(TicketType)
