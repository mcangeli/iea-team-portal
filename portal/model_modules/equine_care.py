from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class HorseCareRecord(models.Model):
    """Historical operational care record for a horse.

    Records describe work that happened. ``next_due_date`` is deliberately
    stored with the historical event so ArenaLine can surface upcoming care
    without overwriting the event that established the due date.

    Coggins is intentionally not a generic care type. ArenaLine already has a
    dedicated Coggins compliance record, which remains the single source of
    truth for show-readiness and Coggins documentation.
    """

    class CareType(models.TextChoices):
        VACCINATION = "vaccination", "Vaccination"
        FARRIER = "farrier", "Farrier"
        DENTAL = "dental", "Dental"
        VETERINARY = "veterinary", "Veterinary visit"
        MEDICATION = "medication", "Medication / treatment"
        WELLNESS = "wellness", "Wellness / routine care"
        OTHER = "other", "Other"

    horse = models.ForeignKey(
        "portal.Horse",
        on_delete=models.CASCADE,
        related_name="care_records",
    )
    care_type = models.CharField(max_length=24, choices=CareType.choices)
    title = models.CharField(
        max_length=160,
        help_text="Short description, such as Spring vaccines, front shoes, or dental float.",
    )
    performed_date = models.DateField()
    next_due_date = models.DateField(null=True, blank=True)
    provider = models.ForeignKey(
        "portal.Person",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="horse_care_records",
        help_text="Optional provider from the organization's People directory.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-performed_date", "-id"]
        indexes = [
            models.Index(fields=["horse", "next_due_date"], name="horse_care_due_idx"),
            models.Index(fields=["care_type", "next_due_date"], name="horse_care_type_due_idx"),
        ]

    def clean(self):
        super().clean()
        if self.provider_id and self.horse_id and self.provider.team_id != self.horse.team_id:
            raise ValidationError({"provider": "Care provider must belong to the horse's organization."})
        if self.next_due_date and self.performed_date and self.next_due_date < self.performed_date:
            raise ValidationError({"next_due_date": "Next due date cannot be before the performed date."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def due_status(self):
        if not self.next_due_date:
            return "none"
        today = timezone.localdate()
        if self.next_due_date < today:
            return "overdue"
        if self.next_due_date <= today + timedelta(days=30):
            return "due_soon"
        return "current"

    @property
    def due_status_label(self):
        return {
            "none": "No due date",
            "overdue": "Overdue",
            "due_soon": "Due soon",
            "current": "Current",
        }[self.due_status]

    def __str__(self):
        return f"{self.horse.display_name} — {self.title} ({self.performed_date:%b %d, %Y})"
