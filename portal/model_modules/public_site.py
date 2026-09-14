from django.db import models

from portal.models import Show, Team


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
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["show__show_date", "show__name"]

    def __str__(self):
        return f"{self.show} — {'Published' if self.is_published else 'Private'}"
