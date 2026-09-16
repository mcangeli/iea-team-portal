from django import forms
from django.db import transaction
from django.db.models import Q

from .model_modules.horses import Horse
from .model_modules.lessons import IEALessonSeriesContext, LessonAssignment, LessonAttendanceRecord, LessonEnrollment, LessonProgram, LessonSeries
from .model_modules.people import OrganizationGroup, OrganizationRoleAssignment, Person
from .models import UserProfile


WEEKDAY_CHOICES = [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday")]


def lesson_instructor_queryset(team, *, iea=False):
    """Return only people allowed to instruct the requested lesson domain."""
    queryset = Person.objects.filter(team=team, active=True)
    if iea:
        return queryset.filter(user__profile__role=UserProfile.Role.COACH).distinct().order_by("last_name", "first_name")
    return queryset.filter(
        role_assignments__active=True,
        role_assignments__role__in=[
            OrganizationRoleAssignment.Role.TRAINER,
            OrganizationRoleAssignment.Role.ASSISTANT_TRAINER,
        ],
    ).distinct().order_by("last_name", "first_name")


class LessonProgramForm(forms.ModelForm):
    class Meta:
        model = LessonProgram
        fields = ["name", "group", "description", "default_capacity", "enrollment_opens", "enrollment_closes", "active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4}), "enrollment_opens": forms.DateInput(attrs={"type": "date"}), "enrollment_closes": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, team, **kwargs):
        super().__init__(*args, **kwargs); self.team = team; self.instance.team = team
        self.fields["group"].queryset = OrganizationGroup.objects.filter(team=team, group_type=OrganizationGroup.GroupType.PROGRAM, active=True).order_by("name")

    def save(self, commit=True):
        obj = super().save(commit=False); obj.team = self.team
        if commit: obj.full_clean(); obj.save()
        return obj


class LessonSeriesForm(forms.ModelForm):
    class Meta:
        model = LessonSeries
        fields = ["name", "instructor", "weekday", "starts_at_time", "duration_minutes", "default_location", "capacity", "start_date", "end_date", "active", "notes"]
        widgets = {"starts_at_time": forms.TimeInput(attrs={"type": "time"}), "start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"}), "notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, program, **kwargs):
        super().__init__(*args, **kwargs); self.program = program; self.instance.program = program
        self.fields["instructor"].queryset = lesson_instructor_queryset(program.team, iea=False)
        self.fields["weekday"].widget = forms.Select(choices=WEEKDAY_CHOICES)

    def save(self, commit=True):
        obj = super().save(commit=False); obj.program = self.program
        if commit: obj.full_clean(); obj.save()
        return obj


class IEALessonSeriesForm(LessonSeriesForm):
    team_level = forms.ChoiceField(choices=IEALessonSeriesContext.TeamLevel.choices)

    def __init__(self, *args, program, season, **kwargs):
        self.season = season; super().__init__(*args, program=program, **kwargs)
        self.fields["instructor"].queryset = lesson_instructor_queryset(program.team, iea=True)
        if self.instance.pk and self.instance.is_iea_series:
            self.fields["team_level"].initial = self.instance.iea_context.team_level
        else:
            self.fields["start_date"].initial = season.start_date; self.fields["end_date"].initial = season.end_date

    def save(self, commit=True):
        series = super().save(commit=False)
        if not commit:
            return series
        with transaction.atomic():
            # A new series does not have its IEA context yet, so validate the
            # generic fields without making the model guess the lesson domain.
            # The IEA context below is the authoritative Coach validation gate.
            if series.pk:
                series.full_clean()
            series.save()
            context, _ = IEALessonSeriesContext.objects.get_or_create(
                series=series,
                defaults={"season": self.season, "team_level": self.cleaned_data["team_level"]},
            )
            context.season = self.season
            context.team_level = self.cleaned_data["team_level"]
            context.full_clean()
            context.save()
            # Once context exists, the series itself can safely apply its
            # domain-aware instructor validation too.
            series.full_clean()
        return series


class LessonEnrollmentForm(forms.ModelForm):
    class Meta:
        model = LessonEnrollment
        fields = ["person", "status", "start_date", "end_date", "notes"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, series, **kwargs):
        super().__init__(*args, **kwargs); self.series = series; self.instance.series = series
        queryset = Person.objects.filter(team=series.program.team, active=True)
        if not self.instance.pk: queryset = queryset.exclude(pk__in=series.enrollments.values_list("person_id", flat=True))
        self.fields["person"].queryset = queryset.order_by("last_name", "first_name")

    def save(self, commit=True):
        obj = super().save(commit=False); obj.series = self.series
        if commit: obj.full_clean(); obj.save()
        return obj


class LessonAttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = LessonAttendanceRecord
        fields = ["status", "notes"]


class LessonParticipantAssignmentForm(forms.ModelForm):
    class Meta:
        model = LessonAssignment
        fields = ["horse", "notes"]

    def __init__(self, *args, occurrence, **kwargs):
        super().__init__(*args, **kwargs)
        self.occurrence = occurrence
        self.fields["horse"].queryset = Horse.objects.filter(team=occurrence.series.program.team, active=True).order_by("name")

    def save(self, commit=True):
        obj = super().save(commit=False); obj.occurrence = self.occurrence; obj.role = LessonAssignment.Role.PARTICIPANT
        if commit: obj.full_clean(); obj.save()
        return obj


class LessonRescheduleForm(forms.Form):
    starts_at = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    ends_at = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class LessonCancelForm(forms.Form):
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}), label="Cancellation note")
