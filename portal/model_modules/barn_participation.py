from django.core.exceptions import ValidationError
from django.db import models


class HorsePersonRelationship(models.Model):
    class RelationshipType(models.TextChoices):
        OWNER = "owner", "Owner"
        BOARDER = "boarder", "Boarder / Responsible Party"
        FULL_LEASE = "full_lease", "Full Lease"
        HALF_LEASE = "half_lease", "Half Lease"
        PARTIAL_LEASE = "partial_lease", "Partial Lease"
        TRAINER = "trainer", "Trainer"
        CARETAKER = "caretaker", "Caretaker"
        VETERINARIAN = "veterinarian", "Veterinarian"
        FARRIER = "farrier", "Farrier"
        DENTIST = "dentist", "Equine Dentist"
        EMERGENCY_CONTACT = "emergency_contact", "Emergency Contact"

    team = models.ForeignKey(
        "portal.Team",
        on_delete=models.CASCADE,
        related_name="horse_person_relationships",
    )
    horse = models.ForeignKey(
        "portal.Horse",
        on_delete=models.CASCADE,
        related_name="person_relationships",
    )
    person = models.ForeignKey(
        "portal.Person",
        on_delete=models.CASCADE,
        related_name="horse_relationships",
    )
    relationship_type = models.CharField(max_length=24, choices=RelationshipType.choices)
    share_percent = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Optional participation share for lease/ownership arrangements, from 1 to 100.",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    credit_recipient = models.BooleanField(
        default=False,
        help_text="Use this person for earned credits generated from the horse's use.",
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["horse__name", "relationship_type", "person__last_name", "person__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["horse", "person", "relationship_type", "start_date"],
                name="unique_horse_person_relationship_period",
            ),
            models.UniqueConstraint(
                fields=["horse", "person", "relationship_type"],
                condition=models.Q(start_date__isnull=True),
                name="unique_horse_person_relationship_null_start",
            ),
            models.UniqueConstraint(
                fields=["horse"],
                condition=models.Q(active=True, credit_recipient=True),
                name="unique_active_horse_credit_recipient",
            ),
        ]

    def clean(self):
        super().clean()
        if self.horse_id and self.team_id and self.horse.team_id != self.team_id:
            raise ValidationError("Horse relationship must belong to the horse's organization.")
        if self.person_id and self.team_id and self.person.team_id != self.team_id:
            raise ValidationError("Horse relationship must belong to the person's organization.")
        if self.horse_id and self.person_id and self.horse.team_id != self.person.team_id:
            raise ValidationError("Horse and person must belong to the same organization.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Relationship end date cannot be before the start date.")
        if self.share_percent is not None and not 1 <= self.share_percent <= 100:
            raise ValidationError({"share_percent": "Share must be between 1 and 100 percent."})
        if self.credit_recipient and not self.active:
            raise ValidationError({"credit_recipient": "An inactive horse relationship cannot receive earned credits."})

    def __str__(self):
        return f"{self.horse} — {self.person} ({self.get_relationship_type_display()})"
