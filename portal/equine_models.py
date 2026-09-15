from django.db import models

from .models import Team


class Horse(models.Model):
    """Canonical equine identity for ArenaLine.

    Keep this model focused on durable identity and current registry state.
    Relationships, assignments, care, documents, and activity belong in
    historical supporting records added throughout the v3.3.x line.
    """

    class Sex(models.TextChoices):
        MARE = "mare", "Mare"
        GELDING = "gelding", "Gelding"
        STALLION = "stallion", "Stallion"
        UNKNOWN = "unknown", "Unknown / not recorded"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        RETIRED = "retired", "Retired"
        DECEASED = "deceased", "Deceased"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="horses")
    barn_name = models.CharField(max_length=120)
    registered_name = models.CharField(max_length=180, blank=True)
    breed = models.CharField(max_length=120, blank=True)
    sex = models.CharField(max_length=20, choices=Sex.choices, default=Sex.UNKNOWN)
    color = models.CharField(max_length=80, blank=True)
    height_hands = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    markings = models.TextField(blank=True)
    photo = models.ImageField(upload_to="horses/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["barn_name", "registered_name", "id"]
        indexes = [
            models.Index(fields=["team", "status"], name="horse_team_status_idx"),
            models.Index(fields=["team", "barn_name"], name="horse_team_name_idx"),
        ]

    @property
    def display_name(self):
        return self.barn_name

    def __str__(self):
        if self.registered_name and self.registered_name != self.barn_name:
            return f"{self.barn_name} ({self.registered_name})"
        return self.barn_name


class HorseIdentifier(models.Model):
    """External or organization-specific identifiers without polluting Horse."""

    horse = models.ForeignKey(Horse, on_delete=models.CASCADE, related_name="identifiers")
    authority = models.CharField(max_length=100, help_text="Registry or organization, such as IEA or USEF.")
    identifier_type = models.CharField(max_length=80, blank=True, help_text="Optional identifier type or program name.")
    value = models.CharField(max_length=120)
    is_primary = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["authority", "identifier_type", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["horse", "authority", "identifier_type", "value"],
                name="unique_horse_external_identifier",
            )
        ]

    def __str__(self):
        label = self.identifier_type or self.authority
        return f"{self.horse} — {label}: {self.value}"
