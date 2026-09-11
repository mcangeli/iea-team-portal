from django.urls import path

from .view_modules import lifecycle

urlpatterns = [
    path("riders/former/", lifecycle.former_rider_list, name="former_rider_list"),
    path(
        "riders/<int:pk>/lifecycle/",
        lifecycle.rider_lifecycle_edit,
        name="rider_lifecycle_edit",
    ),
]
