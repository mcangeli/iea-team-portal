from django.urls import path

from .view_modules import hoofprint, horses

urlpatterns = [
    path("horses/", horses.horse_list, name="horse_list"),
    path("horses/add/", horses.horse_create, name="horse_create"),
    path("horses/<int:pk>/", horses.horse_detail, name="horse_detail"),
    path("horses/<int:pk>/edit/", horses.horse_edit, name="horse_edit"),
    path("horses/<int:horse_pk>/coggins/add/", horses.horse_coggins_add, name="horse_coggins_add"),
    path("horses/<int:horse_pk>/coggins/<int:pk>/edit/", horses.horse_coggins_edit, name="horse_coggins_edit"),
    path("horses/<int:horse_pk>/eligibility/", horses.horse_season_profile, name="horse_season_profile"),
    path("horses/<int:horse_pk>/eligibility/<int:season_pk>/", horses.horse_season_profile, name="horse_season_profile_season"),
    path("shows/<int:show_pk>/horses/", horses.show_horses, name="show_horses"),
    path("shows/<int:show_pk>/horses/add/", horses.show_horse_add, name="show_horse_add"),
    path("shows/<int:show_pk>/horses/<int:pk>/edit/", horses.show_horse_edit, name="show_horse_edit"),
    path("shows/<int:show_pk>/horses/<int:pk>/remove/", horses.show_horse_remove, name="show_horse_remove"),
    path("shows/<int:show_pk>/horses/awards/add/", horses.show_horse_award_add, name="show_horse_award_add"),
    path("shows/<int:show_pk>/horses/awards/<int:pk>/edit/", horses.show_horse_award_edit, name="show_horse_award_edit"),
    path("shows/<int:show_pk>/horses/awards/<int:pk>/remove/", horses.show_horse_award_remove, name="show_horse_award_remove"),
    path("shows/<int:show_pk>/hoofprint/", hoofprint.show_hoofprint, name="show_hoofprint"),
    path("shows/<int:show_pk>/hoofprint/finalize/", hoofprint.show_hoofprint_finalize, name="show_hoofprint_finalize"),
    path("shows/<int:show_pk>/hoofprint/<int:snapshot_pk>.pdf", hoofprint.show_hoofprint_pdf, name="show_hoofprint_pdf"),
]
