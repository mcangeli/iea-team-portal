from django.core.exceptions import ValidationError
from django.db import models

from portal.models import Show, ShowClass, Team


class PublicSiteProfile(models.Model):
    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name="public_site")
    slug = models.SlugField(max_length=120, unique=True)
    enabled = models.BooleanField(
        default=False,
        help_text="Nothing is publicly accessible for this organization until this is enabled.",
    )
    display_name = models.CharField(max_length=160, blank=True)
    tagline = models.CharField(max_length=240, blank=True)
    introduction = models.TextField(blank=True)
    publish_logo = models.BooleanField(default=False)
    publish_website = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["team__name"]

    def __str__(self):
        return self.display_name or self.team.name


class PublicShowPublication(models.Model):
    class PublicStatus(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        IN_PROGRESS = "in_progress", "In progress"
        PAUSED = "paused", "Paused"
        COMPLETE = "complete", "Complete"

    show = models.OneToOneField(Show, on_delete=models.CASCADE, related_name="public_publication")
    slug = models.SlugField(max_length=180, unique=True)
    is_published = models.BooleanField(
        default=False,
        help_text="The show remains private until this is enabled and the organization public site is enabled.",
    )
    public_summary = models.TextField(blank=True)
    publish_time = models.BooleanField(default=False)
    publish_venue = models.BooleanField(default=False)
    publish_address = models.BooleanField(default=False)
    publish_host_team = models.BooleanField(default=False)
    publish_iea_area = models.BooleanField(default=False)
    publish_schedule = models.BooleanField(
        default=False,
        help_text="Publishes only the show's allow-listed class order and public schedule fields. Entries and internal strategy remain private.",
    )
    publish_results = models.BooleanField(
        default=False,
        help_text="Publishes only finalized class placings and rider display names. Entry strategy, internal notes, and points-rider status remain private.",
    )
    publish_live_status = models.BooleanField(
        default=False,
        help_text="Publishes the spectator-facing show status and current class. Internal show-day operations remain private.",
    )
    public_status = models.CharField(
        max_length=20,
        choices=PublicStatus.choices,
        default=PublicStatus.UPCOMING,
    )
    current_class = models.ForeignKey(
        ShowClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional class currently running for the public spectator view.",
    )
    public_status_note = models.CharField(
        max_length=180,
        blank=True,
        help_text="Optional public update such as 'Running about 15 minutes behind.'",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["show__show_date", "show__name"]

    def clean(self):
        super().clean()
        if self.current_class_id and self.show_id and self.current_class.show_id != self.show_id:
            raise ValidationError({"current_class": "Current class must belong to this show."})

    def __str__(self):
        return f"{self.show} — {'Published' if self.is_published else 'Private'}"
