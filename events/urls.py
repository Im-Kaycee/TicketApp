from django.urls import path
from .views import *
urlpatterns = [
    path("", EventDiscoveryView.as_view(), name="event-discovery"),
    path("create/", EventCreateView.as_view(), name="event-create"),
    path("dashboard/overview/", OrganizerOverviewView.as_view(), name="organizer-overview"),
    path("<int:event_id>/ticket-types/", AddTicketTypeView.as_view(), name="add-ticket-type"),
    path("<int:event_id>/add-staff/<int:user_id>/", AddStaffView.as_view(), name="add-staff"),
    path("<int:event_id>/remove-staff/<int:user_id>/", RemoveStaffView.as_view(), name="remove-staff"),
    path("<int:event_id>/staff/", EventStaffView.as_view(), name="event-staff"),
    path("<int:event_id>/dashboard/summary/", EventDashboardSummaryView.as_view(), name="dashboard-summary"),
    path("<int:event_id>/dashboard/ticket-types/", EventDashboardTicketTypesView.as_view(), name="dashboard-ticket-types"),
    path("<int:event_id>/dashboard/orders/", EventDashboardOrdersView.as_view(), name="dashboard-orders"),
    path("<int:event_id>/dashboard/attendance/", EventDashboardAttendanceView.as_view(), name="dashboard-attendance"),
]