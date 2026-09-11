from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .models import Show


class HoofprintSnapshot(models.Model):
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="hoofprint_snapshots")
    version = models.PositiveIntegerField()
    payload = models.JSONField(default=dict)
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finalized_hoofprints",
    )
    finalized_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version", "-finalized_at"]
        constraints = [
            models.UniqueConstraint(fields=["show", "version"], name="unique_hoofprint_version_per_show"),
        ]

    def clean(self):
        super().clean()
        if self.version < 1:
            raise ValidationError("Hoofprint version must be at least 1.")

    def __str__(self):
        return f"{self.show.name} — Hoofprint v{self.version}"


class ShowHorseListDocument(models.Model):
    """Host/show-provided horse list retained as a versioned operational source document."""

    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="horse_list_documents")
    revision = models.PositiveIntegerField()
    document = models.FileField(upload_to="show_horse_lists/%Y/%m/")
    source_name = models.CharField(
        max_length=160,
        blank=True,
        help_text="Optional source, host team, or label for this horse list.",
    )
    notes = models.CharField(max_length=255, blank=True)
    family_notes = models.TextField(
        blank=True,
        help_text="Coach notes intentionally shared with riders and parents for this show horse list.",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_show_horse_lists",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-revision", "-uploaded_at"]
        constraints = [
            models.UniqueConstraint(fields=["show", "revision"], name="unique_horse_list_revision_per_show"),
        ]

    def clean(self):
        super().clean()
        if self.revision < 1:
            raise ValidationError("Horse list revision must be at least 1.")

    def __str__(self):
        return f"{self.show.name} — Horse list revision {self.revision}"
