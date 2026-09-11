from django.urls import path

from .view_modules import calendar_v2

urlpatterns = [
    path("calendar/", calendar_v2.calendar, name="calendar"),
    path("calendar/<int:pk>/", calendar_v2.event_detail, name="event_detail"),
]
