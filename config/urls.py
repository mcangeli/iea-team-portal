from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("portal.branding_urls")),
    path("", include("portal.account_urls")),
    path("", include("portal.lifecycle_urls")),
    path("", include("portal.calendar_urls")),
    path("", include("portal.horse_urls")),
    path("", include("portal.season_class_code_urls")),
    path("", include("portal.show_readiness_urls")),
    path("", include("portal.course_urls")),
    path("", include("portal.post_show_horse_urls")),
    path("", include("portal.host_show_urls")),
    path("", include("portal.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
