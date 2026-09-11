from django.urls import path

from . import host_show_views

urlpatterns = [
    path("dashboard/show-manager/", host_show_views.dashboard_show_manager, name="dashboard_show_manager"),
    path("host-shows/", host_show_views.host_show_list, name="host_show_list"),
    path("shows/<int:show_pk>/host/", host_show_views.host_show_workspace, name="host_show_workspace"),
    path("shows/<int:show_pk>/host/edit/", host_show_views.host_show_edit, name="host_show_edit"),
    path("shows/<int:show_pk>/host/manager/add/", host_show_views.show_manager_add, name="show_manager_add"),
    path("shows/<int:show_pk>/host/manager/<int:assignment_pk>/remove/", host_show_views.show_manager_remove, name="show_manager_remove"),
    path("shows/<int:show_pk>/host/staff/add/", host_show_views.host_staff_add, name="host_staff_add"),
    path("shows/<int:show_pk>/host/staff/<int:staff_pk>/edit/", host_show_views.host_staff_edit, name="host_staff_edit"),
    path("shows/<int:show_pk>/host/staff/<int:staff_pk>/remove/", host_show_views.host_staff_remove, name="host_staff_remove"),
]
