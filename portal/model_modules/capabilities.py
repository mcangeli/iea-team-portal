from django.core.exceptions import ValidationError
from django.db import models


class OrganizationCapabilityAssignment(models.Model):
    """Explicit authorization delegated to a Person independently of job/participation roles."""

    class Capability(models.TextChoices):
        MANAGE_HORSES = "manage_horses", "Manage Horses"

    team = models.ForeignKey(
        "portal.Team",
        on_delete=models.CASCADE,
        related_name="capability_assignments",
    )
    person = models.ForeignKey(
        "portal.Person",
        on_delete=models.CASCADE,
        related_name="capability_assignments",
    )
    capability = models.CharField(max_length=40, choices=Capability.choices)
    active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["capability", "person__last_name", "person__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "person", "capability"],
                name="unique_person_organization_capability",
            )
        ]

    def clean(self):
        super().clean()
        if self.person_id and self.team_id and self.person.team_id != self.team_id:
            raise ValidationError("Capability assignment must belong to the person's organization.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Capability end date cannot be before the start date.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.person} — {self.get_capability_display()}"
