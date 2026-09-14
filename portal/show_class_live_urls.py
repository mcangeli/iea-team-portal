from django.urls import path

from portal.view_modules.show_class_live import show_class_live_status_update

urlpatterns = [
    path(
        "show-classes/<int:class_pk>/live-status/",
        show_class_live_status_update,
        name="show_class_live_status_update",
    ),
]
