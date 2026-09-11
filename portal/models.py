from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils import timezone


class Team(models.Model):
    name = models.CharField(max_length=150)
    short_name = models.CharField(max_length=60, blank=True)
    discipline = models.CharField(
        max_length=30,
        choices=[
            ("hunt_seat", "Hunt Seat"),
            ("western", "Western"),
            ("dressage", "Dressage"),
            ("multi", "Multi-discipline"),
        ],
        default="hunt_seat",
    )
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="team_logos/", blank=True, null=True,
        help_text="Use only a logo your team is authorized to display.")

    def __str__(self):
        return self.name


class Season(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="seasons")
    name = models.CharField(max_length=50, help_text="Example: 2026–2027")
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False, help_text="Closed seasons are archived and protected from normal operational edits.")
    closed_at = models.DateTimeField(null=True, blank=True)
    futures_volunteer_hours_required = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    upper_volunteer_hours_required = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class ShowFeePolicy(models.TextChoices):
        INCLUDED = "included", "Included in membership dues"
        FAMILY = "family", "Bill families per show"
        PACKAGE = "package", "Season show package"
        MANUAL = "manual", "Manual / mixed"

    regular_show_fee_policy = models.CharField(max_length=20, choices=ShowFeePolicy.choices, default=ShowFeePolicy.MANUAL)
    regional_show_fee_policy = models.CharField(max_length=20, choices=ShowFeePolicy.choices, default=ShowFeePolicy.MANUAL)
    zone_show_fee_policy = models.CharField(max_length=20, choices=ShowFeePolicy.choices, default=ShowFeePolicy.MANUAL)
    national_show_fee_policy = models.CharField(max_length=20, choices=ShowFeePolicy.choices, default=ShowFeePolicy.MANUAL)
    other_show_fee_policy = models.CharField(max_length=20, choices=ShowFeePolicy.choices, default=ShowFeePolicy.MANUAL)
    default_rider_show_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    dues_coverage_notes = models.TextField(blank=True, help_text="Describe what membership dues or season packages cover.")

    def show_fee_policy_for(self, competition_level):
        return {
            "regular": self.regular_show_fee_policy,
            "regional": self.regional_show_fee_policy,
            "zone": self.zone_show_fee_policy,
            "national": self.national_show_fee_policy,
        }.get(competition_level, self.other_show_fee_policy)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.team} — {self.name}"


class AuditEvent(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PAID = "paid", "Paid"
        VOIDED = "voided", "Voided"
        RESTORED = "restored", "Restored"
        ALLOCATED = "allocated", "Allocated"
        REMOVED = "removed", "Removed"
        GENERATED = "generated", "Generated"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="audit_events")
    season = models.ForeignKey(
        "Season", on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events"
    )
    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="portal_audit_events"
    )
    action = models.CharField(max_length=24, choices=Action.choices)
    entity_type = models.CharField(max_length=80)
    entity_id = models.PositiveBigIntegerField(null=True, blank=True)
    entity_label = models.CharField(max_length=255)
    summary = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_action_display()} · {self.entity_label}"


class UserProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        COACH = "coach", "Coach"
        PARENT = "parent", "Parent/Guardian"
        RIDER = "rider", "Rider"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="user_profiles")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PARENT)
    phone = models.CharField(max_length=30, blank=True)
    must_change_password = models.BooleanField(default=False)
    email_announcements = models.BooleanField(default=True)
    email_show_updates = models.BooleanField(default=True)
    email_reminders = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class Rider(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="riders")
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="rider_record")
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    preferred_name = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    school = models.CharField(max_length=150, blank=True)
    grade = models.PositiveSmallIntegerField(null=True, blank=True)
    iea_member_number = models.CharField(max_length=40, blank=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="riders/", blank=True, null=True)
    active = models.BooleanField(default=True)
    # Legacy authorization relation retained for seamless upgrades. New parent details
    # live in GuardianContact / RiderGuardian.
    guardians = models.ManyToManyField(User, blank=True, related_name="guardian_riders")

    class Meta:
        ordering = ["last_name", "first_name"]

    @property
    def display_name(self):
        return self.preferred_name or self.first_name

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class GuardianContact(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="guardian_contacts")
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="guardian_contact")
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.display_name


class RiderGuardian(models.Model):
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="guardian_links")
    guardian = models.ForeignKey(GuardianContact, on_delete=models.CASCADE, related_name="rider_links")
    relationship = models.CharField(max_length=50, blank=True, help_text="Example: Parent, Mother, Father, Guardian")
    primary_contact = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["rider", "guardian"], name="unique_rider_guardian_contact")]

    def __str__(self):
        return f"{self.guardian} — {self.rider}"


class SeasonClass(models.Model):
    class TeamLevel(models.TextChoices):
        FUTURES = "futures", "Futures Team"
        UPPER = "upper", "Upper School Team"
        BOTH = "both", "Both teams"

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="season_classes")
    name = models.CharField(max_length=160)
    team_level = models.CharField(max_length=20, choices=TeamLevel.choices, default=TeamLevel.BOTH)
    discipline = models.CharField(
        max_length=30,
        choices=[
            ("hunt_seat", "Hunt Seat"),
            ("western", "Western"),
            ("dressage", "Dressage"),
            ("other", "Other"),
        ],
        default="hunt_seat",
    )
    sort_order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["team_level", "sort_order", "name"]
        constraints = [models.UniqueConstraint(fields=["season", "name", "team_level"], name="unique_season_class_by_team")]

    def __str__(self):
        return f"{self.get_team_level_display()} — {self.name}"


class SeasonMembership(models.Model):
    class TeamLevel(models.TextChoices):
        FUTURES = "futures", "Futures Team"
        UPPER = "upper", "Upper School Team"

    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="memberships")
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="memberships")
    team_level = models.CharField(max_length=20, choices=TeamLevel.choices, blank=True)
    home_barn = models.ForeignKey(
        "HomeBarn", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="season_memberships",
        help_text="The rider's home barn for this season. Stored on the season membership so barn changes preserve history.",
    )
    division = models.CharField(max_length=100, blank=True)
    class_level = models.CharField(max_length=100, blank=True)
    classes = models.ManyToManyField(SeasonClass, blank=True, related_name="rider_memberships")
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["rider", "season"], name="unique_rider_season")]

    def save(self, *args, **kwargs):
        if not self.team_level and self.rider.grade:
            if 4 <= self.rider.grade <= 8:
                self.team_level = self.TeamLevel.FUTURES
            elif 9 <= self.rider.grade <= 12:
                self.team_level = self.TeamLevel.UPPER
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.rider} — {self.season.name}"



class EventRSVP(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "No response"
        GOING = "going", "Going"
        MAYBE = "maybe", "Maybe"
        NOT_GOING = "not_going", "Not going"

    event = models.ForeignKey("CalendarEvent", on_delete=models.CASCADE, related_name="rsvps")
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="event_rsvps")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.CharField(max_length=255, blank=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="event_rsvp_responses")
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["rider__last_name", "rider__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["event", "rider"], name="unique_event_rider_rsvp")
        ]

    def save(self, *args, **kwargs):
        if self.status != self.Status.PENDING:
            self.responded_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.rider} — {self.event}"


class ActionItem(models.Model):
    class Category(models.TextChoices):
        RSVP = "rsvp", "RSVP / response"
        VOLUNTEER = "volunteer", "Volunteer"
        SUPPLY = "supply", "Bring / supply"
        PAPERWORK = "paperwork", "Paperwork"
        TASK = "task", "Task"
        OTHER = "other", "Other"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="action_items")
    season = models.ForeignKey(Season, on_delete=models.SET_NULL, null=True, blank=True, related_name="action_items")
    title = models.CharField(max_length=180)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.TASK)
    details = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    event = models.ForeignKey("CalendarEvent", on_delete=models.CASCADE, null=True, blank=True, related_name="action_items")
    show = models.ForeignKey("Show", on_delete=models.CASCADE, null=True, blank=True, related_name="action_items")
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, null=True, blank=True, related_name="action_items")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_action_items")
    claimed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="claimed_action_items")
    family_visible = models.BooleanField(default=True)
    claimable = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_action_items")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["completed", "due_at", "-created_at"]

    @property
    def owner(self):
        return self.claimed_by or self.assigned_to

    def save(self, *args, **kwargs):
        if self.completed and not self.completed_at:
            self.completed_at = timezone.now()
        elif not self.completed:
            self.completed_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Announcement(models.Model):
    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        IMPORTANT = "important", "Important"
        URGENT = "urgent", "Urgent"

    class Audience(models.TextChoices):
        ALL = "all", "Entire team"
        FUTURES = "futures", "Futures Team"
        UPPER = "upper", "Upper School Team"
        COACHES = "coaches", "Coaches / Admins"
        PARENTS = "parents", "Parents / Guardians"
        RIDERS = "riders", "Riders"
        SELECTED = "selected", "Selected users"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="announcements")
    season = models.ForeignKey(Season, on_delete=models.SET_NULL, null=True, blank=True, related_name="announcements")
    title = models.CharField(max_length=160)
    body = models.TextField()
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    selected_users = models.ManyToManyField(User, blank=True, related_name="selected_announcements")
    send_email = models.BooleanField(default=True)
    published = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_current(self):
        return self.published and (not self.expires_at or self.expires_at > timezone.now())


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="portal_notifications")
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    show_day_update = models.ForeignKey(
        "ShowDayUpdate", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_read(self):
        return bool(self.read_at)

    def __str__(self):
        return f"{self.user}: {self.title}"


class CommitteeAssignment(models.Model):
    class Role(models.TextChoices):
        UPPER_PARENT = "upper_parent", "Upper Team Parent"
        FUTURES_PARENT = "futures_parent", "Futures Team Parent"
        TREASURER = "treasurer", "Treasurer"
        POINTS_SECRETARY = "points_secretary", "Secretary / Points Secretary"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="committee_assignments")
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="committee_assignments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="committee_assignments")
    role = models.CharField(max_length=30, choices=Role.choices)
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["role", "user__last_name", "user__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["season", "user", "role"], name="unique_committee_assignment")
        ]

    def __str__(self):
        return f"{self.get_role_display()} — {self.user.get_full_name() or self.user.username}"


class ShowLeadAssignment(models.Model):
    show = models.ForeignKey("Show", on_delete=models.CASCADE, related_name="lead_assignments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="show_lead_assignments")
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["show", "user"], name="unique_show_lead_assignment")
        ]

    def __str__(self):
        return f"{self.show} — {self.user.get_full_name() or self.user.username}"


class ShowPlanningItem(models.Model):
    class Category(models.TextChoices):
        LUNCH = "lunch", "Lunch"
        SNACK = "snack", "Snack"
        DRINK = "drink", "Drink"
        SUPPLY = "supply", "Supply"
        TASK = "task", "Show-day task"
        OTHER = "other", "Other"

    class ItemType(models.TextChoices):
        CHECKLIST = "checklist", "Checklist"
        VOLUNTEER = "volunteer", "Volunteer"
        SUPPLY = "supply", "Supply / Hospitality"

    class TeamLevel(models.TextChoices):
        ALL = "all", "Everyone"
        FUTURES = "futures", "Futures Team"
        UPPER = "upper", "Upper School Team"

    show = models.ForeignKey("Show", on_delete=models.CASCADE, related_name="planning_items")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.TASK)
    item_type = models.CharField(max_length=20, choices=ItemType.choices, default=ItemType.CHECKLIST)
    team_level = models.CharField(max_length=20, choices=TeamLevel.choices, default=TeamLevel.ALL)
    title = models.CharField(max_length=160)
    quantity = models.CharField(max_length=60, blank=True)
    details = models.CharField(max_length=255, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="show_planning_items")
    claimed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="claimed_show_planning_items")
    completed = models.BooleanField(default=False)
    family_visible = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "category", "title"]

    @property
    def owner(self):
        return self.claimed_by or self.assigned_to

    def __str__(self):
        return f"{self.show} — {self.title}"


class ShowDayUpdate(models.Model):
    class Audience(models.TextChoices):
        ALL = "all", "Everyone"
        FUTURES = "futures", "Futures Team"
        UPPER = "upper", "Upper School Team"

    show = models.ForeignKey("Show", on_delete=models.CASCADE, related_name="day_updates")
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    title = models.CharField(max_length=160)
    body = models.TextField()
    send_email = models.BooleanField(default=True, help_text="Also email recipients who allow announcement email.")
    published = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="show_day_updates_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="show_day_updates_updated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def clean(self):
        super().clean()
        if self.audience not in {self.Audience.ALL, self.Audience.FUTURES, self.Audience.UPPER}:
            raise ValidationError("Choose a valid show-update audience.")

    def __str__(self):
        return f"{self.show} · {self.get_audience_display()} · {self.title}"


class RiderDevelopmentNote(models.Model):
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="development_notes")
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="development_notes")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="rider_development_notes")
    note = models.TextField()
    family_visible = models.BooleanField(default=False, help_text="Allow the rider and linked guardians to read this note.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rider} — {self.season.name}"


class RiderAward(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="awards")
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="awards")
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    presentation_date = models.DateField(null=True, blank=True)
    published = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="rider_awards_created")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["season__start_date", "title"]
        constraints = [
            models.UniqueConstraint(fields=["season", "rider", "title"], name="unique_season_rider_award")
        ]

    def __str__(self):
        return f"{self.title} — {self.rider}"


class CalendarEvent(models.Model):
    class Kind(models.TextChoices):
        SHOW = "show", "Show"
        LESSON = "lesson", "Lesson"
        MEETING = "meeting", "Meeting"
        DEADLINE = "deadline", "Deadline"
        SOCIAL = "social", "Social"
        OTHER = "other", "Other"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="events")
    season = models.ForeignKey(Season, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    title = models.CharField(max_length=160)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    visible_to_all = models.BooleanField(default=True)
    all_day = models.BooleanField(default=False)
    rsvp_requested = models.BooleanField(default=False, help_text="Ask riders/families to respond Going, Maybe, or Not going.")
    rsvp_deadline = models.DateTimeField(null=True, blank=True)
    show = models.OneToOneField("Show", on_delete=models.CASCADE, null=True, blank=True, related_name="calendar_event")
    lesson = models.OneToOneField("Lesson", on_delete=models.CASCADE, null=True, blank=True, related_name="calendar_event")

    class Meta:
        ordering = ["starts_at"]

    def __str__(self):
        return self.title


class Show(models.Model):
    class CompetitionLevel(models.TextChoices):
        REGULAR = "regular", "Regular season"
        REGIONAL = "regional", "Region Finals"
        ZONE = "zone", "Zone Finals"
        NATIONAL = "national", "National Finals"

    class FinancialRole(models.TextChoices):
        ATTENDING = "attending", "Attending"
        HOSTING_ATTENDING = "hosting_attending", "Hosting & attending"

    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        REGISTRATION = "registration", "Registration open"
        ENTERED = "entered", "Entries submitted"
        COMPLETE = "complete", "Complete"
        CANCELLED = "cancelled", "Cancelled"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="shows")
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="shows")
    name = models.CharField(max_length=180)
    show_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    venue = models.CharField(max_length=180, blank=True)
    address = models.CharField(max_length=255, blank=True)
    host_team = models.CharField(max_length=180, blank=True)
    iea_zone = models.CharField(max_length=40, blank=True)
    iea_region = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNING)
    financial_role = models.CharField(max_length=30, choices=FinancialRole.choices, default=FinancialRole.ATTENDING)
    competition_level = models.CharField(
        max_length=20,
        choices=CompetitionLevel.choices,
        default=CompetitionLevel.REGULAR,
    )
    entry_deadline = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_historical_import = models.BooleanField(
        default=False,
        help_text="Marks a show created through the historical-results workflow."
    )
    futures_team_place = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Overall Futures team placing at a finals show."
    )
    upper_team_place = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Overall Upper School team placing at a finals show."
    )

    class Meta:
        ordering = ["show_date", "name"]

    def __str__(self):
        return self.name


class ShowClass(models.Model):
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="classes")
    season_class = models.ForeignKey(SeasonClass, on_delete=models.PROTECT, null=True, blank=True, related_name="show_classes")
    # Legacy copies are kept for upgrade compatibility and snapshots of old data.
    name = models.CharField(max_length=160)
    division = models.CharField(max_length=120, blank=True)
    discipline = models.CharField(
        max_length=30,
        choices=[
            ("hunt_seat", "Hunt Seat"),
            ("western", "Western"),
            ("dressage", "Dressage"),
            ("other", "Other"),
        ],
        default="hunt_seat",
    )
    class_number = models.CharField(max_length=30, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    prize_list_time = models.TimeField(
        null=True, blank=True,
        help_text="Baseline time published in the prize list, if one is provided."
    )
    estimated_time = models.TimeField(
        null=True, blank=True,
        help_text="Current show-day estimate. This can move without changing the published prize-list time."
    )
    schedule_note = models.CharField(
        max_length=180, blank=True,
        help_text="Short public scheduling note, such as 'after lunch break' or 'Ring 2'."
    )

    class Meta:
        ordering = ["sort_order", "class_number", "name"]

    @property
    def display_name(self):
        return self.season_class.name if self.season_class else self.name

    @property
    def team_level(self):
        return self.season_class.team_level if self.season_class else "both"

    @property
    def schedule_time(self):
        """Current estimate, falling back to the prize-list baseline."""
        return self.estimated_time or self.prize_list_time

    def save(self, *args, **kwargs):
        if self.season_class:
            self.name = self.season_class.name
            self.discipline = self.season_class.discipline
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.show.name} — {self.display_name}"


class ShowEntry(models.Model):
    class CompetitionTrack(models.TextChoices):
        REGULAR = "regular", "Regular-season entry"
        INDIVIDUAL = "individual", "Individual finals"
        TEAM = "team", "Team finals"

    class EntryType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        TEAM = "team", "Team"
        BOTH = "both", "Individual + Team"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ENTERED = "entered", "Entered"
        SCRATCHED = "scratched", "Scratched"

    show_class = models.ForeignKey(ShowClass, on_delete=models.CASCADE, related_name="entries")
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="show_entries")
    competition_track = models.CharField(
        max_length=20,
        choices=CompetitionTrack.choices,
        default=CompetitionTrack.REGULAR,
    )
    entry_type = models.CharField(max_length=20, choices=EntryType.choices, default=EntryType.INDIVIDUAL)
    is_point_rider = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["show_class", "rider__last_name", "rider__first_name", "competition_track"]
        constraints = [
            models.UniqueConstraint(
                fields=["show_class", "rider", "competition_track"],
                name="unique_rider_show_class_track",
            )
        ]

    def clean(self):
        super().clean()
        if not self.show_class_id or not self.rider_id or not self.show_class.season_class_id:
            return

        show = self.show_class.show
        membership = SeasonMembership.objects.filter(rider=self.rider, season=show.season).first()
        if not membership:
            raise ValidationError("This rider is not on the roster for this show's season.")

        sc = self.show_class.season_class
        if sc.team_level != SeasonClass.TeamLevel.BOTH and membership.team_level != sc.team_level:
            raise ValidationError("This class belongs to a different team level than the rider's season roster.")
        if not membership.classes.filter(pk=sc.pk).exists():
            raise ValidationError("This rider is not assigned to this class for the season.")

        if show.competition_level == Show.CompetitionLevel.REGULAR:
            if self.competition_track != self.CompetitionTrack.REGULAR:
                raise ValidationError("Regular-season shows must use the regular-season competition track.")
            if self.is_point_rider:
                if self.entry_type == self.EntryType.INDIVIDUAL:
                    raise ValidationError("A points rider must be entered as Team or Individual + Team.")
                conflict_ids = []
                for other in self.show_class.entries.filter(
                    is_point_rider=True,
                    competition_track=self.CompetitionTrack.REGULAR,
                ).exclude(pk=self.pk).select_related("rider"):
                    other_membership = SeasonMembership.objects.filter(
                        rider=other.rider, season=show.season
                    ).first()
                    if other_membership and other_membership.team_level == membership.team_level:
                        conflict_ids.append(other.pk)
                if conflict_ids:
                    raise ValidationError(
                        f"A {membership.get_team_level_display()} points rider is already designated for this class."
                    )
        else:
            if self.competition_track == self.CompetitionTrack.REGULAR:
                raise ValidationError("Post-season entries must be marked Individual or Team.")
            class_code = (self.show_class.class_number or "").strip().upper()
            class_label = (self.show_class.display_name or "").strip().upper()
            if self.competition_track == self.CompetitionTrack.TEAM and (
                class_code in {"H8", "H14"}
                or class_label.startswith("H8 ")
                or class_label.startswith("H14 ")
                or class_label.startswith("H8-")
                or class_label.startswith("H14-")
            ):
                raise ValidationError("H8 and H14 Walk/Trot classes are individual-only and do not earn team points.")
            if self.is_point_rider:
                raise ValidationError("Post-season team entries are recorded on the Team track, not as regular-season point riders.")
            expected_type = (
                self.EntryType.INDIVIDUAL
                if self.competition_track == self.CompetitionTrack.INDIVIDUAL
                else self.EntryType.TEAM
            )
            self.entry_type = expected_type

    @property
    def result_or_none(self):
        try:
            return self.result
        except ObjectDoesNotExist:
            return None

    def __str__(self):
        return f"{self.rider} — {self.show_class.display_name}"


class ShowResult(models.Model):
    entry = models.OneToOneField(ShowEntry, on_delete=models.CASCADE, related_name="result")
    place = models.PositiveSmallIntegerField(null=True, blank=True)
    points = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    manual_points = models.BooleanField(default=False, help_text="Keep the entered points instead of calculating from placing.")
    horse_name = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    def save(self, *args, **kwargs):
        if not self.manual_points and self.place:
            config, _ = SeasonScoringConfig.objects.get_or_create(season=self.entry.show_class.show.season)
            self.points = config.points_for_place(self.place)
        elif not self.manual_points and not self.place:
            self.points = None
        super().save(*args, **kwargs)


class SeasonScoringConfig(models.Model):
    season = models.OneToOneField(Season, on_delete=models.CASCADE, related_name="scoring_config")
    first_points = models.DecimalField(max_digits=4, decimal_places=1, default=7)
    second_points = models.DecimalField(max_digits=4, decimal_places=1, default=5)
    third_points = models.DecimalField(max_digits=4, decimal_places=1, default=4)
    fourth_points = models.DecimalField(max_digits=4, decimal_places=1, default=3)
    fifth_points = models.DecimalField(max_digits=4, decimal_places=1, default=2)
    sixth_points = models.DecimalField(max_digits=4, decimal_places=1, default=1)
    individual_qualification_points = models.DecimalField(max_digits=5, decimal_places=1, default=18)
    team_qualification_points = models.DecimalField(max_digits=5, decimal_places=1, default=20)

    def points_for_place(self, place):
        return {
            1: self.first_points, 2: self.second_points, 3: self.third_points,
            4: self.fourth_points, 5: self.fifth_points, 6: self.sixth_points,
        }.get(place, 0)

    def __str__(self):
        return f"Scoring — {self.season.name}"


class QualificationOverride(models.Model):
    class Status(models.TextChoices):
        AUTO = "auto", "Automatic"
        QUALIFIED = "qualified", "Qualified"
        NOT_QUALIFIED = "not_qualified", "Not qualified"

    membership = models.ForeignKey(SeasonMembership, on_delete=models.CASCADE, related_name="qualification_overrides")
    season_class = models.ForeignKey(SeasonClass, on_delete=models.CASCADE, related_name="qualification_overrides")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AUTO)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["membership", "season_class"], name="unique_qualification_override")]

    def __str__(self):
        return f"{self.membership.rider} — {self.season_class.name}"


class LessonGroup(models.Model):
    class TeamLevel(models.TextChoices):
        FUTURES = "futures", "Futures Team"
        UPPER = "upper", "Upper School Team"
        BOTH = "both", "Both teams"

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="lesson_groups")
    name = models.CharField(max_length=120)
    team_level = models.CharField(max_length=20, choices=TeamLevel.choices, default=TeamLevel.BOTH)
    coach = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="lesson_groups_coached")
    riders = models.ManyToManyField(Rider, blank=True, related_name="lesson_groups")
    default_location = models.CharField(max_length=180, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["team_level", "name"]
        constraints = [models.UniqueConstraint(fields=["season", "name"], name="unique_lesson_group_season")]

    def __str__(self):
        return f"{self.name} — {self.season.name}"


class Lesson(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="lessons")
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="lessons")
    group = models.ForeignKey(LessonGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="lessons")
    coach = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="lessons_coached")
    title = models.CharField(max_length=160, default="Team lesson")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=180, blank=True)
    notes = models.TextField(blank=True)
    cancelled = models.BooleanField(default=False)

    class Meta:
        ordering = ["starts_at"]

    def __str__(self):
        return f"{self.title} — {timezone.localtime(self.starts_at):%b %d, %Y}"


class LessonAttendance(models.Model):
    class Status(models.TextChoices):
        EXPECTED = "expected", "Expected"
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        EXCUSED = "excused", "Excused"
        MAKEUP = "makeup", "Makeup"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="attendance")
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="lesson_attendance")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EXPECTED)
    horse_name = models.CharField(max_length=100, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["rider__last_name", "rider__first_name"]
        constraints = [models.UniqueConstraint(fields=["lesson", "rider"], name="unique_lesson_rider_attendance")]

    def __str__(self):
        return f"{self.rider} — {self.lesson}"


class ShowAvailability(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "No response"
        AVAILABLE = "available", "Available"
        CONDITIONAL = "conditional", "Available with conditions"
        UNAVAILABLE = "unavailable", "Unavailable"

    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="availability")
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="show_availability")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.CharField(max_length=255, blank=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="show_availability_responses")
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["rider__last_name", "rider__first_name"]
        constraints = [models.UniqueConstraint(fields=["show", "rider"], name="unique_show_rider_availability")]

    def save(self, *args, **kwargs):
        if self.status != self.Status.PENDING and not self.responded_at:
            self.responded_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.rider} — {self.show}"


class ShowDayRiderStatus(models.Model):
    class Status(models.TextChoices):
        EXPECTED = "expected", "Expected"
        ARRIVED = "arrived", "Arrived"
        RUNNING_LATE = "running_late", "Running Late"
        SCRATCHED = "scratched", "Scratched"
        FINISHED = "finished", "Finished / Left"

    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="rider_statuses")
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="show_day_statuses")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EXPECTED)
    note = models.CharField(max_length=180, blank=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="show_day_status_updates"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rider__last_name", "rider__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["show", "rider"], name="unique_show_day_rider_status")
        ]

    def clean(self):
        super().clean()
        if self.show_id and self.rider_id:
            if self.rider.team_id != self.show.team_id:
                raise ValidationError("Show-day rider status must belong to the same team as the show.")
            if not SeasonMembership.objects.filter(season=self.show.season, rider=self.rider).exists():
                raise ValidationError("This rider is not on the roster for the show's season.")

    def __str__(self):
        return f"{self.show} · {self.rider} · {self.get_status_display()}"


class VolunteerLog(models.Model):
    class Category(models.TextChoices):
        SHOW = "show", "Show support"
        BARN = "barn", "Barn/team support"
        FUNDRAISING = "fundraising", "Fundraising"
        TEAM = "team", "Team event"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="volunteer_logs")
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="volunteer_logs")
    service_date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.TEAM)
    performed_by = models.CharField(max_length=160, blank=True, help_text="Name of the family member/person who completed the hours.")
    description = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="volunteer_logs_submitted")
    submitted_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="volunteer_logs_approved")
    approved_at = models.DateTimeField(null=True, blank=True)
    coach_notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-service_date", "-submitted_at"]

    def clean(self):
        super().clean()
        if self.hours is not None and self.hours <= 0:
            raise ValidationError("Volunteer hours must be greater than zero.")
        if self.rider_id and self.season_id and self.rider.team_id != self.season.team_id:
            raise ValidationError("Rider and season must belong to the same team.")

    def __str__(self):
        return f"{self.rider} — {self.hours} hours"

class FinancialAccount(models.Model):
    class AccountType(models.TextChoices):
        CHECKING = "checking", "Checking"
        SAVINGS = "savings", "Savings"
        CASH = "cash", "Cash"
        CLEARING = "clearing", "Payment / clearing"
        OTHER = "other", "Other"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="financial_accounts")
    name = models.CharField(max_length=120)
    account_type = models.CharField(max_length=20, choices=AccountType.choices, default=AccountType.CHECKING)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["team", "name"], name="unique_financial_account_team_name")
        ]

    def __str__(self):
        return self.name


class FinancialCategory(models.Model):
    class Kind(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"
        BOTH = "both", "Income or expense"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="financial_categories")
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.EXPENSE)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["team", "name"], name="unique_financial_category_team_name")
        ]

    def __str__(self):
        return self.name


class FinancialTransaction(models.Model):
    class Kind(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    class ShowFinanceScope(models.TextChoices):
        PARTICIPATION = "participation", "Our team participation"
        HOSTING = "hosting", "Hosting operations"

    class Status(models.TextChoices):
        POSTED = "posted", "Posted"
        VOID = "void", "Void"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="financial_transactions")
    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name="financial_transactions")
    transaction_date = models.DateField()
    kind = models.CharField(max_length=20, choices=Kind.choices)
    account = models.ForeignKey(FinancialAccount, on_delete=models.PROTECT, related_name="transactions")
    category = models.ForeignKey(FinancialCategory, on_delete=models.PROTECT, related_name="transactions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payee = models.CharField(max_length=160, blank=True)
    description = models.CharField(max_length=255)
    show = models.ForeignKey("Show", on_delete=models.SET_NULL, null=True, blank=True, related_name="financial_transactions")
    show_finance_scope = models.CharField(max_length=20, choices=ShowFinanceScope.choices, blank=True)
    rider = models.ForeignKey(Rider, on_delete=models.SET_NULL, null=True, blank=True, related_name="financial_transactions")
    receipt = models.FileField(upload_to="finance/private/receipts/%Y/%m/", blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, help_text="Optional check number, payment reference, or external transaction ID.")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="financial_transactions_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="financial_transactions_updated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.POSTED)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="financial_transactions_voided")
    void_reason = models.CharField(max_length=255, blank=True)
    reversal_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="reversals")

    class Meta:
        ordering = ["-transaction_date", "-created_at"]

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError("Transaction amount must be greater than zero.")
        if self.account_id and self.account.team_id != self.team_id:
            raise ValidationError("Financial account must belong to the same team.")
        if self.category_id and self.category.team_id != self.team_id:
            raise ValidationError("Financial category must belong to the same team.")
        if self.season_id and self.season.team_id != self.team_id:
            raise ValidationError("Season must belong to the same team.")
        if self.show_id and self.show.team_id != self.team_id:
            raise ValidationError("Show must belong to the same team.")
        if self.show_finance_scope and not self.show_id:
            raise ValidationError("Show finance scope can only be used when a show is selected.")
        if self.show_finance_scope == self.ShowFinanceScope.HOSTING and self.show_id and self.show.financial_role != Show.FinancialRole.HOSTING_ATTENDING:
            raise ValidationError("Hosting operations scope is only valid for a show the team hosts.")
        if self.rider_id and self.rider.team_id != self.team_id:
            raise ValidationError("Rider must belong to the same team.")
        if self.category_id:
            allowed = {
                FinancialCategory.Kind.INCOME: {self.Kind.INCOME},
                FinancialCategory.Kind.EXPENSE: {self.Kind.EXPENSE},
                FinancialCategory.Kind.BOTH: {self.Kind.INCOME, self.Kind.EXPENSE},
            }[self.category.kind]
            if self.kind not in allowed:
                raise ValidationError("Transaction type does not match the selected category.")

        # Existing show allocations constrain later ledger edits. A transaction
        # cannot be reduced below its allocated total or moved into a season /
        # category / type that would make its allocations invalid.
        if self.pk:
            allocations = self.show_allocations.select_related("show", "budget_line")
            allocated_total = allocations.aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
            if self.amount is not None and allocated_total > self.amount:
                raise ValidationError(
                    f"Transaction amount cannot be less than its existing show allocations (${allocated_total:.2f})."
                )
            if self.season_id and allocations.exclude(show__season_id=self.season_id).exists():
                raise ValidationError(
                    "Transaction season cannot be changed while show allocations belong to another season."
                )
            for allocation in allocations.exclude(budget_line__isnull=True):
                if allocation.budget_line.category_id != self.category_id:
                    raise ValidationError(
                        "Transaction category cannot be changed while an allocation is tied to a budget item in another category."
                    )
                if allocation.budget_line.kind != self.kind:
                    raise ValidationError(
                        "Transaction type cannot be changed while an allocation is tied to a budget item of another type."
                    )

    def save(self, *args, **kwargs):
        old_receipt = None
        if self.pk:
            old_receipt = type(self).objects.filter(pk=self.pk).values_list("receipt", flat=True).first()
        super().save(*args, **kwargs)
        new_receipt = self.receipt.name if self.receipt else ""
        if old_receipt and old_receipt != new_receipt:
            self.receipt.storage.delete(old_receipt)

    def delete(self, *args, **kwargs):
        receipt_name = self.receipt.name if self.receipt else ""
        storage = self.receipt.storage if self.receipt else None
        result = super().delete(*args, **kwargs)
        if receipt_name and storage:
            storage.delete(receipt_name)
        return result

    def __str__(self):
        return f"{self.transaction_date} — {self.description} — ${self.amount}"


class ShowTransactionAllocation(models.Model):
    transaction = models.ForeignKey(
        FinancialTransaction, on_delete=models.CASCADE, related_name="show_allocations"
    )
    show = models.ForeignKey(
        "Show", on_delete=models.CASCADE, related_name="financial_allocations"
    )
    scope = models.CharField(
        max_length=20, choices=FinancialTransaction.ShowFinanceScope.choices
    )
    budget_line = models.ForeignKey(
        "ShowBudgetLine", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transaction_allocations"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["show__show_date", "show__name", "scope", "id"]

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError("Allocation amount must be greater than zero.")
        if self.transaction_id and self.show_id:
            if self.transaction.team_id != self.show.team_id:
                raise ValidationError("Allocated show must belong to the transaction's team.")
            if self.transaction.season_id != self.show.season_id:
                raise ValidationError("Allocated show must belong to the transaction's season.")
            if (
                self.scope == FinancialTransaction.ShowFinanceScope.HOSTING
                and self.show.financial_role != Show.FinancialRole.HOSTING_ATTENDING
            ):
                raise ValidationError("Hosting operations can only be allocated to a show the team hosts.")
        if self.budget_line_id:
            if self.budget_line.show_id != self.show_id:
                raise ValidationError("Selected budget item must belong to the allocated show.")
            if self.budget_line.scope != self.scope:
                raise ValidationError("Selected budget item must use the same Hosting/Participation scope.")
            if self.transaction_id and self.budget_line.category_id != self.transaction.category_id:
                raise ValidationError("Selected budget item must use the same financial category as the transaction.")
            if self.transaction_id and self.budget_line.kind != self.transaction.kind:
                raise ValidationError("Selected budget item must use the same income/expense type as the transaction.")
        if self.transaction_id and self.amount:
            existing = ShowTransactionAllocation.objects.filter(
                transaction_id=self.transaction_id
            ).exclude(pk=self.pk).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
            if existing + self.amount > self.transaction.amount:
                raise ValidationError(
                    f"Allocations cannot exceed the transaction amount of ${self.transaction.amount}."
                )

    def __str__(self):
        return f"{self.transaction.description} → {self.show.name} (${self.amount})"


class SeasonBudget(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="budgets")
    category = models.ForeignKey(FinancialCategory, on_delete=models.PROTECT, related_name="season_budgets")
    kind = models.CharField(max_length=20, choices=FinancialTransaction.Kind.choices, default=FinancialTransaction.Kind.EXPENSE)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.CharField(max_length=255, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="season_budgets_updated")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__sort_order", "category__name"]
        constraints = [
            models.UniqueConstraint(fields=["season", "category", "kind"], name="unique_season_budget_category_kind")
        ]

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount < 0:
            raise ValidationError("Budget amount cannot be negative.")
        if self.season_id and self.category_id and self.season.team_id != self.category.team_id:
            raise ValidationError("Budget category must belong to the season's team.")
        if self.category_id:
            allowed = {
                FinancialCategory.Kind.INCOME: {FinancialTransaction.Kind.INCOME},
                FinancialCategory.Kind.EXPENSE: {FinancialTransaction.Kind.EXPENSE},
                FinancialCategory.Kind.BOTH: {FinancialTransaction.Kind.INCOME, FinancialTransaction.Kind.EXPENSE},
            }[self.category.kind]
            if self.kind not in allowed:
                raise ValidationError("Budget type does not match the selected category.")

    def __str__(self):
        return f"{self.season.name} — {self.category.name} — {self.get_kind_display()}"

# --- v1.9.1 Family receivables and membership dues -------------------------

class HomeBarn(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_barns")
    name = models.CharField(max_length=150)
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["team", "name"], name="unique_home_barn_team_name")
        ]

    def __str__(self):
        return self.name


class MembershipDuesRate(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="membership_dues_rates")
    home_barn = models.ForeignKey(HomeBarn, on_delete=models.PROTECT, related_name="dues_rates")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["home_barn__name"]
        constraints = [
            models.UniqueConstraint(fields=["season", "home_barn"], name="unique_season_home_barn_dues_rate")
        ]

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount < 0:
            raise ValidationError("Membership dues cannot be negative.")
        if self.season_id and self.home_barn_id and self.season.team_id != self.home_barn.team_id:
            raise ValidationError("Home barn must belong to the same team as the season.")

    def __str__(self):
        return f"{self.season.name} — {self.home_barn.name} — ${self.amount}"


class FamilyCharge(models.Model):
    class ChargeType(models.TextChoices):
        MEMBERSHIP_DUES = "membership_dues", "Membership dues"
        SHOW_FEE = "show_fee", "Show fee"
        LESSON = "lesson", "Lesson / clinic"
        APPAREL = "apparel", "Apparel"
        TRAVEL = "travel", "Travel"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        WAIVED = "waived", "Waived"
        CLOSED = "closed", "Closed"

    membership = models.ForeignKey(SeasonMembership, on_delete=models.CASCADE, related_name="family_charges")
    charge_type = models.CharField(max_length=30, choices=ChargeType.choices, default=ChargeType.OTHER)
    description = models.CharField(max_length=180)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    charge_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    show = models.ForeignKey("Show", on_delete=models.SET_NULL, null=True, blank=True, related_name="family_charges")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    source_dues_rate = models.ForeignKey(MembershipDuesRate, on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_charges")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="family_charges_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "charge_date", "id"]

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount < 0:
            raise ValidationError("Charge amount cannot be negative.")
        if self.show_id and self.show.season_id != self.membership.season_id:
            raise ValidationError("The linked show must be from the rider's season.")

    @property
    def applied_credit_total(self):
        return sum((x.amount for x in self.credits.filter(status=FamilyCredit.Status.APPLIED)), Decimal("0"))

    @property
    def service_credit_total(self):
        return sum((x.amount for x in self.service_credits.filter(status=ServiceAgreementCredit.Status.APPLIED)), Decimal("0"))

    @property
    def assistance_total(self):
        eligible = self.assistance_claims.exclude(
            status__in=[AssistanceClaim.Status.DRAFT, AssistanceClaim.Status.DENIED, AssistanceClaim.Status.CANCELLED]
        )
        return sum((x.family_relief_amount for x in eligible), Decimal("0"))

    @property
    def payment_total(self):
        return sum(
            (x.amount for x in self.payments.filter(status=FamilyPayment.Status.POSTED)),
            Decimal("0"),
        )

    @property
    def balance(self):
        if self.status == self.Status.WAIVED:
            return Decimal("0")
        value = self.amount - self.applied_credit_total - self.service_credit_total - self.assistance_total - self.payment_total
        return max(value, Decimal("0"))

    def __str__(self):
        return f"{self.membership.rider} — {self.description}"


class FamilyCredit(models.Model):
    class CreditType(models.TextChoices):
        SCHOLARSHIP = "scholarship", "Scholarship / aid"
        COURTESY = "courtesy", "Courtesy credit"
        MANUAL = "manual", "Manual adjustment"
        FUNDRAISING = "fundraising", "Fundraising credit"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPLIED = "applied", "Applied"
        CANCELLED = "cancelled", "Cancelled"

    charge = models.ForeignKey(FamilyCharge, on_delete=models.CASCADE, related_name="credits")
    credit_type = models.CharField(max_length=30, choices=CreditType.choices, default=CreditType.MANUAL)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=150, blank=True, help_text="Who or what authorized/funded this credit.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="family_credits_created")
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError("Credit amount must be greater than zero.")

    def __str__(self):
        return f"{self.charge} — credit ${self.amount}"


class ServiceAgreementCredit(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPLIED = "applied", "Applied"
        CANCELLED = "cancelled", "Cancelled"

    membership = models.ForeignKey(SeasonMembership, on_delete=models.CASCADE, related_name="service_agreements")
    charge = models.ForeignKey(FamilyCharge, on_delete=models.CASCADE, related_name="service_credits")
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    required_shows = models.ManyToManyField("Show", blank=True, related_name="service_credit_agreements")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    completed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="service_agreements_created")
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError("Service credit must be greater than zero.")
        if self.charge_id and self.membership_id and self.charge.membership_id != self.membership_id:
            raise ValidationError("Service agreement must apply to a charge for the same rider season.")

    def __str__(self):
        return f"{self.membership.rider} — {self.description}"


class FinancialAssistanceAward(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXHAUSTED = "exhausted", "Exhausted"
        CLOSED = "closed", "Closed"

    membership = models.ForeignKey(SeasonMembership, on_delete=models.CASCADE, related_name="assistance_awards")
    provider = models.CharField(max_length=150, help_text="Example: IEA")
    program_name = models.CharField(max_length=180, blank=True)
    approved_maximum = models.DecimalField(max_digits=10, decimal_places=2)
    award_date = models.DateField(null=True, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    eligible_expenses = models.TextField(blank=True, help_text="Describe the expense types covered by this award.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assistance_awards_created")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def allocated_total(self):
        return sum(
            (c.family_relief_amount for c in self.claims.exclude(status__in=[AssistanceClaim.Status.DENIED, AssistanceClaim.Status.CANCELLED])),
            Decimal("0"),
        )

    @property
    def reimbursed_total(self):
        return sum((c.reimbursed_amount for c in self.claims.all()), Decimal("0"))

    @property
    def remaining_eligibility(self):
        return max(self.approved_maximum - self.allocated_total, Decimal("0"))

    def clean(self):
        super().clean()
        if self.approved_maximum is not None and self.approved_maximum <= 0:
            raise ValidationError("Approved award amount must be greater than zero.")

    def __str__(self):
        label = self.program_name or self.provider
        return f"{self.membership.rider} — {label}"


class AssistanceClaim(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Not submitted"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REIMBURSED = "reimbursed", "Reimbursed"
        DENIED = "denied", "Denied"
        CANCELLED = "cancelled", "Cancelled"

    award = models.ForeignKey(FinancialAssistanceAward, on_delete=models.CASCADE, related_name="claims")
    charge = models.ForeignKey(FamilyCharge, on_delete=models.PROTECT, related_name="assistance_claims")
    family_relief_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Amount of this charge covered by the award and removed from the family's responsibility.",
    )
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2)
    amount_approved = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reimbursed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    submitted_date = models.DateField(null=True, blank=True)
    approved_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    reimbursement_account = models.ForeignKey(FinancialAccount, on_delete=models.PROTECT, null=True, blank=True, related_name="assistance_claims")
    reimbursement_category = models.ForeignKey(FinancialCategory, on_delete=models.PROTECT, null=True, blank=True, related_name="assistance_claims")
    financial_transaction = models.OneToOneField(
        FinancialTransaction, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assistance_claim",
    )
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assistance_claims_updated")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_date", "-id"]

    def clean(self):
        super().clean()
        for value, label in [
            (self.family_relief_amount, "Family relief amount"),
            (self.amount_requested, "Requested amount"),
            (self.amount_approved, "Approved amount"),
            (self.reimbursed_amount, "Reimbursed amount"),
        ]:
            if value is not None and value < 0:
                raise ValidationError(f"{label} cannot be negative.")
        if self.charge_id and self.award_id and self.charge.membership_id != self.award.membership_id:
            raise ValidationError("Assistance claim and charge must belong to the same rider season.")
        if self.amount_requested and self.family_relief_amount and self.family_relief_amount > self.amount_requested:
            raise ValidationError("Family relief cannot exceed the amount requested.")
        if self.status == self.Status.REIMBURSED:
            if not self.received_date or not self.reimbursement_account_id or not self.reimbursement_category_id:
                raise ValidationError("Reimbursed claims require received date, account, and income category.")
            if self.reimbursed_amount <= 0:
                raise ValidationError("Enter the amount actually reimbursed.")
        if self.reimbursement_category_id and self.reimbursement_category.kind == FinancialCategory.Kind.EXPENSE:
            raise ValidationError("Reimbursement category must allow income.")

    def __str__(self):
        return f"{self.award} — {self.charge.description}"


class FamilyPayment(models.Model):
    class Status(models.TextChoices):
        POSTED = "posted", "Posted"
        VOID = "void", "Void"

    membership = models.ForeignKey(SeasonMembership, on_delete=models.CASCADE, related_name="family_payments")
    charge = models.ForeignKey(FamilyCharge, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    received_date = models.DateField(default=timezone.localdate)
    account = models.ForeignKey(FinancialAccount, on_delete=models.PROTECT, related_name="family_payments")
    category = models.ForeignKey(FinancialCategory, on_delete=models.PROTECT, related_name="family_payments")
    method = models.CharField(max_length=80, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    financial_transaction = models.OneToOneField(
        FinancialTransaction, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="family_payment",
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="family_payments_created")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.POSTED)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="family_payments_voided")
    void_reason = models.CharField(max_length=255, blank=True)

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
        if self.charge_id and self.membership_id and self.charge.membership_id != self.membership_id:
            raise ValidationError("Payment and charge must belong to the same rider season.")
        if self.account_id and self.account.team_id != self.membership.season.team_id:
            raise ValidationError("Payment account must belong to the team.")
        if self.category_id and self.category.team_id != self.membership.season.team_id:
            raise ValidationError("Payment category must belong to the team.")
        if self.category_id and self.category.kind == FinancialCategory.Kind.EXPENSE:
            raise ValidationError("Payment category must allow income.")

    def __str__(self):
        return f"{self.membership.rider} — payment ${self.amount}"



# --- v1.9.6 Fundraising -----------------------------------------------------

class FundraisingPolicy(models.Model):
    class Model(models.TextChoices):
        TEAM_WIDE = "team_wide", "Team-wide"
        FAMILY_CREDIT = "family_credit", "Family credit"
        HYBRID = "hybrid", "Hybrid"

    season = models.OneToOneField(Season, on_delete=models.CASCADE, related_name="fundraising_policy")
    model = models.CharField(max_length=24, choices=Model.choices, default=Model.TEAM_WIDE)
    default_family_credit_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Default percentage of an attributed contribution applied to the family account."
    )
    participation_optional = models.BooleanField(default=True)
    allowed_charge_types = models.JSONField(
        default=list, blank=True,
        help_text="Family charge types that fundraising credits may reduce. Empty means any charge type."
    )
    family_message = models.TextField(
        blank=True,
        help_text="Plain-language fundraising policy shown to linked Parent/Guardian accounts."
    )
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fundraising_policies_updated"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        pct = self.default_family_credit_percent
        if pct is not None and (pct < 0 or pct > 100):
            raise ValidationError("Default family credit percentage must be between 0 and 100.")
        if self.model == self.Model.TEAM_WIDE and pct:
            raise ValidationError("Team-wide fundraising must use a 0% default family credit.")
        if self.model == self.Model.FAMILY_CREDIT and pct != Decimal("100"):
            raise ValidationError("Family Credit fundraising uses a 100% default family credit.")
        valid_types = {value for value, _ in FamilyCharge.ChargeType.choices}
        invalid = set(self.allowed_charge_types or []) - valid_types
        if invalid:
            raise ValidationError("Fundraising policy contains an invalid family charge type.")

    def default_credit_for(self, amount):
        if self.model == self.Model.TEAM_WIDE:
            return Decimal("0")
        if self.model == self.Model.FAMILY_CREDIT:
            return amount
        pct = self.default_family_credit_percent or Decimal("0")
        return (amount * pct / Decimal("100")).quantize(Decimal("0.01"))

    def charge_type_allowed(self, charge):
        allowed = self.allowed_charge_types or []
        return not allowed or charge.charge_type in allowed

    def __str__(self):
        return f"{self.season.name} · {self.get_model_display()}"


class FundraisingCampaign(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="fundraising_campaigns")
    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name="fundraising_campaigns")
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    goal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="fundraising_campaigns_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-created_at", "name"]

    def clean(self):
        super().clean()
        if self.season_id and self.team_id and self.season.team_id != self.team_id:
            raise ValidationError("Fundraising campaign season must belong to the same team.")
        if self.goal_amount is not None and self.goal_amount < 0:
            raise ValidationError("Fundraising goal cannot be negative.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Campaign end date cannot be before its start date.")

    @property
    def posted_total(self):
        return self.contributions.filter(status=FundraisingContribution.Status.POSTED).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0")

    @property
    def family_credit_total(self):
        return self.contributions.filter(status=FundraisingContribution.Status.POSTED).aggregate(
            total=models.Sum("family_credit_amount")
        )["total"] or Decimal("0")

    @property
    def team_retained_total(self):
        return self.posted_total - self.family_credit_total

    @property
    def goal_remaining(self):
        if not self.goal_amount:
            return Decimal("0")
        return max(self.goal_amount - self.posted_total, Decimal("0"))

    @property
    def goal_percent(self):
        if not self.goal_amount:
            return 0
        return min(int((self.posted_total / self.goal_amount) * 100), 100)

    def __str__(self):
        return self.name


class FundraisingContribution(models.Model):
    class Status(models.TextChoices):
        POSTED = "posted", "Posted"
        VOID = "void", "Void"

    campaign = models.ForeignKey(FundraisingCampaign, on_delete=models.PROTECT, related_name="contributions")
    received_date = models.DateField(default=timezone.localdate)
    donor_name = models.CharField(max_length=180, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    beneficiary_membership = models.ForeignKey(
        SeasonMembership, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fundraising_contributions",
        help_text="Optional rider/family attribution for this contribution.",
    )
    family_credit_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Optional portion credited to the attributed family's receivable balance.",
    )
    family_charge = models.ForeignKey(
        FamilyCharge, on_delete=models.PROTECT, null=True, blank=True,
        related_name="fundraising_contributions",
        help_text="Required when a family credit is applied; choose the family charge to reduce.",
    )
    account = models.ForeignKey(FinancialAccount, on_delete=models.PROTECT, related_name="fundraising_contributions")
    category = models.ForeignKey(FinancialCategory, on_delete=models.PROTECT, related_name="fundraising_contributions")
    method = models.CharField(max_length=80, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.POSTED)
    financial_transaction = models.OneToOneField(
        FinancialTransaction, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fundraising_contribution",
    )
    family_credit = models.OneToOneField(
        FamilyCredit, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fundraising_contribution",
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="fundraising_contributions_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="fundraising_contributions_voided")
    void_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-received_date", "-created_at"]

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError("Fundraising contribution amount must be greater than zero.")
        if self.family_credit_amount is not None and self.family_credit_amount < 0:
            raise ValidationError("Family credit cannot be negative.")
        if self.family_credit_amount and self.amount and self.family_credit_amount > self.amount:
            raise ValidationError("Family credit cannot exceed the contribution amount.")
        if self.campaign_id:
            if self.account_id and self.account.team_id != self.campaign.team_id:
                raise ValidationError("Fundraising account must belong to the campaign team.")
            if self.category_id and self.category.team_id != self.campaign.team_id:
                raise ValidationError("Fundraising category must belong to the campaign team.")
            if self.category_id and self.category.kind == FinancialCategory.Kind.EXPENSE:
                raise ValidationError("Fundraising contributions require an income-capable category.")
            if self.beneficiary_membership_id:
                if self.beneficiary_membership.season_id != self.campaign.season_id:
                    raise ValidationError("Attributed rider/family must belong to the campaign season.")
            if self.family_credit_amount:
                if not self.beneficiary_membership_id:
                    raise ValidationError("Choose a rider/family before applying a fundraising family credit.")
                if not self.family_charge_id:
                    raise ValidationError("Choose the family charge that the fundraising credit should reduce.")
                if self.family_charge.membership_id != self.beneficiary_membership_id:
                    raise ValidationError("Fundraising family credit must apply to a charge for the attributed rider/family.")

    @property
    def team_retained_amount(self):
        return self.amount - (self.family_credit_amount or Decimal("0"))

    def __str__(self):
        donor = self.donor_name or "Anonymous"
        return f"{self.campaign.name} · {donor} · ${self.amount:.2f}"


# --- v1.9.4 Show finance & funding policies -------------------------------

class ShowBudgetLine(models.Model):
    class Scope(models.TextChoices):
        PARTICIPATION = "participation", "Our team participation"
        HOSTING = "hosting", "Hosting operations"

    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="show_budget_lines")
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.PARTICIPATION)
    category = models.ForeignKey(FinancialCategory, on_delete=models.PROTECT, related_name="show_budget_lines")
    kind = models.CharField(max_length=20, choices=FinancialTransaction.Kind.choices, default=FinancialTransaction.Kind.EXPENSE)
    description = models.CharField(max_length=160, help_text="Specific budget item, such as Insurance, Judge fee, Food, or Facility rental.")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["scope", "kind", "category__sort_order", "category__name", "description", "id"]

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount < 0:
            raise ValidationError("Show budget amount cannot be negative.")
        if self.show_id and self.category_id and self.show.team_id != self.category.team_id:
            raise ValidationError("Budget category must belong to the show's team.")
        if self.scope == self.Scope.HOSTING and self.show_id and self.show.financial_role != Show.FinancialRole.HOSTING_ATTENDING:
            raise ValidationError("Hosting budget lines are only available for shows the team hosts.")

    def __str__(self):
        description = self.description or (self.category.name if self.category_id else "Budget item")
        category = self.category.name if self.category_id else "Uncategorized"
        return f"{description} · {category} · ${self.amount:.2f}"


class ReimbursementRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PAID = "paid", "Paid"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="reimbursement_requests")
    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name="reimbursement_requests")
    show = models.ForeignKey(Show, on_delete=models.SET_NULL, null=True, blank=True, related_name="reimbursement_requests")
    show_finance_scope = models.CharField(max_length=20, choices=FinancialTransaction.ShowFinanceScope.choices, blank=True)
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reimbursement_requests")
    payee_name = models.CharField(max_length=160)
    expense_date = models.DateField(default=timezone.localdate)
    category = models.ForeignKey(FinancialCategory, on_delete=models.PROTECT, related_name="reimbursement_requests")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    receipt = models.FileField(upload_to="finance/private/reimbursements/%Y/%m/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reimbursements_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    paid_date = models.DateField(null=True, blank=True)
    payment_account = models.ForeignKey(FinancialAccount, on_delete=models.PROTECT, null=True, blank=True, related_name="reimbursements_paid")
    financial_transaction = models.OneToOneField(FinancialTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name="reimbursement_request")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError("Reimbursement amount must be greater than zero.")
        if self.season_id and self.team_id and self.season.team_id != self.team_id:
            raise ValidationError("Season must belong to the team.")
        if self.show_id and self.show.season_id != self.season_id:
            raise ValidationError("Show must belong to the selected season.")
        if self.show_id and not self.show_finance_scope:
            raise ValidationError("Choose Hosting operations or Our team participation for a show-linked reimbursement.")
        if self.show_finance_scope and not self.show_id:
            raise ValidationError("Show finance scope requires a linked show.")
        if self.show_finance_scope == FinancialTransaction.ShowFinanceScope.HOSTING and self.show_id and self.show.financial_role != Show.FinancialRole.HOSTING_ATTENDING:
            raise ValidationError("Hosting operations can only be used for a show the team hosts.")
        if self.category_id and self.category.team_id != self.team_id:
            raise ValidationError("Category must belong to the team.")
        if self.category_id and self.category.kind == FinancialCategory.Kind.INCOME:
            raise ValidationError("Reimbursements require an expense category.")
        if self.status == self.Status.PAID and (not self.paid_date or not self.payment_account_id):
            raise ValidationError("Paid reimbursements require a paid date and payment account.")

    def __str__(self):
        return f"{self.payee_name} — {self.description} — ${self.amount}"
