from django.urls import path

from portal.public_site_admin import public_show_publication_edit, public_site_manage

urlpatterns = [
    path("manage/public-site/", public_site_manage, name="public_site_manage"),
    path(
        "manage/public-site/shows/<int:show_pk>/",
        public_show_publication_edit,
        name="public_show_publication_edit",
    ),
]
