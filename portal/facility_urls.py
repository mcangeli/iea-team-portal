from django.urls import path

from . import facility_views

urlpatterns = [
    path("facilities/", facility_views.facility_list, name="facility_list"),
    path("facilities/add/", facility_views.facility_create, name="facility_create"),
    path("facilities/<int:pk>/", facility_views.facility_detail, name="facility_detail"),
    path("facilities/<int:pk>/edit/", facility_views.facility_edit, name="facility_edit"),
    path("facilities/<int:facility_pk>/spaces/add/", facility_views.facility_space_create, name="facility_space_create"),
    path("facility-spaces/<int:pk>/edit/", facility_views.facility_space_edit, name="facility_space_edit"),
    path("facilities/<int:facility_pk>/housing/assign/", facility_views.stall_assignment_create, name="stall_assignment_create"),
    path("stall-assignments/<int:pk>/edit/", facility_views.stall_assignment_edit, name="stall_assignment_edit"),
]
