from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .models import Show


class ShowManagerAssignment(models.Model):
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="manager_assignments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="show_manager_assignments",
    )
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name", "user__username"]
        constraints = [
            models.UniqueConstraint(fields=["show", "user"], name="unique_show_manager_assignment")
        ]

    def clean(self):
        super().clean()
        if self.show_id and self.show.financial_role != Show.FinancialRole.HOSTING_ATTENDING:
            raise ValidationError("A Show Manager can only be assigned to a hosted show.")
        if self.user_id and self.show_id:
            profile = getattr(self.user, "profile", None)
            if profile and profile.team_id and profile.team_id != self.show.team_id:
                raise ValidationError("The Show Manager must belong to the same team as the show.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.show} — {self.user.get_full_name() or self.user.username} (Show Manager)"


class HostShowOperations(models.Model):
    show = models.OneToOneField(Show, on_delete=models.CASCADE, related_name="host_operations")

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
        help_text="Private host-team notes for Coaches/Admins and the assigned Show Manager.",
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
            ("Show Manager", self.show.manager_assignments.filter(active=True).exists()),
            ("Show Secretary", self.staff_assignments.filter(role=HostShowStaffAssignment.Role.SECRETARY, active=True).exists()),
            ("Judge", self.staff_assignments.filter(role=HostShowStaffAssignment.Role.JUDGE, active=True).exists()),
            ("Steward", self.staff_assignments.filter(role=HostShowStaffAssignment.Role.STEWARD, active=True).exists()),
            ("Gate", self.staff_assignments.filter(role=HostShowStaffAssignment.Role.GATE, active=True).exists()),
            ("Announcer", self.staff_assignments.filter(role=HostShowStaffAssignment.Role.ANNOUNCER, active=True).exists()),
            ("EMS", self.staff_assignments.filter(role=HostShowStaffAssignment.Role.EMS, active=True).exists()),
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


class HostShowStaffAssignment(models.Model):
    class Role(models.TextChoices):
        SECRETARY = "secretary", "Show Secretary"
        JUDGE = "judge", "Judge"
        STEWARD = "steward", "Steward"
        GATE = "gate", "Gate"
        ANNOUNCER = "announcer", "Show Announcer"
        EMS = "ems", "EMS"
        OTHER = "other", "Other"

    operations = models.ForeignKey(
        HostShowOperations,
        on_delete=models.CASCADE,
        related_name="staff_assignments",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    name = models.CharField(max_length=160)
    organization = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    notes = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "role", "name"]

    def __str__(self):
        return f"{self.get_role_display()} — {self.name}"


class HostShowReadinessCheckpoint(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETE = "complete", "Complete"
        WAIVED = "waived", "Waived"

    operations = models.ForeignKey(
        HostShowOperations,
        on_delete=models.CASCADE,
        related_name="readiness_checkpoints",
    )
    title = models.CharField(max_length=180)
    due_at = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="host_show_readiness_checkpoints",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    notes = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "due_at", "sort_order", "title"]

    @property
    def is_done(self):
        return self.status in {self.Status.COMPLETE, self.Status.WAIVED}

    def __str__(self):
        return f"{self.operations.show.name} — {self.title}"


class HostShowDutyAssignment(models.Model):
    class Area(models.TextChoices):
        GATE = "gate", "Gate / in-gate"
        RING = "ring", "Ring operations"
        WARMUP = "warmup", "Warm-up / schooling"
        CHECKIN = "checkin", "Check-in / secretary"
        PARKING = "parking", "Parking / traffic"
        HOSPITALITY = "hospitality", "Hospitality"
        HORSES = "horses", "Horse operations"
        RUNNER = "runner", "Runner / communications"
        SETUP = "setup", "Setup / teardown"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        CHECKED_IN = "checked_in", "Checked in"
        ACTIVE = "active", "On duty"
        HANDED_OFF = "handed_off", "Handed off"
        COMPLETE = "complete", "Complete"

    operations = models.ForeignKey(
        HostShowOperations,
        on_delete=models.CASCADE,
        related_name="duty_assignments",
    )
    area = models.CharField(max_length=20, choices=Area.choices, default=Area.OTHER)
    title = models.CharField(max_length=180)
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="host_show_duties",
    )
    assigned_name = models.CharField(
        max_length=160,
        blank=True,
        help_text="Use for a volunteer or staff member without a portal login.",
    )
    location = models.CharField(max_length=160, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    instructions = models.TextField(blank=True)
    handoff_notes = models.TextField(blank=True)
    relieved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="host_show_duty_handoffs",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["starts_at", "sort_order", "area", "title"]

    def clean(self):
        super().clean()
        if not self.assigned_user_id and not self.assigned_name.strip():
            raise ValidationError("Assign a team user or enter the volunteer/staff member's name.")
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise ValidationError("Duty end time cannot be before its start time.")
        if self.assigned_user_id:
            profile = getattr(self.assigned_user, "profile", None)
            if profile and profile.team_id and profile.team_id != self.operations.show.team_id:
                raise ValidationError("Assigned team user must belong to the same team as the show.")

    @property
    def assignee_name(self):
        if self.assigned_user_id:
            return self.assigned_user.get_full_name() or self.assigned_user.username
        return self.assigned_name

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.operations.show.name} — {self.title} — {self.assignee_name}"