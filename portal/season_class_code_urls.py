from django.urls import path

from .season_class_code_views import season_class_code_edit

urlpatterns = [
    path("season/classes/<int:class_pk>/class-id/", season_class_code_edit, name="season_class_code_edit"),
]
