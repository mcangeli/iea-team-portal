"""ArenaLine Station shared-device identity and work-shift foundation."""

import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class StationDevice(models.Model):
    """A registered shared device permitted to use ArenaLine Station."""

    team = models.ForeignKey(
        "portal.Team",
        on_delete=models.CASCADE,
        related_name="station_devices",
    )
    name = models.CharField(max_length=120)
    device_key = models.CharField(max_length=64, unique=True, editable=False)
    secret_hash = models.CharField(max_length=128, editable=False)
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["team", "name"], name="unique_station_device_name_per_team"),
        ]

    def save(self, *args, **kwargs):
        if not self.device_key:
            self.device_key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def set_secret(self, raw_secret):
        if not raw_secret or len(raw_secret) < 16:
            raise ValidationError("Station device secrets must be at least 16 characters.")
        self.secret_hash = make_password(raw_secret)

    def check_secret(self, raw_secret):
        return bool(self.secret_hash and raw_secret and check_password(raw_secret, self.secret_hash))

    def __str__(self):
        return self.name


class StationCredential(models.Model):
    """Limited shared-device identity for a Person; never stores a portal password."""

    team = models.ForeignKey(
        "portal.Team",
        on_delete=models.CASCADE,
        related_name="station_credentials",
    )
    person = models.OneToOneField(
        "portal.Person",
        on_delete=models.CASCADE,
        related_name="station_credential",
    )
    pin_hash = models.CharField(max_length=128, editable=False)
    active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["person__last_name", "person__first_name", "id"]

    def clean(self):
        super().clean()
        if self.person_id and self.team_id and self.person.team_id != self.team_id:
            raise ValidationError("Station credential and person must belong to the same organization.")

    def set_pin(self, raw_pin):
        pin = str(raw_pin or "").strip()
        if not pin.isdigit() or not 4 <= len(pin) <= 8:
            raise ValidationError("Station PIN must contain 4 to 8 digits.")
        self.pin_hash = make_password(pin)

    def check_pin(self, raw_pin):
        pin = str(raw_pin or "").strip()
        return bool(self.pin_hash and pin and check_password(pin, self.pin_hash))

    def __str__(self):
        return f"Station identity — {self.person}"


class WorkShiftEntry(models.Model):
    """Clock-in/out record created from Station or later manager workflows."""

    class Role(models.TextChoices):
        WORKING_STUDENT = "working_student", "Working Student"
        BARN_STAFF = "barn_staff", "Barn Staff"
        BARN_MANAGER = "barn_manager", "Barn Manager"
        TRAINER = "trainer", "Trainer"
        ASSISTANT_TRAINER = "assistant_trainer", "Assistant Trainer"
        OTHER = "other", "Other"

    team = models.ForeignKey(
        "portal.Team",
        on_delete=models.CASCADE,
        related_name="work_shift_entries",
    )
    person = models.ForeignKey(
        "portal.Person",
        on_delete=models.PROTECT,
        related_name="work_shift_entries",
    )
    station = models.ForeignKey(
        StationDevice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_shift_entries",
    )
    role = models.CharField(max_length=24, choices=Role.choices, default=Role.WORKING_STUDENT)
    clock_in = models.DateTimeField()
    clock_out = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    approved_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_work_shift_entries",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-clock_in", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["person"],
                condition=Q(clock_out__isnull=True),
                name="unique_open_work_shift_per_person",
            ),
        ]

    def clean(self):
        super().clean()
        if self.person_id and self.team_id and self.person.team_id != self.team_id:
            raise ValidationError("Work shift and person must belong to the same organization.")
        if self.station_id and self.team_id and self.station.team_id != self.team_id:
            raise ValidationError("Work shift and station must belong to the same organization.")
        if self.clock_in and self.clock_out and self.clock_out < self.clock_in:
            raise ValidationError("Clock-out time cannot be before clock-in time.")
        if self.approved_by_id and self.team_id:
            # Query the persisted profile rather than relying on the reverse
            # one-to-one cache on User, which can be stale after profile updates.
            from portal.models import UserProfile

            approver_team_id = (
                UserProfile.objects.filter(user_id=self.approved_by_id)
                .values_list("team_id", flat=True)
                .first()
            )
            if approver_team_id != self.team_id:
                raise ValidationError("Shift approver must belong to the same organization.")

    @property
    def is_open(self):
        return self.clock_out is None

    def __str__(self):
        return f"{self.person} — {self.clock_in:%Y-%m-%d %H:%M}"
