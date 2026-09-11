from django.urls import path

from . import show_readiness_views as views


urlpatterns = [
    path("season/<int:season_pk>/horse-requirements/", views.season_horse_requirements, name="season_horse_requirements"),
    path("shows/<int:show_pk>/readiness/", views.show_readiness, name="show_readiness"),
    path("shows/<int:show_pk>/leased-horses/add/", views.show_leased_horse_add, name="show_leased_horse_add"),
    path("shows/<int:show_pk>/leased-horses/<int:pk>/edit/", views.show_leased_horse_edit, name="show_leased_horse_edit"),
    path("shows/<int:show_pk>/leased-horses/<int:pk>/remove/", views.show_leased_horse_remove, name="show_leased_horse_remove"),
]
