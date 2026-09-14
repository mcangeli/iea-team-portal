from django.urls import path

from portal.view_modules.show_day_live import show_day_live_status_update

urlpatterns = [
    path(
        "shows/<int:pk>/show-day/live-status/",
        show_day_live_status_update,
        name="show_day_live_status_update",
    ),
]
