from django import forms

from .model_modules.lessons import IEALessonSeriesContext, LessonEnrollment, LessonProgram, LessonSeries
from .model_modules.people import OrganizationGroup, Person


WEEKDAY_CHOICES = [
    (0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"),
    (4, "Friday"), (5, "Saturday"), (6, "Sunday"),
]


class LessonProgramForm(forms.ModelForm):
    class Meta:
        model = LessonProgram
        fields = ["name", "group", "description", "default_capacity", "enrollment_opens", "enrollment_closes", "active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "enrollment_opens": forms.DateInput(attrs={"type": "date"}),
            "enrollment_closes": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, team, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.instance.team = team
        self.fields["group"].queryset = OrganizationGroup.objects.filter(
            team=team, group_type=OrganizationGroup.GroupType.PROGRAM, active=True
        ).order_by("name")

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.team = self.team
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class LessonSeriesForm(forms.ModelForm):
    class Meta:
        model = LessonSeries
        fields = ["name", "instructor", "weekday", "starts_at_time", "duration_minutes", "default_location", "capacity", "start_date", "end_date", "active", "notes"]
        widgets = {
            "starts_at_time": forms.TimeInput(attrs={"type": "time"}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, program, **kwargs):
        super().__init__(*args, **kwargs)
        self.program = program
        self.instance.program = program
        self.fields["instructor"].queryset = Person.objects.filter(team=program.team, active=True).order_by("last_name", "first_name")
        self.fields["weekday"].widget = forms.Select(choices=WEEKDAY_CHOICES)

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.program = self.program
        if commit:
            obj.full_clean()
            obj.save()
        return obj


class IEALessonSeriesForm(LessonSeriesForm):
    """Create a generic series plus its explicit IEA season/team specialization."""
    team_level = forms.ChoiceField(choices=IEALessonSeriesContext.TeamLevel.choices)

    def __init__(self, *args, program, season, **kwargs):
        self.season = season
        super().__init__(*args, program=program, **kwargs)
        self.fields["start_date"].initial = season.start_date
        self.fields["end_date"].initial = season.end_date

    def save(self, commit=True):
        series = super().save(commit=commit)
        if commit:
            context = IEALessonSeriesContext(
                series=series,
                season=self.season,
                team_level=self.cleaned_data["team_level"],
            )
            context.full_clean()
            context.save()
        return series


class LessonEnrollmentForm(forms.ModelForm):
    class Meta:
        model = LessonEnrollment
        fields = ["person", "status", "start_date", "end_date", "notes"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, series, **kwargs):
        super().__init__(*args, **kwargs)
        self.series = series
        self.instance.series = series
        queryset = Person.objects.filter(team=series.program.team, active=True)
        if not self.instance.pk:
            enrolled_ids = series.enrollments.values_list("person_id", flat=True)
            queryset = queryset.exclude(pk__in=enrolled_ids)
        self.fields["person"].queryset = queryset.order_by("last_name", "first_name")

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.series = self.series
        if commit:
            obj.full_clean()
            obj.save()
        return obj
