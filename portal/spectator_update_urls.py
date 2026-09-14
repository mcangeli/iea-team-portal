from django.urls import path

from portal.view_modules.spectator_updates import (
    spectator_announcement_add,
    spectator_ring_delay_update,
    spectator_update_dismiss,
)

urlpatterns = [
    path("shows/<int:pk>/spectator-updates/add/", spectator_announcement_add, name="spectator_announcement_add"),
    path("shows/<int:pk>/spectator-updates/ring-delay/", spectator_ring_delay_update, name="spectator_ring_delay_update"),
    path("spectator-updates/<int:update_pk>/dismiss/", spectator_update_dismiss, name="spectator_update_dismiss"),
]
