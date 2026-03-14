from django.urls import path, include
from .views import *

urlpatterns = [
    path('create/', EventCreateView.as_view(), name='event-create'),
    path('<int:event_id>/add-staff/<int:user_id>/', AddStaffView.as_view(), name='add-staff'),
    path('<int:event_id>/remove-staff/<int:user_id>/', RemoveStaffView.as_view(), name='remove-staff'),
    path('<int:event_id>/staff/', EventStaffView.as_view(), name='event-staff'),
    path("<int:event_id>/ticket-types/", AddTicketTypeView.as_view(), name="add-ticket-type"),
]
