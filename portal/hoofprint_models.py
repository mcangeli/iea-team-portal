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
