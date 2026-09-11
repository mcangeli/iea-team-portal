from django.urls import path

from . import host_show_views

urlpatterns = [
    path("shows/<int:show_pk>/host/", host_show_views.host_show_workspace, name="host_show_workspace"),
    path("shows/<int:show_pk>/host/edit/", host_show_views.host_show_edit, name="host_show_edit"),
]
