from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .horse_models import Horse, HorseShowAssignment
from .models import Show
from .show_readiness_models import ShowLeasedHorse


class ShowHorseHistory(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINAL = "final", "Final"

    show = models.OneToOneField(Show, on_delete=models.CASCADE, related_name="horse_history")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True, help_text="Post-show notes about the final horse contribution and usage record.")
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_show_horse_histories",
    )
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finalized_show_horse_histories",
    )
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-show__show_date", "-id"]

    @property
    def is_final(self):
        return self.status == self.Status.FINAL

    @property
    def contributed_count(self):
        return self.records.filter(counted_as_contribution=True).count()

    @property
    def used_count(self):
        return self.records.filter(actually_used=True).count()

    def clean(self):
        super().clean()
        if self.status == self.Status.FINAL and not self.finalized_at:
            raise ValidationError({"finalized_at": "Final horse history must have a finalized timestamp."})

    def __str__(self):
        return f"{self.show.name} — Post-show horse history"


class ShowHorseHistoryRecord(models.Model):
    class SourceType(models.TextChoices):
        REGISTRY = "registry", "Horse Registry"
        LEASED = "leased", "Leased / show-specific"
        OTHER = "other", "Other"

    history = models.ForeignKey(ShowHorseHistory, on_delete=models.CASCADE, related_name="records")
    source_type = models.CharField(max_length=12, choices=SourceType.choices)
    source_assignment = models.ForeignKey(
        HorseShowAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="history_records",
    )
    source_leased_horse = models.ForeignKey(
        ShowLeasedHorse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="history_records",
    )
    horse = models.ForeignKey(
        Horse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="show_history_records",
        help_text="Registry horse actually used. A leased placeholder can be reconciled to a registry horse after the show.",
    )
    barn_name = models.CharField(max_length=120)
    show_name = models.CharField(max_length=120, blank=True)
    provider = models.CharField(max_length=160, blank=True)
    ownership_type = models.CharField(max_length=20, blank=True)
    actually_used = models.BooleanField(default=True)
    counted_as_contribution = models.BooleanField(default=True)
    class_snapshot = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["barn_name", "id"]

    @property
    def display_name(self):
        return self.barn_name or self.show_name

    @property
    def reconciled_from_leased(self):
        return self.source_type == self.SourceType.LEASED and self.horse_id is not None

    def clean(self):
        super().clean()
        if self.horse_id and self.history_id and self.horse.team_id != self.history.show.team_id:
            raise ValidationError({"horse": "The reconciled horse must belong to the same team as the show."})
        if self.source_assignment_id and self.history_id and self.source_assignment.show_id != self.history.show_id:
            raise ValidationError({"source_assignment": "The source horse assignment must belong to this show."})
        if self.source_leased_horse_id and self.history_id and self.source_leased_horse.show_id != self.history.show_id:
            raise ValidationError({"source_leased_horse": "The leased horse record must belong to this show."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.history.show.name} — {self.display_name}"
