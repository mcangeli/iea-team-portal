"""Team branding model for v2.0 Preview 8."""

from django.db import models

from .models import Team


class TeamBranding(models.Model):
    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name="branding")
    hero_image = models.ImageField(
        upload_to="team_branding/",
        blank=True,
        null=True,
        help_text="Wide team/show photograph used on the dashboard and sign-in presentation.",
    )
    hero_image_position = models.CharField(
        max_length=8,
        choices=[
            ("20%", "Favor top"),
            ("50%", "Center"),
            ("80%", "Favor bottom"),
        ],
        default="50%",
        help_text="Adjust which part of the photograph remains visible when it is cropped.",
    )

    futures_hero_image = models.ImageField(
        upload_to="team_branding/",
        blank=True,
        null=True,
        help_text="Wide photograph representing the Futures Team.",
    )
    futures_hero_image_position = models.CharField(
        max_length=8,
        choices=[("20%", "Favor top"), ("50%", "Center"), ("80%", "Favor bottom")],
        default="50%",
    )
    upper_hero_image = models.ImageField(
        upload_to="team_branding/",
        blank=True,
        null=True,
        help_text="Wide photograph representing the Upper Team.",
    )
    upper_hero_image_position = models.CharField(
        max_length=8,
        choices=[("20%", "Favor top"), ("50%", "Center"), ("80%", "Favor bottom")],
        default="50%",
    )

    def __str__(self):
        return f"{self.team} branding"
