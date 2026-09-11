from django.urls import path
from .view_modules import branding

urlpatterns = [
    path("manage/branding/", branding.team_branding, name="team_branding"),
]
