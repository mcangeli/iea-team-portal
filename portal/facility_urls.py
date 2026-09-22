from django.urls import path

from . import facility_views

urlpatterns = [
    path("facilities/", facility_views.facility_list, name="facility_list"),
    path("facilities/add/", facility_views.facility_create, name="facility_create"),
    path("facilities/<int:pk>/", facility_views.facility_detail, name="facility_detail"),
    path("facilities/<int:pk>/edit/", facility_views.facility_edit, name="facility_edit"),
    path("facilities/<int:facility_pk>/spaces/add/", facility_views.facility_space_create, name="facility_space_create"),
    path("facility-spaces/<int:pk>/", facility_views.facility_space_detail, name="facility_space_detail"),
    path("facility-spaces/<int:pk>/edit/", facility_views.facility_space_edit, name="facility_space_edit"),
    path("facilities/<int:facility_pk>/housing/assign/", facility_views.stall_assignment_create, name="stall_assignment_create"),
    path("stall-assignments/<int:pk>/edit/", facility_views.stall_assignment_edit, name="stall_assignment_edit"),
    path("stall-assignments/<int:pk>/move/", facility_views.stall_assignment_move, name="stall_assignment_move"),
    path("stall-assignments/<int:pk>/vacate/", facility_views.stall_assignment_vacate, name="stall_assignment_vacate"),
    path("facilities/<int:facility_pk>/turnout/assign/", facility_views.pasture_assignment_create, name="pasture_assignment_create"),
    path("pasture-assignments/<int:pk>/edit/", facility_views.pasture_assignment_edit, name="pasture_assignment_edit"),
    path("pasture-assignments/<int:pk>/end/", facility_views.pasture_assignment_end, name="pasture_assignment_end"),
    path("pasture-assignments/<int:pk>/move/", facility_views.pasture_assignment_move, name="pasture_assignment_move"),
]
