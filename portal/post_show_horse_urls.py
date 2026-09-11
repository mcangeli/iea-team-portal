from django.urls import path

from .post_show_horse_views import (
    post_show_horse_history,
    post_show_horse_record_add,
    post_show_horse_record_edit,
)

urlpatterns = [
    path("shows/<int:show_pk>/horse-history/", post_show_horse_history, name="post_show_horse_history"),
    path("shows/<int:show_pk>/horse-history/add/", post_show_horse_record_add, name="post_show_horse_record_add"),
    path("shows/<int:show_pk>/horse-history/<int:record_pk>/edit/", post_show_horse_record_edit, name="post_show_horse_record_edit"),
]
