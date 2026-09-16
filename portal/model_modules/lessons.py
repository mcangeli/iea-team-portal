from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from portal.models import Season, SeasonMembership, Team


class LessonProgram(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="lesson_programs")
    group = models.ForeignKey("portal.OrganizationGroup", on_delete=models.PROTECT, null=True, blank=True, related_name="lesson_programs")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    default_capacity = models.PositiveSmallIntegerField(null=True, blank=True)
    enrollment_opens = models.DateField(null=True, blank=True)
    enrollment_closes = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["name", "id"]
        constraints = [models.UniqueConstraint(fields=["team", "name"], name="unique_lesson_program_team_name")]
    def clean(self):
        super().clean()
        if self.default_capacity is not None and self.default_capacity < 1: raise ValidationError({"default_capacity": "Capacity must be at least 1."})
        if self.enrollment_opens and self.enrollment_closes and self.enrollment_closes < self.enrollment_opens: raise ValidationError("Enrollment close date cannot be before the open date.")
        if self.group_id:
            if self.group.team_id != self.team_id: raise ValidationError("Lesson program group must belong to the same organization.")
            if self.group.group_type != self.group.GroupType.PROGRAM: raise ValidationError("Lesson programs may only use an organization Program group.")
    def __str__(self): return self.name


class LessonSeries(models.Model):
    program = models.ForeignKey(LessonProgram, on_delete=models.CASCADE, related_name="series")
    name = models.CharField(max_length=160)
    instructor = models.ForeignKey("portal.Person", on_delete=models.PROTECT, null=True, blank=True, related_name="lesson_series_instructed")
    weekday = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Monday=0 through Sunday=6.")
    starts_at_time = models.TimeField(null=True, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    default_location = models.CharField(max_length=180, blank=True)
    capacity = models.PositiveSmallIntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["program__name", "name", "id"]
        constraints = [models.UniqueConstraint(fields=["program", "name"], name="unique_lesson_series_program_name")]
    @property
    def effective_capacity(self): return self.capacity if self.capacity is not None else self.program.default_capacity
    @property
    def is_iea_series(self): return hasattr(self, "iea_context")
    def clean(self):
        super().clean()
        if self.weekday is not None and not 0 <= self.weekday <= 6: raise ValidationError({"weekday": "Weekday must be between 0 and 6."})
        if self.duration_minutes is not None and self.duration_minutes < 1: raise ValidationError({"duration_minutes": "Duration must be at least 1 minute."})
        if self.capacity is not None and self.capacity < 1: raise ValidationError({"capacity": "Capacity must be at least 1."})
        if self.start_date and self.end_date and self.end_date < self.start_date: raise ValidationError("Series end date cannot be before the start date.")
        if self.instructor_id and self.instructor.team_id != self.program.team_id: raise ValidationError("Lesson series instructor must belong to the same organization.")
    def __str__(self): return f"{self.program.name} — {self.name}"


class IEALessonSeriesContext(models.Model):
    class TeamLevel(models.TextChoices):
        FUTURES = SeasonMembership.TeamLevel.FUTURES, "Futures Team"
        UPPER = SeasonMembership.TeamLevel.UPPER, "Upper School Team"
    series = models.OneToOneField(LessonSeries, on_delete=models.CASCADE, related_name="iea_context")
    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name="iea_lesson_series")
    team_level = models.CharField(max_length=20, choices=TeamLevel.choices)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-season__start_date", "team_level", "series__name", "id"]
        constraints = [models.UniqueConstraint(fields=["season", "team_level", "series"], name="unique_iea_lesson_series_context")]
    def clean(self):
        super().clean()
        if self.series_id and self.season_id and self.series.program.team_id != self.season.team_id: raise ValidationError("IEA lesson series and season must belong to the same organization.")
        if self.team_level not in {self.TeamLevel.FUTURES, self.TeamLevel.UPPER}: raise ValidationError({"team_level": "IEA lesson series must be Futures or Upper School."})
    def __str__(self): return f"{self.season.name} · {self.get_team_level_display()} · {self.series.name}"


class LessonEnrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WAITLISTED = "waitlisted", "Waitlisted"
        WITHDRAWN = "withdrawn", "Withdrawn"
        COMPLETED = "completed", "Completed"
    series = models.ForeignKey(LessonSeries, on_delete=models.CASCADE, related_name="enrollments")
    person = models.ForeignKey("portal.Person", on_delete=models.PROTECT, related_name="lesson_enrollments")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["person__last_name", "person__first_name", "id"]
        constraints = [models.UniqueConstraint(fields=["series", "person"], name="unique_lesson_series_person_enrollment")]
    def clean(self):
        super().clean()
        if self.series_id and self.series.is_iea_series: raise ValidationError("IEA team lesson rosters come from season team membership, not barn lesson enrollment.")
        if self.person_id and self.person.team_id != self.series.program.team_id: raise ValidationError("Lesson enrollment must remain within one organization.")
        if self.start_date and self.end_date and self.end_date < self.start_date: raise ValidationError("Enrollment end date cannot be before the start date.")
    def __str__(self): return f"{self.person} — {self.series}"


class LessonOccurrence(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        RESCHEDULED = "rescheduled", "Rescheduled"
    class Origin(models.TextChoices):
        GENERATED = "generated", "Generated"
        MANUAL = "manual", "Manual"
        LEGACY = "legacy", "Legacy conversion"
    series = models.ForeignKey(LessonSeries, on_delete=models.PROTECT, related_name="occurrences")
    title = models.CharField(max_length=160)
    instructor = models.ForeignKey("portal.Person", on_delete=models.PROTECT, null=True, blank=True, related_name="lesson_occurrences_instructed")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    origin = models.CharField(max_length=12, choices=Origin.choices, default=Origin.MANUAL)
    scheduled_for = models.DateTimeField(null=True, blank=True, help_text="Immutable recurrence slot for generated occurrences.")
    location = models.CharField(max_length=180, blank=True)
    capacity = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SCHEDULED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["starts_at", "id"]
        constraints = [models.UniqueConstraint(fields=["series", "scheduled_for"], name="unique_lesson_series_scheduled_slot")]
    def clean(self):
        super().clean()
        if self.ends_at and self.ends_at <= self.starts_at: raise ValidationError("Lesson occurrence end time must be after its start time.")
        if self.capacity is not None and self.capacity < 1: raise ValidationError({"capacity": "Capacity must be at least 1."})
        if self.instructor_id and self.instructor.team_id != self.series.program.team_id: raise ValidationError("Lesson occurrence instructor must belong to the same organization.")
        if self.origin == self.Origin.GENERATED and self.scheduled_for is None: raise ValidationError({"scheduled_for": "Generated lesson occurrences require their original recurrence slot."})
        if self.origin != self.Origin.GENERATED and self.scheduled_for is not None: raise ValidationError({"scheduled_for": "Only generated lesson occurrences may have a recurrence slot."})
    def __str__(self): return f"{self.title} — {self.starts_at:%Y-%m-%d}"


class LessonAttendanceRecord(models.Model):
    class Status(models.TextChoices):
        EXPECTED = "expected", "Expected"
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        EXCUSED = "excused", "Excused"
        NO_SHOW = "no_show", "No-show"
        CANCELLED = "cancelled", "Cancelled"
        MAKEUP = "makeup", "Makeup"
    occurrence = models.ForeignKey(LessonOccurrence, on_delete=models.CASCADE, related_name="attendance_records")
    person = models.ForeignKey("portal.Person", on_delete=models.PROTECT, related_name="lesson_attendance_records")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.EXPECTED)
    notes = models.CharField(max_length=255, blank=True)
    recorded_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["person__last_name", "person__first_name", "id"]
        constraints = [models.UniqueConstraint(fields=["occurrence", "person"], name="unique_lesson_occurrence_person_attendance")]
    def clean(self):
        super().clean()
        if self.person_id and self.person.team_id != self.occurrence.series.program.team_id: raise ValidationError("Lesson attendance must remain within one organization.")
    def __str__(self): return f"{self.person} — {self.occurrence}"


class LessonAssignment(models.Model):
    class Role(models.TextChoices):
        PARTICIPANT = "participant", "Participant"
        INSTRUCTOR = "instructor", "Instructor"
    occurrence = models.ForeignKey(LessonOccurrence, on_delete=models.CASCADE, related_name="assignments")
    person = models.ForeignKey("portal.Person", on_delete=models.PROTECT, related_name="lesson_assignments")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.PARTICIPANT)
    horse = models.ForeignKey("portal.Horse", on_delete=models.PROTECT, null=True, blank=True, related_name="lesson_assignments")
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["role", "person__last_name", "person__first_name", "id"]
        constraints = [models.UniqueConstraint(fields=["occurrence", "person", "role"], name="unique_lesson_occurrence_person_role")]
    def clean(self):
        super().clean(); team_id = self.occurrence.series.program.team_id
        if self.person_id and self.person.team_id != team_id: raise ValidationError("Lesson assignment person must belong to the same organization.")
        if self.horse_id and self.horse.team_id != team_id: raise ValidationError("Lesson assignment horse must belong to the same organization.")
        if self.role == self.Role.INSTRUCTOR and self.horse_id: raise ValidationError("Instructor assignments cannot have a horse assignment.")
    def __str__(self): return f"{self.person} — {self.get_role_display()} — {self.occurrence}"


class LessonParticipantMove(models.Model):
    """Auditable movement of one participant between lesson occurrences."""
    class Kind(models.TextChoices):
        MOVE = "move", "Move"
        MAKEUP = "makeup", "Make-up"
    class Initiator(models.TextChoices):
        STAFF = "staff", "Staff"
        RIDER = "rider", "Rider"
    source_occurrence = models.ForeignKey(LessonOccurrence, on_delete=models.PROTECT, related_name="participant_moves_out")
    destination_occurrence = models.ForeignKey(LessonOccurrence, on_delete=models.PROTECT, related_name="participant_moves_in")
    person = models.ForeignKey("portal.Person", on_delete=models.PROTECT, related_name="lesson_participant_moves")
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.MAKEUP)
    source_status = models.CharField(max_length=16, choices=LessonAttendanceRecord.Status.choices, default=LessonAttendanceRecord.Status.EXCUSED)
    carry_horse = models.BooleanField(default=False)
    reason = models.CharField(max_length=255, blank=True)
    initiated_by = models.CharField(max_length=12, choices=Initiator.choices, default=Initiator.STAFF)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="lesson_participant_moves_created")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at", "id"]
        constraints = [models.UniqueConstraint(fields=["source_occurrence", "destination_occurrence", "person"], name="unique_lesson_participant_move")]
    def clean(self):
        super().clean()
        if self.source_occurrence_id and self.destination_occurrence_id:
            if self.source_occurrence_id == self.destination_occurrence_id: raise ValidationError("Destination lesson must be different from the original lesson.")
            source_team = self.source_occurrence.series.program.team_id
            if self.destination_occurrence.series.program.team_id != source_team: raise ValidationError("Rider lesson moves must remain within one organization.")
            if self.person_id and self.person.team_id != source_team: raise ValidationError("Rider lesson move must remain within one organization.")
            if self.destination_occurrence.status in {LessonOccurrence.Status.COMPLETED, LessonOccurrence.Status.CANCELLED}: raise ValidationError("Riders cannot be moved into completed or cancelled lessons.")
            source_iea = self.source_occurrence.series.is_iea_series
            destination_iea = self.destination_occurrence.series.is_iea_series
            if source_iea != destination_iea: raise ValidationError("Barn and IEA lesson rosters cannot be mixed by a rider move.")
            if source_iea:
                source_context = self.source_occurrence.series.iea_context
                destination_context = self.destination_occurrence.series.iea_context
                if source_context.season_id != destination_context.season_id or source_context.team_level != destination_context.team_level:
                    raise ValidationError("IEA rider moves must stay within the same season and team level.")
    def __str__(self): return f"{self.person} · {self.source_occurrence} → {self.destination_occurrence}"
