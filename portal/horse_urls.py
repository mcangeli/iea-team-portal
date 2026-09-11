from django.urls import path

from .view_modules import horses

urlpatterns = [
    path("horses/", horses.horse_list, name="horse_list"),
    path("horses/add/", horses.horse_create, name="horse_create"),
    path("horses/<int:pk>/", horses.horse_detail, name="horse_detail"),
    path("horses/<int:pk>/edit/", horses.horse_edit, name="horse_edit"),
    path("horses/<int:horse_pk>/coggins/add/", horses.horse_coggins_add, name="horse_coggins_add"),
    path("horses/<int:horse_pk>/coggins/<int:pk>/edit/", horses.horse_coggins_edit, name="horse_coggins_edit"),
    path("horses/<int:horse_pk>/eligibility/", horses.horse_season_profile, name="horse_season_profile"),
    path("horses/<int:horse_pk>/eligibility/<int:season_pk>/", horses.horse_season_profile, name="horse_season_profile_season"),
]
