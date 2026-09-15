from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class HorseDocument(models.Model):
    """Durable document attached to ArenaLine's canonical Horse.

    Specialized compliance records, such as Coggins, remain their own source of
    truth. This model holds supporting and general horse documents without
    duplicating those domain records.
    """

    class DocumentType(models.TextChoices):
        REGISTRATION = "registration", "Registration papers"
        VACCINATION = "vaccination", "Vaccination record"
        LEASE = "lease", "Lease agreement"
        OWNERSHIP = "ownership", "Ownership document"
        VETERINARY = "veterinary", "Veterinary document"
        INSURANCE = "insurance", "Insurance document"
        CARE = "care", "Care document"
        OTHER = "other", "Other"

    horse = models.ForeignKey("portal.Horse", on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=24, choices=DocumentType.choices)
    title = models.CharField(max_length=160)
    file = models.FileField(upload_to="horses/documents/%Y/%m/")
    effective_date = models.DateField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    care_record = models.ForeignKey(
        "portal.HorseCareRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        help_text="Optional care event this document supports.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["document_type", "title", "-effective_date", "-id"]
        indexes = [
            models.Index(fields=["horse", "expiration_date"], name="horse_doc_expiry_idx"),
            models.Index(fields=["document_type", "expiration_date"], name="horse_doc_type_exp_idx"),
        ]

    def clean(self):
        super().clean()
        if self.expiration_date and self.effective_date and self.expiration_date < self.effective_date:
            raise ValidationError({"expiration_date": "Expiration date cannot be before the effective date."})
        if self.care_record_id and self.horse_id and self.care_record.horse_id != self.horse_id:
            raise ValidationError({"care_record": "Linked care record must belong to this horse."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def expiration_status(self):
        if not self.expiration_date:
            return "none"
        today = timezone.localdate()
        if self.expiration_date < today:
            return "expired"
        if self.expiration_date <= today + timedelta(days=30):
            return "expiring"
        return "current"

    @property
    def expiration_status_label(self):
        return {
            "none": "No expiration",
            "expired": "Expired",
            "expiring": "Expiring soon",
            "current": "Current",
        }[self.expiration_status]

    def __str__(self):
        return f"{self.horse.display_name} — {self.title}"
