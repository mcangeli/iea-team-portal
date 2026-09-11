from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .models import Season, SeasonClass, Team


class Horse(models.Model):
    class Preference(models.TextChoices):
        YES = "yes", "Yes"
        NO = "no", "No"
        OPTIONAL = "optional", "Optional"

    class LeadChange(models.TextChoices):
        FLYING = "flying", "Flying"
        SIMPLE = "simple", "Simple"
        EITHER = "either", "Either"
        NONE = "none", "None / not applicable"

    class OwnershipType(models.TextChoices):
        TEAM = "team", "Team-owned"
        PRIVATE = "private", "Privately contributed"
        LEASED = "leased", "Leased"
        OTHER = "other", "Other"

    class Sex(models.TextChoices):
        MARE = "mare", "Mare"
        GELDING = "gelding", "Gelding"
        STALLION = "stallion", "Stallion"
        OTHER = "other", "Other / not specified"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="horses")
    name = models.CharField(max_length=120)
    show_name = models.CharField(max_length=120, blank=True, help_text="Optional show name if different from barn name.")
    breed = models.CharField(max_length=120, blank=True)
    sex = models.CharField(max_length=12, choices=Sex.choices, blank=True)
    size_type = models.CharField(max_length=80, blank=True, help_text="Example: horse, large pony, medium pony.")
    height_hands = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    has_height_restriction = models.BooleanField(default=False)
    height_restriction_notes = models.CharField(max_length=255, blank=True)
    has_weight_restriction = models.BooleanField(default=False)
    weight_restriction_notes = models.CharField(max_length=255, blank=True)

    crop_preference = models.CharField(max_length=12, choices=Preference.choices, default=Preference.OPTIONAL)
    spur_preference = models.CharField(max_length=12, choices=Preference.choices, default=Preference.OPTIONAL)
    lead_change = models.CharField(max_length=12, choices=LeadChange.choices, default=LeadChange.EITHER)
    riding_description = models.TextField(blank=True, help_text="Short description for riders and Hoofprint paperwork.")

    ownership_type = models.CharField(max_length=12, choices=OwnershipType.choices, default=OwnershipType.PRIVATE)
    owner_name = models.CharField(max_length=160, blank=True)
    home_barn = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
    photo = models.ImageField(upload_to="horses/", blank=True, null=True)
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["team", "name"], name="unique_horse_name_per_team"),
        ]

    @property
    def display_name(self):
        return self.show_name or self.name

    @property
    def current_coggins(self):
        today = timezone.localdate()
        return self.coggins_records.filter(expiration_date__gte=today).order_by("expiration_date", "-test_date").last()

    @property
    def latest_coggins(self):
        return self.coggins_records.order_by("-expiration_date", "-test_date", "-id").first()

    def __str__(self):
        return self.display_name


class HorseCogginsRecord(models.Model):
    horse = models.ForeignKey(Horse, on_delete=models.CASCADE, related_name="coggins_records")
    test_date = models.DateField()
    expiration_date = models.DateField()
    document = models.FileField(upload_to="horses/coggins/%Y/%m/", blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-expiration_date", "-test_date", "-id"]

    def clean(self):
        super().clean()
        if self.test_date and self.expiration_date and self.expiration_date < self.test_date:
            raise ValidationError("Coggins expiration date cannot be before the test date.")

    @property
    def status(self):
        today = timezone.localdate()
        if self.expiration_date < today:
            return "expired"
        if self.expiration_date <= today + timedelta(days=30):
            return "expiring"
        return "current"

    @property
    def status_label(self):
        return {
            "expired": "Expired",
            "expiring": "Expiring soon",
            "current": "Current",
        }[self.status]

    def __str__(self):
        return f"{self.horse.display_name} — Coggins through {self.expiration_date:%b %d, %Y}"


class HorseSeasonProfile(models.Model):
    horse = models.ForeignKey(Horse, on_delete=models.CASCADE, related_name="season_profiles")
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="horse_profiles")
    eligible_classes = models.ManyToManyField(SeasonClass, blank=True, related_name="eligible_horse_profiles")
    active_for_season = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-season__start_date", "horse__name"]
        constraints = [
            models.UniqueConstraint(fields=["horse", "season"], name="unique_horse_season_profile"),
        ]

    def clean(self):
        super().clean()
        if self.horse_id and self.season_id and self.horse.team_id != self.season.team_id:
            raise ValidationError("Horse and season must belong to the same team.")

    def save(self, *args, **kwargs):
        self.full_clean(exclude=["eligible_classes"])
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.horse.display_name} — {self.season.name}"
