from django.urls import path

from portal.view_modules.equine_access import person_horse_access
from portal.view_modules.people import (
    barn_operations,
    committee_add,
    committee_edit,
    organization_group_add,
    organization_group_edit,
    people_directory,
    people_structure,
    person_committee_add,
    person_committee_edit,
    person_create,
    person_detail,
    person_edit,
    person_relationship_add,
    person_relationship_edit,
    person_role_add,
    person_role_edit,
)
from portal.view_modules.people_access import person_login_create
from portal.view_modules.people_structure import committee_detail, organization_group_detail

urlpatterns = [
    path("people/", people_directory, name="people_directory"),
    path("people/operations/", barn_operations, name="barn_operations"),
    path("people/structure/", people_structure, name="people_structure"),
    path("people/structure/groups/add/", organization_group_add, name="organization_group_add"),
    path("people/structure/groups/<int:group_pk>/", organization_group_detail, name="organization_group_detail"),
    path("people/structure/groups/<int:group_pk>/edit/", organization_group_edit, name="organization_group_edit"),
    path("people/structure/committees/add/", committee_add, name="committee_add"),
    path("people/structure/committees/<int:committee_pk>/", committee_detail, name="committee_detail"),
    path("people/structure/committees/<int:committee_pk>/edit/", committee_edit, name="committee_edit"),
    path("people/add/", person_create, name="person_create"),
    path("people/<int:pk>/", person_detail, name="person_detail"),
    path("people/<int:pk>/edit/", person_edit, name="person_edit"),
    path("people/<int:pk>/access/create/", person_login_create, name="person_login_create"),
    path("people/<int:person_pk>/access/horses/", person_horse_access, name="person_horse_access"),
    path("people/<int:pk>/roles/add/", person_role_add, name="person_role_add"),
    path("people/<int:pk>/roles/<int:role_pk>/edit/", person_role_edit, name="person_role_edit"),
    path("people/<int:pk>/relationships/add/", person_relationship_add, name="person_relationship_add"),
    path("people/<int:pk>/relationships/<int:relationship_pk>/edit/", person_relationship_edit, name="person_relationship_edit"),
    path("people/<int:pk>/committees/add/", person_committee_add, name="person_committee_add"),
    path("people/<int:pk>/committees/<int:membership_pk>/edit/", person_committee_edit, name="person_committee_edit"),
]
