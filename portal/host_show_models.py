from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .models import Show


class HostShowOperations(models.Model):
    show = models.OneToOneField(Show, on_delete=models.CASCADE, related_name="host_operations")

    show_manager_name = models.CharField(max_length=160, blank=True)
    show_manager_email = models.EmailField(blank=True)
    show_manager_phone = models.CharField(max_length=40, blank=True)
    venue_contact = models.CharField(max_length=160, blank=True)
    venue_contact_phone = models.CharField(max_length=40, blank=True)

    arrival_instructions = models.TextField(blank=True)
    check_in_location = models.CharField(max_length=180, blank=True)
    trailer_parking = models.TextField(blank=True)
    spectator_parking = models.TextField(blank=True)
    warmup_schooling = models.TextField(blank=True)
    ring_operations = models.TextField(blank=True)
    hospitality = models.TextField(blank=True)
    volunteer_check_in = models.TextField(blank=True)
    emergency_information = models.TextField(blank=True)

    prize_list_url = models.URLField(blank=True)
    schedule_url = models.URLField(blank=True)
    family_notes = models.TextField(
        blank=True,
        help_text="Operational information appropriate for riders and families.",
    )
    internal_notes = models.TextField(
        blank=True,
        help_text="Private host-team notes for Coaches/Admins.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_host_show_operations",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_host_show_operations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["show__show_date", "show__name"]

    def clean(self):
        super().clean()
        if self.show_id and self.show.financial_role != Show.FinancialRole.HOSTING_ATTENDING:
            raise ValidationError("Host Show Operations is only available for shows marked Hosting & attending.")

    @property
    def readiness_items(self):
        return [
            ("Show manager", bool(self.show_manager_name)),
            ("Arrival instructions", bool(self.arrival_instructions)),
            ("Check-in location", bool(self.check_in_location)),
            ("Trailer parking", bool(self.trailer_parking)),
            ("Warm-up / schooling", bool(self.warmup_schooling)),
            ("Ring operations", bool(self.ring_operations)),
            ("Volunteer check-in", bool(self.volunteer_check_in)),
            ("Emergency information", bool(self.emergency_information)),
        ]

    @property
    def readiness_complete(self):
        items = self.readiness_items
        return bool(items) and all(ready for _, ready in items)

    @property
    def readiness_percent(self):
        items = self.readiness_items
        if not items:
            return 0
        complete = sum(1 for _, ready in items if ready)
        return round((complete / len(items)) * 100)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.show.name} — Host Show Operations"
