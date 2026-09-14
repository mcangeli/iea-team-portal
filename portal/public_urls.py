from django.urls import path

from portal.view_modules.public_site import public_schedule, public_show_detail, public_site_home


urlpatterns = [
    path("public/<slug:site_slug>/", public_site_home, name="public_site_home"),
    path(
        "public/<slug:site_slug>/schedule/",
        public_schedule,
        name="public_schedule",
    ),
    path(
        "public/<slug:site_slug>/shows/<slug:show_slug>/",
        public_show_detail,
        name="public_show_detail",
    ),
]
