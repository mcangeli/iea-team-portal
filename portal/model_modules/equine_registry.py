from django.db import models


class HorseIdentifier(models.Model):
    """Organization or registry identifier attached to ArenaLine's canonical Horse."""

    horse = models.ForeignKey("portal.Horse", on_delete=models.CASCADE, related_name="identifiers")
    authority = models.CharField(max_length=100, help_text="Registry or organization, such as IEA or USEF.")
    identifier_type = models.CharField(max_length=80, blank=True, help_text="Optional identifier type or program name.")
    value = models.CharField(max_length=120)
    is_primary = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["authority", "identifier_type", "value", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["horse", "authority", "identifier_type", "value"],
                name="unique_horse_external_identifier",
            )
        ]

    def __str__(self):
        label = self.identifier_type or self.authority
        return f"{self.horse} — {label}: {self.value}"
