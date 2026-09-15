from django.core.exceptions import ValidationError
from django.db import models


class HorseComplianceRequirement(models.Model):
    """Organization-level definition of paperwork required for horse readiness."""

    class RequirementType(models.TextChoices):
        COGGINS = "coggins", "Coggins"
        DOCUMENT = "document", "Horse document"

    team = models.ForeignKey("portal.Team", on_delete=models.CASCADE, related_name="horse_compliance_requirements")
    name = models.CharField(max_length=120)
    requirement_type = models.CharField(max_length=16, choices=RequirementType.choices)
    document_type = models.CharField(
        max_length=24,
        choices=[
            ("registration", "Registration papers"),
            ("vaccination", "Vaccination record"),
            ("lease", "Lease agreement"),
            ("ownership", "Ownership document"),
            ("veterinary", "Veterinary document"),
            ("insurance", "Insurance document"),
            ("care", "Care document"),
            ("other", "Other"),
        ],
        blank=True,
    )
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["team", "name"], name="unique_horse_compliance_requirement_name")
        ]

    def clean(self):
        super().clean()
        if self.requirement_type == self.RequirementType.DOCUMENT and not self.document_type:
            raise ValidationError({"document_type": "Choose the horse document type that satisfies this requirement."})
        if self.requirement_type == self.RequirementType.COGGINS and self.document_type:
            raise ValidationError({"document_type": "Coggins uses the dedicated Coggins record and does not need a document type."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name
