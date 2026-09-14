from django.urls import path

from portal.view_modules.people import (
    people_directory,
    person_create,
    person_detail,
    person_edit,
)

urlpatterns = [
    path("people/", people_directory, name="people_directory"),
    path("people/add/", person_create, name="person_create"),
    path("people/<int:pk>/", person_detail, name="person_detail"),
    path("people/<int:pk>/edit/", person_edit, name="person_edit"),
]
