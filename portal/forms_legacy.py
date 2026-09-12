from decimal import Decimal
from django.core.exceptions import ValidationError
from django import forms
from django.forms import formset_factory
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import (
    Announcement, CalendarEvent, GuardianContact, Rider, RiderGuardian, SeasonClass,
    SeasonMembership, SeasonScoringConfig, QualificationOverride, Show, ShowClass, ShowEntry, ShowResult,
    LessonGroup, Lesson, LessonAttendance, ShowAvailability, VolunteerLog, Season, UserProfile,
    CommitteeAssignment, ShowLeadAssignment, ShowPlanningItem, ShowDayUpdate, RiderDevelopmentNote, RiderAward,
    EventRSVP, ActionItem, FinancialAccount, FinancialCategory, FinancialTransaction, SeasonBudget,
    HomeBarn, MembershipDuesRate, FamilyCharge, FamilyCredit, ServiceAgreementCredit,
    FinancialAssistanceAward, AssistanceClaim, FamilyPayment, ShowBudgetLine, ReimbursementRequest, ShowTransactionAllocation,
    FundraisingCampaign, FundraisingContribution, FundraisingPolicy,
)


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"

class DateInput(forms.DateInput):
    input_type = "date"

class TimeInput(forms.TimeInput):
    input_type = "time"


class RiderForm(forms.ModelForm):
    season = forms.ModelChoiceField(
        queryset=Season.objects.none(),
        required=False,
        help_text="Optional when creating a rider. The rider record remains permanent; this creates the rider's enrollment for the selected season."
    )
    team_level = forms.ChoiceField(
        choices=[("", "---------")] + list(SeasonMembership.TeamLevel.choices),
        required=False,
        label="Season team"
    )
    home_barn = forms.ModelChoiceField(
        queryset=HomeBarn.objects.none(),
        required=False,
        label="Home barn",
        help_text="Home barn for the selected season; it can change in a future season without changing history."
    )
    classes = forms.ModelMultipleChoiceField(
        queryset=SeasonClass.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Choose the rider's classes for the selected season."
    )
    season_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Season notes"
    )

    class Meta:
        model = Rider
        fields = ["first_name", "last_name", "preferred_name", "email", "school", "grade", "iea_member_number", "bio", "photo", "active"]

    def __init__(self, *args, team=None, include_season=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.include_season = include_season

        if not include_season:
            for field_name in ["season", "team_level", "home_barn", "classes", "season_notes"]:
                self.fields.pop(field_name, None)
            return

        if team:
            seasons = Season.objects.filter(team=team, is_closed=False).order_by("-is_active", "-start_date")
            self.fields["season"].queryset = seasons
            self.fields["home_barn"].queryset = HomeBarn.objects.filter(team=team, active=True).order_by("name")
            self.fields["classes"].queryset = SeasonClass.objects.filter(
                season__team=team,
                season__is_closed=False,
                active=True,
            ).select_related("season").order_by("-season__is_active", "-season__start_date", "sort_order", "name")

            active = seasons.filter(is_active=True).first()
            if not self.is_bound and active:
                self.initial.setdefault("season", active.pk)

    def clean(self):
        cleaned = super().clean()
        if not self.include_season:
            return cleaned

        season = cleaned.get("season")
        team_level = cleaned.get("team_level")
        classes = cleaned.get("classes")

        if season:
            if self.team and season.team_id != self.team.id:
                self.add_error("season", "Choose a season for this team.")
            if season.is_closed:
                self.add_error("season", "This season is archived and cannot accept new rider enrollments.")
            if not team_level:
                self.add_error("team_level", "Choose Futures or Upper School for the selected season.")
        elif team_level or cleaned.get("home_barn") or classes or cleaned.get("season_notes"):
            self.add_error("season", "Choose a season before entering season-specific rider information.")

        if season and cleaned.get("home_barn") and cleaned["home_barn"].team_id != season.team_id:
            self.add_error("home_barn", "Choose a home barn for this team.")

        if season and team_level and classes:
            invalid = classes.exclude(
                season=season,
                team_level__in=[team_level, SeasonClass.TeamLevel.BOTH],
                active=True,
            )
            if invalid.exists():
                self.add_error("classes", "Choose only active classes available to this rider's selected season and team.")

        return cleaned


class SeasonMembershipForm(forms.ModelForm):
    class Meta:
        model = SeasonMembership
        fields = ["team_level", "home_barn", "classes", "notes"]
        widgets = {"classes": forms.CheckboxSelectMultiple}

    def __init__(self, *args, season=None, **kwargs):
        super().__init__(*args, **kwargs)
        if season:
            self.fields["classes"].queryset = season.season_classes.filter(active=True)
            barn_qs = HomeBarn.objects.filter(team=season.team, active=True)
            if self.instance and self.instance.pk and self.instance.home_barn_id:
                barn_qs = HomeBarn.objects.filter(team=season.team).filter(
                    Q(active=True) | Q(pk=self.instance.home_barn_id)
                )
            self.fields["home_barn"].queryset = barn_qs.distinct()

    def clean(self):
        cleaned = super().clean()
        team_level = cleaned.get("team_level")
        classes = cleaned.get("classes")
        if team_level and classes:
            bad = classes.exclude(team_level__in=[team_level, SeasonClass.TeamLevel.BOTH])
            if bad.exists():
                self.add_error("classes", "Choose only classes available to this rider's Futures/Upper team.")
        return cleaned


class GuardianContactForm(forms.ModelForm):
    relationship = forms.CharField(max_length=50, required=False, initial="Parent")
    primary_contact = forms.BooleanField(required=False)

    class Meta:
        model = GuardianContact
        fields = ["first_name", "last_name", "email", "phone", "notes"]


class SeasonClassForm(forms.ModelForm):
    class Meta:
        model = SeasonClass
        fields = ["name", "team_level", "discipline", "sort_order", "active"]

    def __init__(self, *args, season=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season or (self.instance.season if self.instance and self.instance.pk else None)

    def clean(self):
        cleaned = super().clean()
        name = (cleaned.get("name") or "").strip()
        team_level = cleaned.get("team_level")
        if self.season and name and team_level:
            qs = SeasonClass.objects.filter(
                season=self.season, name__iexact=name, team_level=team_level
            ).exclude(pk=getattr(self.instance, "pk", None))
            if qs.exists():
                self.add_error("name", "This season already has a class with this name for the selected team level.")
        return cleaned


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "body", "priority", "audience", "selected_users", "send_email", "published", "expires_at"]
        widgets = {
            "expires_at": DateTimeLocalInput(format="%Y-%m-%dT%H:%M"),
            "selected_users": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team:
            self.fields["selected_users"].queryset = self.fields["selected_users"].queryset.filter(profile__team=team, is_active=True).order_by("last_name", "first_name", "username")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("audience") == Announcement.Audience.SELECTED and not cleaned.get("selected_users"):
            self.add_error("selected_users", "Choose at least one user for a selected-user announcement.")
        return cleaned


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["email_announcements", "email_show_updates", "email_reminders"]
        labels = {
            "email_announcements": "Email team announcements",
            "email_show_updates": "Email show-day updates",
            "email_reminders": "Email reminders",
        }


class CalendarEventForm(forms.ModelForm):
    class Meta:
        model = CalendarEvent
        fields = [
            "title", "kind", "starts_at", "ends_at", "all_day", "location",
            "description", "visible_to_all", "rsvp_requested", "rsvp_deadline",
        ]
        widgets = {
            "starts_at": DateTimeLocalInput(format="%Y-%m-%dT%H:%M"),
            "ends_at": DateTimeLocalInput(format="%Y-%m-%dT%H:%M"),
            "rsvp_deadline": DateTimeLocalInput(format="%Y-%m-%dT%H:%M"),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("rsvp_requested") and not cleaned.get("visible_to_all"):
            self.add_error("visible_to_all", "An event requesting family RSVP must be visible to the team.")
        deadline = cleaned.get("rsvp_deadline")
        starts = cleaned.get("starts_at")
        if deadline and starts and deadline > starts:
            self.add_error("rsvp_deadline", "The RSVP deadline must be before the event starts.")
        return cleaned


class ShowForm(forms.ModelForm):
    class Meta:
        model = Show
        fields = [
            "name", "competition_level", "financial_role", "show_date", "start_time", "venue", "address",
            "host_team", "iea_zone", "iea_region", "status", "entry_deadline",
            "futures_team_place", "upper_team_place", "notes",
        ]
        widgets = {"show_date": DateInput(), "start_time": TimeInput(), "entry_deadline": DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["futures_team_place"].label = "Futures overall team place"
        self.fields["upper_team_place"].label = "Upper School overall team place"
        self.fields["futures_team_place"].help_text = "Finals only. Enter the team's overall placing."
        self.fields["upper_team_place"].help_text = "Finals only. Enter the team's overall placing."

    def clean(self):
        cleaned = super().clean()
        new_level = cleaned.get("competition_level")
        if self.instance and self.instance.pk and new_level:
            old_level = Show.objects.filter(pk=self.instance.pk).values_list("competition_level", flat=True).first()
            changed_regular_boundary = (
                (old_level == Show.CompetitionLevel.REGULAR)
                != (new_level == Show.CompetitionLevel.REGULAR)
            )
            if changed_regular_boundary and self.instance.classes.filter(entries__isnull=False).exists():
                self.add_error(
                    "competition_level",
                    "Remove existing rider entries before changing a show between Regular Season and Finals.",
                )
        return cleaned


class ShowClassForm(forms.ModelForm):
    class Meta:
        model = ShowClass
        fields = [
            "season_class", "class_number", "sort_order",
            "prize_list_time", "estimated_time", "schedule_note",
        ]
        widgets = {
            "prize_list_time": TimeInput(),
            "estimated_time": TimeInput(),
        }

    def __init__(self, *args, show=None, **kwargs):
        super().__init__(*args, **kwargs)
        if show:
            used = show.classes.exclude(pk=getattr(self.instance, "pk", None)).values_list("season_class_id", flat=True)
            self.fields["season_class"].queryset = show.season.season_classes.filter(active=True).exclude(pk__in=used)


class ShowEntryForm(forms.ModelForm):
    class Meta:
        model = ShowEntry
        fields = ["show_class", "rider", "competition_track", "entry_type", "status", "notes"]

    def __init__(self, *args, show=None, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.show = show
        if show is not None:
            self.fields["show_class"].queryset = show.classes.select_related("season_class")
            riders = Rider.objects.filter(team=team, active=True, memberships__season=show.season)
            selected_class_id = self.data.get("show_class") if self.is_bound else getattr(self.instance, "show_class_id", None)
            if selected_class_id:
                try:
                    selected = show.classes.select_related("season_class").get(pk=selected_class_id)
                    if selected.season_class_id:
                        riders = riders.filter(memberships__season=show.season, memberships__classes=selected.season_class)
                        if selected.season_class.team_level != SeasonClass.TeamLevel.BOTH:
                            riders = riders.filter(memberships__team_level=selected.season_class.team_level)
                except (ShowClass.DoesNotExist, ValueError, TypeError):
                    pass
            self.fields["rider"].queryset = riders.distinct()

            if show.competition_level == Show.CompetitionLevel.REGULAR:
                self.fields.pop("competition_track", None)
            else:
                self.fields.pop("entry_type", None)
                self.fields["competition_track"].choices = [
                    (ShowEntry.CompetitionTrack.INDIVIDUAL, "Individual"),
                    (ShowEntry.CompetitionTrack.TEAM, "Team"),
                ]
                self.fields["competition_track"].help_text = (
                    "Use separate Individual and Team entries if the same rider competes in both at this finals show."
                )

    def clean(self):
        cleaned = super().clean()
        show_class = cleaned.get("show_class")
        rider = cleaned.get("rider")
        if show_class and rider and self.show:
            entry = self.instance
            entry.show_class = show_class
            entry.rider = rider
            if self.show.competition_level == Show.CompetitionLevel.REGULAR:
                entry.competition_track = ShowEntry.CompetitionTrack.REGULAR
            else:
                entry.competition_track = cleaned.get("competition_track")
                entry.entry_type = (
                    ShowEntry.EntryType.INDIVIDUAL
                    if entry.competition_track == ShowEntry.CompetitionTrack.INDIVIDUAL
                    else ShowEntry.EntryType.TEAM
                )
                entry.is_point_rider = False
            try:
                entry.clean()
            except ValidationError as exc:
                raise exc
        return cleaned


class ShowResultForm(forms.ModelForm):
    class Meta:
        model = ShowResult
        fields = ["place", "manual_points", "points", "horse_name", "notes"]

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("manual_points"):
            cleaned["points"] = None
        return cleaned


class SeasonScoringConfigForm(forms.ModelForm):
    class Meta:
        model = SeasonScoringConfig
        fields = [
            "first_points", "second_points", "third_points", "fourth_points",
            "fifth_points", "sixth_points", "individual_qualification_points",
            "team_qualification_points",
        ]


class QualificationOverrideForm(forms.ModelForm):
    class Meta:
        model = QualificationOverride
        fields = ["status", "notes"]


class LessonGroupForm(forms.ModelForm):
    class Meta:
        model = LessonGroup
        fields = ["name", "team_level", "coach", "riders", "default_location", "active"]
        widgets = {"riders": forms.CheckboxSelectMultiple}

    def __init__(self, *args, season=None, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season or (self.instance.season if self.instance and self.instance.pk else None)
        if season:
            self.fields["riders"].queryset = Rider.objects.filter(team=season.team, active=True, memberships__season=season).distinct()
        if team:
            self.fields["coach"].queryset = self.fields["coach"].queryset.filter(profile__team=team, profile__role__in=["admin", "coach"])

    def clean(self):
        cleaned = super().clean()
        team_level = cleaned.get("team_level")
        riders = cleaned.get("riders")
        if team_level and team_level != LessonGroup.TeamLevel.BOTH and riders:
            season = self.season
            bad = riders.exclude(memberships__season=season, memberships__team_level=team_level) if season else riders
            if bad.exists():
                self.add_error("riders", "Choose only riders assigned to this lesson group's Futures/Upper team level.")
        name = (cleaned.get("name") or "").strip()
        if self.season and name:
            duplicate = LessonGroup.objects.filter(
                season=self.season, name__iexact=name
            ).exclude(pk=getattr(self.instance, "pk", None))
            if duplicate.exists():
                self.add_error("name", "A lesson group with this name already exists in this season.")
        return cleaned


class LessonForm(forms.ModelForm):
    recurrence_weeks = forms.IntegerField(min_value=1, max_value=26, initial=1, help_text="Create this lesson weekly for this many weeks.")

    class Meta:
        model = Lesson
        fields = ["group", "coach", "title", "starts_at", "ends_at", "location", "notes", "cancelled"]
        widgets = {
            "starts_at": DateTimeLocalInput(format="%Y-%m-%dT%H:%M"),
            "ends_at": DateTimeLocalInput(format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, season=None, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if season:
            self.fields["group"].queryset = season.lesson_groups.filter(active=True)
        if team:
            self.fields["coach"].queryset = self.fields["coach"].queryset.filter(profile__team=team, profile__role__in=["admin", "coach"])
        if self.instance and self.instance.pk:
            self.fields.pop("recurrence_weeks", None)

    def clean(self):
        cleaned = super().clean()
        starts = cleaned.get("starts_at")
        ends = cleaned.get("ends_at")
        if starts and ends and ends <= starts:
            self.add_error("ends_at", "Lesson end time must be after the start time.")
        return cleaned


class LessonAttendanceForm(forms.ModelForm):
    class Meta:
        model = LessonAttendance
        fields = ["status", "horse_name", "notes"]


class ShowAvailabilityForm(forms.ModelForm):
    class Meta:
        model = ShowAvailability
        fields = ["status", "notes"]


class VolunteerLogForm(forms.ModelForm):
    class Meta:
        model = VolunteerLog
        fields = ["rider", "service_date", "hours", "category", "performed_by", "description"]
        widgets = {"service_date": DateInput()}

    def __init__(self, *args, team=None, season=None, visible_riders=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Rider.objects.none()
        if visible_riders is not None:
            qs = visible_riders
        elif team:
            qs = Rider.objects.filter(team=team, active=True)
        if season:
            qs = qs.filter(memberships__season=season)
        self.fields["rider"].queryset = qs.distinct()


class VolunteerReviewForm(forms.ModelForm):
    class Meta:
        model = VolunteerLog
        fields = ["status", "coach_notes"]


class VolunteerRequirementForm(forms.ModelForm):
    class Meta:
        model = Season
        fields = ["futures_volunteer_hours_required", "upper_volunteer_hours_required"]
        labels = {
            "futures_volunteer_hours_required": "Futures required hours",
            "upper_volunteer_hours_required": "Upper School required hours",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["futures_volunteer_hours_required"].min_value = 0
        self.fields["upper_volunteer_hours_required"].min_value = 0

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile


class UserOnboardingForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    username = forms.CharField(max_length=150)
    role = forms.ChoiceField(choices=UserProfile.Role.choices)
    rider = forms.ModelChoiceField(queryset=Rider.objects.none(), required=False, help_text="Required for Rider accounts.")
    guardian = forms.ModelChoiceField(queryset=GuardianContact.objects.none(), required=False, help_text="Required for Parent accounts; optional for Coach/Administrator accounts who are also a parent/guardian.")
    temporary_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Leave blank to use DEFAULT_TEMP_PASSWORD from the server environment.",
    )

    def __init__(self, *args, team=None, actor=None, initial_rider=None, initial_guardian=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.actor = actor
        self.fields["rider"].queryset = Rider.objects.filter(team=team, user__isnull=True).order_by("last_name", "first_name") if team else Rider.objects.none()
        self.fields["guardian"].queryset = GuardianContact.objects.filter(team=team, user__isnull=True).order_by("last_name", "first_name") if team else GuardianContact.objects.none()
        if initial_rider:
            self.fields["rider"].initial = initial_rider
            self.fields["first_name"].initial = initial_rider.first_name
            self.fields["last_name"].initial = initial_rider.last_name
            self.fields["email"].initial = initial_rider.email
            self.fields["role"].initial = UserProfile.Role.RIDER
            self.fields["username"].initial = f"{initial_rider.first_name}.{initial_rider.last_name}".lower().replace(" ", "")
        if initial_guardian:
            self.fields["guardian"].initial = initial_guardian
            self.fields["first_name"].initial = initial_guardian.first_name
            self.fields["last_name"].initial = initial_guardian.last_name
            self.fields["email"].initial = initial_guardian.email
            self.fields["role"].initial = UserProfile.Role.PARENT
            self.fields["username"].initial = f"{initial_guardian.first_name}.{initial_guardian.last_name}".lower().replace(" ", "")
        if actor and not (actor.is_superuser or (hasattr(actor, "profile") and actor.profile.role == UserProfile.Role.ADMIN)):
            self.fields["role"].choices = [
                (UserProfile.Role.PARENT, "Parent/Guardian"),
                (UserProfile.Role.RIDER, "Rider"),
            ]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already in use.")
        return username

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        rider = cleaned.get("rider")
        guardian = cleaned.get("guardian")
        if role == UserProfile.Role.RIDER and not rider:
            self.add_error("rider", "Choose the rider this login belongs to.")
        if role == UserProfile.Role.PARENT and not guardian:
            self.add_error("guardian", "Choose the parent/guardian this login belongs to.")
        if role != UserProfile.Role.RIDER and rider:
            self.add_error("rider", "A rider link can only be used with the Rider role.")
        if role == UserProfile.Role.RIDER and guardian:
            self.add_error("guardian", "A Rider login cannot also be linked as a parent/guardian. Staff accounts may also be linked as guardians.")
        if role in {UserProfile.Role.ADMIN, UserProfile.Role.COACH}:
            is_admin_actor = self.actor and (self.actor.is_superuser or (hasattr(self.actor, "profile") and self.actor.profile.role == UserProfile.Role.ADMIN))
            if not is_admin_actor:
                self.add_error("role", "Only administrators can create Coach or Administrator accounts.")
        temp = cleaned.get("temporary_password") or settings.DEFAULT_TEMP_PASSWORD
        if not temp:
            self.add_error("temporary_password", "Enter a temporary password or configure DEFAULT_TEMP_PASSWORD on the server.")
        else:
            candidate = User(username=cleaned.get("username", ""), first_name=cleaned.get("first_name", ""), last_name=cleaned.get("last_name", ""), email=cleaned.get("email", ""))
            try:
                validate_password(temp, user=candidate)
            except ValidationError as exc:
                self.add_error("temporary_password", exc)
            cleaned["resolved_password"] = temp
        return cleaned

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["username"], email=data["email"], password=data["resolved_password"],
            first_name=data["first_name"], last_name=data["last_name"],
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.team = self.team
        profile.role = data["role"]
        profile.must_change_password = True
        profile.save(update_fields=["team", "role", "must_change_password"])

        rider = data.get("rider")
        guardian = data.get("guardian")
        if rider:
            # Re-check inside the same transaction so a stale/raced form cannot
            # crash with a OneToOne database error.
            locked_rider = Rider.objects.select_for_update().get(pk=rider.pk, team=self.team)
            if locked_rider.user_id and locked_rider.user_id != user.id:
                raise ValidationError("This rider already has a login. Manage the existing account instead.")
            locked_rider.user = user
            if not locked_rider.email:
                locked_rider.email = user.email
            locked_rider.save(update_fields=["user", "email"])
        if guardian:
            locked_guardian = GuardianContact.objects.select_for_update().get(pk=guardian.pk, team=self.team)
            if locked_guardian.user_id and locked_guardian.user_id != user.id:
                raise ValidationError("This parent/guardian already has a login. Manage the existing account instead.")
            locked_guardian.user = user
            if not locked_guardian.email:
                locked_guardian.email = user.email
            locked_guardian.save(update_fields=["user", "email"])
            for link in locked_guardian.rider_links.select_related("rider").all():
                link.rider.guardians.add(user)
        return user


class UserAccountEditForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    role = forms.ChoiceField(choices=UserProfile.Role.choices)
    is_active = forms.BooleanField(required=False)
    rider = forms.ModelChoiceField(queryset=Rider.objects.none(), required=False)
    guardian = forms.ModelChoiceField(queryset=GuardianContact.objects.none(), required=False, help_text="Optional for Coach/Administrator accounts who are also a parent/guardian.")

    def __init__(self, *args, team=None, actor=None, user_obj=None, **kwargs):
        self.team = team; self.actor = actor; self.user_obj = user_obj
        initial = kwargs.setdefault("initial", {})
        if user_obj:
            initial.update({"first_name": user_obj.first_name, "last_name": user_obj.last_name, "email": user_obj.email,
                            "role": user_obj.profile.role, "is_active": user_obj.is_active,
                            "rider": getattr(getattr(user_obj, "rider_record", None), "pk", None),
                            "guardian": getattr(getattr(user_obj, "guardian_contact", None), "pk", None)})
        super().__init__(*args, **kwargs)
        rider_qs = Rider.objects.filter(team=team).filter(Q(user__isnull=True) | Q(user=user_obj)).order_by("last_name", "first_name") if team else Rider.objects.none()
        guardian_qs = GuardianContact.objects.filter(team=team).filter(Q(user__isnull=True) | Q(user=user_obj)).order_by("last_name", "first_name") if team else GuardianContact.objects.none()
        self.fields["rider"].queryset = rider_qs
        self.fields["guardian"].queryset = guardian_qs
        if actor and not (actor.is_superuser or (hasattr(actor, "profile") and actor.profile.role == UserProfile.Role.ADMIN)):
            self.fields["role"].choices = [(UserProfile.Role.PARENT, "Parent/Guardian"), (UserProfile.Role.RIDER, "Rider")]

    def clean(self):
        cleaned = super().clean(); role = cleaned.get("role")
        if self.user_obj and self.user_obj == self.actor and not cleaned.get("is_active"):
            self.add_error("is_active", "You cannot deactivate your own account.")
        if role == UserProfile.Role.RIDER and not cleaned.get("rider"):
            self.add_error("rider", "Choose the linked rider.")
        if role == UserProfile.Role.PARENT and not cleaned.get("guardian"):
            self.add_error("guardian", "Choose the linked parent/guardian.")
        if role != UserProfile.Role.RIDER and cleaned.get("rider"):
            self.add_error("rider", "Rider links require the Rider role.")
        if role == UserProfile.Role.RIDER and cleaned.get("guardian"):
            self.add_error("guardian", "A Rider login cannot also be linked as a parent/guardian. Staff accounts may also be linked as guardians.")
        if role in {UserProfile.Role.ADMIN, UserProfile.Role.COACH}:
            is_admin_actor = self.actor and (self.actor.is_superuser or (hasattr(self.actor, "profile") and self.actor.profile.role == UserProfile.Role.ADMIN))
            if not is_admin_actor:
                self.add_error("role", "Only administrators can assign Coach or Administrator roles.")
        return cleaned

    def save(self):
        data=self.cleaned_data; user=self.user_obj
        old_rider = getattr(user, "rider_record", None); old_guardian = getattr(user, "guardian_contact", None)
        if old_rider and old_rider != data.get("rider"):
            old_rider.user = None; old_rider.save(update_fields=["user"])
        if old_guardian and old_guardian != data.get("guardian"):
            for link in old_guardian.rider_links.select_related("rider").all():
                link.rider.guardians.remove(user)
            old_guardian.user = None; old_guardian.save(update_fields=["user"])
        user.first_name=data["first_name"]; user.last_name=data["last_name"]; user.email=data["email"]; user.is_active=data["is_active"]; user.save()
        user.profile.role=data["role"]; user.profile.team=self.team; user.profile.save(update_fields=["role", "team"])
        if data.get("rider"):
            data["rider"].user=user; data["rider"].save(update_fields=["user"])
        if data.get("guardian"):
            data["guardian"].user=user; data["guardian"].save(update_fields=["user"])
            for link in data["guardian"].rider_links.select_related("rider").all(): link.rider.guardians.add(user)
        return user


class TemporaryPasswordResetForm(forms.Form):
    temporary_password = forms.CharField(required=False, widget=forms.PasswordInput(render_value=False), help_text="Leave blank to use DEFAULT_TEMP_PASSWORD.")

    def __init__(self, *args, user_obj=None, **kwargs):
        super().__init__(*args, **kwargs); self.user_obj=user_obj

    def clean(self):
        cleaned=super().clean(); temp=cleaned.get("temporary_password") or settings.DEFAULT_TEMP_PASSWORD
        if not temp:
            self.add_error("temporary_password", "Enter a temporary password or configure DEFAULT_TEMP_PASSWORD.")
        else:
            try: validate_password(temp, user=self.user_obj)
            except ValidationError as exc: self.add_error("temporary_password", exc)
            cleaned["resolved_password"] = temp
        return cleaned


class CommitteeAssignmentForm(forms.ModelForm):
    class Meta:
        model = CommitteeAssignment
        fields = ["user", "role", "active", "notes"]

    def __init__(self, *args, team=None, season=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season or (self.instance.season if self.instance and self.instance.pk else None)
        if team:
            self.fields["user"].queryset = User.objects.filter(
                Q(profile__team=team, profile__role=UserProfile.Role.PARENT) | Q(profile__team=team, guardian_contact__isnull=False),
                is_active=True,
            ).distinct().order_by("last_name", "first_name", "username")

    def clean(self):
        cleaned = super().clean()
        user = cleaned.get("user")
        role = cleaned.get("role")
        if self.season and user and role:
            duplicate = CommitteeAssignment.objects.filter(
                season=self.season, user=user, role=role
            ).exclude(pk=getattr(self.instance, "pk", None))
            if duplicate.exists():
                self.add_error("user", "This person already has this committee role for the selected season.")
        return cleaned


class ShowLeadAssignmentForm(forms.ModelForm):
    class Meta:
        model = ShowLeadAssignment
        fields = ["user", "active", "notes"]

    def __init__(self, *args, team=None, show=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.show = show or (self.instance.show if self.instance and self.instance.pk else None)
        if team:
            self.fields["user"].queryset = User.objects.filter(
                Q(profile__team=team, profile__role=UserProfile.Role.PARENT) | Q(profile__team=team, guardian_contact__isnull=False),
                is_active=True,
            ).distinct().order_by("last_name", "first_name", "username")

    def clean(self):
        cleaned = super().clean()
        user = cleaned.get("user")
        if self.show and user:
            duplicate = ShowLeadAssignment.objects.filter(
                show=self.show, user=user
            ).exclude(pk=getattr(self.instance, "pk", None))
            if duplicate.exists():
                self.add_error("user", "This person is already assigned as a Show Lead for this show.")
        return cleaned


class ShowPlanningItemForm(forms.ModelForm):
    class Meta:
        model = ShowPlanningItem
        fields = [
            "item_type", "team_level", "category", "title", "quantity", "details",
            "assigned_to", "completed", "family_visible", "sort_order",
        ]

    def __init__(self, *args, team=None, allowed_team_levels=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team:
            self.fields["assigned_to"].queryset = User.objects.filter(
                profile__team=team, is_active=True
            ).order_by("last_name", "first_name", "username")
        if allowed_team_levels is not None:
            allowed = set(allowed_team_levels)
            self.fields["team_level"].choices = [
                choice for choice in ShowPlanningItem.TeamLevel.choices
                if choice[0] in allowed
            ]


class ShowDayUpdateForm(forms.ModelForm):
    notify_now = forms.BooleanField(
        required=False, initial=True, label="Notify recipients now",
        help_text="Create a new in-portal notification now. Email is also sent when enabled below and allowed by the recipient's preferences.",
    )

    class Meta:
        model = ShowDayUpdate
        fields = ["audience", "title", "body", "send_email", "published"]
        widgets = {"body": forms.Textarea(attrs={"rows": 5})}
        labels = {
            "audience": "Who should see this update?",
            "send_email": "Send active email notification",
            "published": "Visible to families",
        }

    def __init__(self, *args, allowed_audiences=None, **kwargs):
        super().__init__(*args, **kwargs)
        if allowed_audiences is not None:
            allowed = set(allowed_audiences)
            self.fields["audience"].choices = [
                choice for choice in ShowDayUpdate.Audience.choices if choice[0] in allowed
            ]
        self.fields["body"].help_text = (
            "Use this for public show-day information such as schedule movement, arrival instructions, "
            "ring changes, volunteer reminders, or other operational updates."
        )


class RiderDevelopmentNoteForm(forms.ModelForm):
    class Meta:
        model = RiderDevelopmentNote
        fields = ["note", "family_visible"]
        widgets = {"note": forms.Textarea(attrs={"rows": 5})}


class RiderAwardForm(forms.ModelForm):
    class Meta:
        model = RiderAward
        fields = ["rider", "title", "description", "presentation_date", "published"]
        widgets = {"presentation_date": DateInput()}

    def __init__(self, *args, season=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season or (self.instance.season if self.instance and self.instance.pk else None)
        if self.season:
            self.fields["rider"].queryset = Rider.objects.filter(
                memberships__season=self.season, active=True
            ).distinct().order_by("last_name", "first_name")

    def clean(self):
        cleaned = super().clean()
        rider = cleaned.get("rider")
        title = (cleaned.get("title") or "").strip()
        if self.season and rider and title:
            duplicate = RiderAward.objects.filter(
                season=self.season, rider=rider, title__iexact=title
            ).exclude(pk=getattr(self.instance, "pk", None))
            if duplicate.exists():
                self.add_error("title", "This award has already been recorded for this rider in this season.")
        return cleaned


class EventRSVPForm(forms.ModelForm):
    class Meta:
        model = EventRSVP
        fields = ["status", "notes"]

    def clean_status(self):
        status = self.cleaned_data.get("status")
        if status == EventRSVP.Status.PENDING:
            raise forms.ValidationError("Choose Going, Maybe, or Not going.")
        return status


class ActionItemForm(forms.ModelForm):
    class Meta:
        model = ActionItem
        fields = [
            "title", "category", "details", "due_at", "event", "show", "rider",
            "assigned_to", "claimable", "family_visible", "completed",
        ]
        widgets = {"due_at": DateTimeLocalInput(format="%Y-%m-%dT%H:%M")}

    def __init__(self, *args, team=None, season=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.season = season
        if team:
            self.fields["event"].queryset = team.events.filter(starts_at__gte=timezone.now()).order_by("starts_at")
            self.fields["show"].queryset = team.shows.order_by("-show_date")
            self.fields["rider"].queryset = team.riders.filter(active=True).order_by("last_name", "first_name")
            self.fields["assigned_to"].queryset = User.objects.filter(
                profile__team=team, is_active=True
            ).order_by("last_name", "first_name", "username")

    def clean(self):
        cleaned = super().clean()
        event = cleaned.get("event")
        show = cleaned.get("show")
        rider = cleaned.get("rider")
        assigned = cleaned.get("assigned_to")
        if event and self.team and event.team_id != self.team.id:
            self.add_error("event", "Choose an event for this team.")
        if show and self.team and show.team_id != self.team.id:
            self.add_error("show", "Choose a show for this team.")
        if rider and self.team and rider.team_id != self.team.id:
            self.add_error("rider", "Choose a rider for this team.")
        if assigned and hasattr(assigned, "profile") and self.team and assigned.profile.team_id != self.team.id:
            self.add_error("assigned_to", "Choose a team member.")
        return cleaned





class HistoricalResultEditForm(forms.Form):
    season_class = forms.ModelChoiceField(
        queryset=SeasonClass.objects.none(),
        label="Class",
    )
    competition_track = forms.ChoiceField(
        choices=[
            (ShowEntry.CompetitionTrack.REGULAR, "Regular season"),
            (ShowEntry.CompetitionTrack.INDIVIDUAL, "Individual finals"),
            (ShowEntry.CompetitionTrack.TEAM, "Team finals"),
        ],
        label="Competition track",
    )
    place = forms.IntegerField(min_value=1, max_value=999, required=False)
    manual_points = forms.BooleanField(
        required=False,
        label="Use manually entered points",
    )
    points = forms.DecimalField(
        max_digits=5,
        decimal_places=1,
        min_value=0,
        required=False,
    )
    horse_name = forms.CharField(max_length=100, required=False, label="Horse")
    notes = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, entry=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.entry = entry
        if entry:
            membership = SeasonMembership.objects.filter(
                season=entry.show_class.show.season,
                rider=entry.rider,
            ).prefetch_related("classes").first()
            if membership:
                self.fields["season_class"].queryset = membership.classes.all().order_by(
                    "sort_order", "name"
                )
            show = entry.show_class.show
            if show.competition_level == Show.CompetitionLevel.REGULAR:
                self.fields["competition_track"].choices = [
                    (ShowEntry.CompetitionTrack.REGULAR, "Regular season")
                ]
            else:
                self.fields["competition_track"].choices = [
                    (ShowEntry.CompetitionTrack.INDIVIDUAL, "Individual finals"),
                    (ShowEntry.CompetitionTrack.TEAM, "Team finals"),
                ]

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("manual_points"):
            cleaned["points"] = None
        elif cleaned.get("points") is None:
            self.add_error("points", "Enter points when manual points are enabled.")

        season_class = cleaned.get("season_class")
        track = cleaned.get("competition_track")
        if (
            season_class
            and track == ShowEntry.CompetitionTrack.TEAM
        ):
            code = (season_class.name or "").strip().upper()
            if code.startswith("H8 ") or code.startswith("H14 ") or code in {"H8", "H14"}:
                self.add_error("competition_track", "H8 and H14 Walk/Trot are individual-only.")
        return cleaned


class HistoricalImportUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Historical results CSV",
        help_text="UTF-8 CSV, maximum 2 MB. AccessIEA Rider Performance exports are detected automatically; the portal template is also supported.",
    )
    bootstrap_missing = forms.BooleanField(
        required=False,
        initial=True,
        label="Create missing historical roster/classes",
        help_text=(
            "For AccessIEA Rider Performance exports, propose missing riders, season "
            "memberships, class assignments, and season classes during preview. "
            "Nothing is created until you commit the import."
        ),
    )

    def clean_csv_file(self):
        upload = self.cleaned_data["csv_file"]
        if upload.size > 2 * 1024 * 1024:
            raise ValidationError("Historical import files must be 2 MB or smaller.")
        if not upload.name.lower().endswith(".csv"):
            raise ValidationError("Historical import currently accepts CSV files only.")
        return upload


class HistoricalResultHeaderForm(forms.Form):
    season = forms.ModelChoiceField(queryset=Season.objects.none())
    competition_level = forms.ChoiceField(
        choices=Show.CompetitionLevel.choices,
        initial=Show.CompetitionLevel.REGULAR,
        label="Competition level",
        help_text="Choose Regular Season, Region Finals, Zone Finals, or National Finals.",
    )
    show_name = forms.CharField(max_length=180, label="Show name")
    show_date = forms.DateField(widget=DateInput(), label="Show date")
    venue = forms.CharField(max_length=180, required=False)
    futures_team_place = forms.IntegerField(
        min_value=1, max_value=999, required=False, label="Futures overall team place",
        help_text="For finals shows, enter the team's overall placing if applicable.",
    )
    upper_team_place = forms.IntegerField(
        min_value=1, max_value=999, required=False, label="Upper School overall team place",
        help_text="For finals shows, enter the team's overall placing if applicable.",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Optional note about the source of these historical results.",
    )

    def __init__(self, *args, team=None, rider=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.rider = rider
        if team and rider:
            self.fields["season"].queryset = Season.objects.filter(
                team=team, memberships__rider=rider
            ).distinct().order_by("-start_date")


class HistoricalResultLineForm(forms.Form):
    competition_track = forms.ChoiceField(
        choices=[
            ("", "Choose track…"),
            (ShowEntry.CompetitionTrack.INDIVIDUAL, "Individual"),
            (ShowEntry.CompetitionTrack.TEAM, "Team"),
        ],
        required=False,
        label="Track",
        help_text="Used for Region, Zone, and National Finals.",
    )
    season_class = forms.ModelChoiceField(
        queryset=SeasonClass.objects.none(),
        required=False,
        label="Class",
    )
    place = forms.IntegerField(min_value=1, max_value=999, required=False)
    points = forms.DecimalField(max_digits=5, decimal_places=1, min_value=0, required=False)
    horse_name = forms.CharField(max_length=100, required=False, label="Horse")
    notes = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, season=None, rider=None, competition_level=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season
        self.rider = rider
        self.competition_level = competition_level or Show.CompetitionLevel.REGULAR
        if season and rider:
            membership = SeasonMembership.objects.filter(
                season=season, rider=rider
            ).prefetch_related("classes").first()
            if membership:
                self.fields["season_class"].queryset = membership.classes.all().order_by(
                    "sort_order", "name"
                )

    def clean(self):
        cleaned = super().clean()
        competition_track = cleaned.get("competition_track")
        season_class = cleaned.get("season_class")
        place = cleaned.get("place")
        points = cleaned.get("points")
        horse_name = cleaned.get("horse_name")
        notes = cleaned.get("notes")
        has_any = any([
            competition_track is not None,
            season_class is not None,
            place is not None,
            points is not None,
            bool(horse_name),
            bool(notes),
        ])
        if not has_any:
            cleaned["DELETE"] = True
            return cleaned
        if not season_class:
            self.add_error("season_class", "Choose a class for this result.")
        if self.competition_level != Show.CompetitionLevel.REGULAR and not competition_track:
            self.add_error("competition_track", "Choose Individual or Team for a finals result.")
        if (
            self.competition_level != Show.CompetitionLevel.REGULAR
            and competition_track == ShowEntry.CompetitionTrack.TEAM
            and season_class
        ):
            code = (season_class.name or "").strip().upper()
            if code.startswith("H8 ") or code.startswith("H14 ") or code in {"H8", "H14"}:
                self.add_error("competition_track", "H8 and H14 Walk/Trot are individual-only.")
        if place is None and points is None:
            self.add_error("place", "Enter a placing, points, or both.")
        return cleaned


HistoricalResultFormSet = formset_factory(
    HistoricalResultLineForm,
    extra=4,
    max_num=12,
    validate_max=True,
)

class FinancialAccountForm(forms.ModelForm):
    class Meta:
        model = FinancialAccount
        fields = ["name", "account_type", "opening_balance", "active", "notes"]


class FinancialCategoryForm(forms.ModelForm):
    class Meta:
        model = FinancialCategory
        fields = ["name", "kind", "active", "sort_order"]


class FinancialTransactionForm(forms.ModelForm):
    class Meta:
        model = FinancialTransaction
        fields = [
            "season", "transaction_date", "kind", "account", "category", "amount",
            "payee", "description", "rider", "receipt", "reference", "notes",
        ]
        widgets = {"transaction_date": DateInput()}

    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        if team:
            self.fields["season"].queryset = Season.objects.filter(team=team)
            account_qs = FinancialAccount.objects.filter(team=team, active=True)
            category_qs = FinancialCategory.objects.filter(team=team, active=True)
            if self.instance and self.instance.pk:
                account_qs = FinancialAccount.objects.filter(team=team).filter(
                    Q(active=True) | Q(pk=self.instance.account_id)
                )
                category_qs = FinancialCategory.objects.filter(team=team).filter(
                    Q(active=True) | Q(pk=self.instance.category_id)
                )
            self.fields["account"].queryset = account_qs.distinct()
            self.fields["category"].queryset = category_qs.distinct()
            self.fields["rider"].queryset = Rider.objects.filter(team=team, active=True)
        self.fields["rider"].required = False
        self.fields["receipt"].help_text = "Optional PDF, JPG, JPEG, or PNG receipt. Maximum 10 MB."

    def clean_receipt(self):
        receipt = self.cleaned_data.get("receipt")
        if not receipt:
            return receipt
        name = receipt.name.lower()
        if not name.endswith((".pdf", ".jpg", ".jpeg", ".png")):
            raise ValidationError("Receipts must be PDF, JPG, JPEG, or PNG files.")
        if receipt.size > 10 * 1024 * 1024:
            raise ValidationError("Receipt files must be 10 MB or smaller.")
        return receipt

    def clean(self):
        cleaned = super().clean()
        if not self.team:
            return cleaned
        obj = self.instance
        obj.team = self.team
        for field in ["season", "account", "category", "rider", "kind", "amount"]:
            if field in cleaned:
                setattr(obj, field, cleaned.get(field))
        try:
            obj.clean()
        except ValidationError as exc:
            raise exc
        return cleaned


class SeasonBudgetForm(forms.ModelForm):
    class Meta:
        model = SeasonBudget
        fields = ["category", "kind", "amount", "notes"]

    def __init__(self, *args, season=None, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season
        if team:
            qs = FinancialCategory.objects.filter(team=team, active=True)
            if self.instance and self.instance.pk:
                qs = FinancialCategory.objects.filter(team=team).filter(
                    Q(active=True) | Q(pk=self.instance.category_id)
                )
            self.fields["category"].queryset = qs.distinct()

    def clean(self):
        cleaned = super().clean()
        if self.season:
            self.instance.season = self.season
        try:
            self.instance.clean()
        except ValidationError as exc:
            raise exc
        return cleaned

class HomeBarnForm(forms.ModelForm):
    class Meta:
        model = HomeBarn
        fields = ["name", "active", "notes"]


class MembershipDuesRateForm(forms.ModelForm):
    class Meta:
        model = MembershipDuesRate
        fields = ["home_barn", "amount", "due_date", "notes"]
        widgets = {"due_date": DateInput()}

    def __init__(self, *args, team=None, season=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season
        if team:
            qs = HomeBarn.objects.filter(team=team, active=True)
            if self.instance and self.instance.pk:
                qs = HomeBarn.objects.filter(team=team).filter(Q(active=True) | Q(pk=self.instance.home_barn_id))
            self.fields["home_barn"].queryset = qs.distinct()

    def clean(self):
        cleaned = super().clean()
        if self.season:
            self.instance.season = self.season
        if cleaned.get("home_barn"):
            self.instance.home_barn = cleaned["home_barn"]
        if cleaned.get("amount") is not None:
            self.instance.amount = cleaned["amount"]
        self.instance.clean()
        return cleaned


class FamilyChargeForm(forms.ModelForm):
    class Meta:
        model = FamilyCharge
        fields = ["charge_type", "description", "amount", "charge_date", "due_date", "show", "status", "notes"]
        widgets = {"charge_date": DateInput(), "due_date": DateInput()}

    def __init__(self, *args, membership=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.membership = membership
        if membership:
            self.fields["show"].queryset = Show.objects.filter(season=membership.season)

    def clean(self):
        cleaned = super().clean()
        if self.membership:
            self.instance.membership = self.membership
        for name in ["amount", "show"]:
            if name in cleaned:
                setattr(self.instance, name, cleaned.get(name))
        self.instance.clean()
        return cleaned


class FamilyCreditForm(forms.ModelForm):
    class Meta:
        model = FamilyCredit
        fields = ["credit_type", "amount", "source", "status", "notes"]

    def clean(self):
        cleaned = super().clean()
        amount = cleaned.get("amount")
        if amount is not None and amount <= 0:
            self.add_error("amount", "Credit amount must be greater than zero.")
        return cleaned


class ServiceAgreementCreditForm(forms.ModelForm):
    class Meta:
        model = ServiceAgreementCredit
        fields = ["charge", "description", "amount", "required_shows", "status", "completed_date", "notes"]
        widgets = {
            "required_shows": forms.CheckboxSelectMultiple,
            "completed_date": DateInput(),
        }

    def __init__(self, *args, membership=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.membership = membership
        if membership:
            self.fields["charge"].queryset = FamilyCharge.objects.filter(membership=membership)
            self.fields["required_shows"].queryset = Show.objects.filter(season=membership.season)

    def clean(self):
        cleaned = super().clean()
        if self.membership:
            self.instance.membership = self.membership
        for name in ["charge", "amount"]:
            if name in cleaned:
                setattr(self.instance, name, cleaned.get(name))
        self.instance.clean()
        if cleaned.get("status") == ServiceAgreementCredit.Status.APPLIED and not cleaned.get("completed_date"):
            self.add_error("completed_date", "Enter the date the service obligation was completed.")
        return cleaned


class FinancialAssistanceAwardForm(forms.ModelForm):
    class Meta:
        model = FinancialAssistanceAward
        fields = [
            "provider", "program_name", "approved_maximum", "award_date", "reference",
            "eligible_expenses", "status", "notes",
        ]
        widgets = {"award_date": DateInput()}

    def clean(self):
        cleaned = super().clean()
        amount = cleaned.get("approved_maximum")
        if amount is not None and amount <= 0:
            self.add_error("approved_maximum", "Approved award amount must be greater than zero.")
        return cleaned


class AssistanceClaimForm(forms.ModelForm):
    class Meta:
        model = AssistanceClaim
        fields = [
            "charge", "family_relief_amount", "amount_requested", "amount_approved",
            "reimbursed_amount", "status", "submitted_date", "approved_date", "received_date",
            "reimbursement_account", "reimbursement_category", "reference", "notes",
        ]
        widgets = {
            "submitted_date": DateInput(),
            "approved_date": DateInput(),
            "received_date": DateInput(),
        }

    def __init__(self, *args, award=None, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.award = award
        if award:
            self.fields["charge"].queryset = FamilyCharge.objects.filter(membership=award.membership)
        if team:
            self.fields["reimbursement_account"].queryset = FinancialAccount.objects.filter(team=team, active=True)
            self.fields["reimbursement_category"].queryset = FinancialCategory.objects.filter(
                team=team, active=True, kind__in=[FinancialCategory.Kind.INCOME, FinancialCategory.Kind.BOTH]
            )

    def clean(self):
        cleaned = super().clean()
        if self.award:
            self.instance.award = self.award
        for name in [
            "charge", "family_relief_amount", "amount_requested", "amount_approved",
            "reimbursed_amount", "status", "received_date", "reimbursement_account",
            "reimbursement_category",
        ]:
            if name in cleaned:
                setattr(self.instance, name, cleaned.get(name))
        self.instance.clean()
        if self.award and cleaned.get("family_relief_amount") is not None:
            existing = sum(
                (c.family_relief_amount for c in self.award.claims.exclude(
                    status__in=[AssistanceClaim.Status.DENIED, AssistanceClaim.Status.CANCELLED]
                ).exclude(pk=getattr(self.instance, "pk", None))),
                0,
            )
            if existing + cleaned["family_relief_amount"] > self.award.approved_maximum:
                self.add_error("family_relief_amount", "This would exceed the award's approved maximum.")
        return cleaned


class FamilyPaymentForm(forms.ModelForm):
    class Meta:
        model = FamilyPayment
        fields = ["charge", "amount", "received_date", "account", "category", "method", "reference", "notes"]
        widgets = {"received_date": DateInput()}

    def __init__(self, *args, membership=None, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.membership = membership
        if membership:
            self.fields["charge"].queryset = FamilyCharge.objects.filter(membership=membership)
        if team:
            self.fields["account"].queryset = FinancialAccount.objects.filter(team=team, active=True)
            self.fields["category"].queryset = FinancialCategory.objects.filter(
                team=team, active=True, kind__in=[FinancialCategory.Kind.INCOME, FinancialCategory.Kind.BOTH]
            )

    def clean(self):
        cleaned = super().clean()
        if self.membership:
            self.instance.membership = self.membership
        for name in ["charge", "amount", "account", "category"]:
            if name in cleaned:
                setattr(self.instance, name, cleaned.get(name))
        self.instance.clean()
        return cleaned



class FundraisingPolicyForm(forms.ModelForm):
    allowed_charge_types = forms.MultipleChoiceField(
        choices=FamilyCharge.ChargeType.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Family charges fundraising may offset",
        help_text="Leave all unchecked to allow any family charge type.",
    )

    class Meta:
        model = FundraisingPolicy
        fields = [
            "model", "default_family_credit_percent", "participation_optional",
            "allowed_charge_types", "family_message", "notes",
        ]
        widgets = {
            "family_message": forms.Textarea(attrs={"rows": 5}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "model": "Fundraising model",
            "default_family_credit_percent": "Default family credit %",
            "participation_optional": "Family participation is optional",
            "family_message": "Message shown to families",
        }

    def __init__(self, *args, season=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season
        if season:
            self.instance.season = season
        if self.instance.pk:
            self.initial["allowed_charge_types"] = self.instance.allowed_charge_types or []
        self.fields["default_family_credit_percent"].help_text = (
            "Team-wide must be 0%. Family Credit must be 100%. "
            "For Hybrid, set the normal percentage credited to a participating family."
        )

    def clean(self):
        cleaned = super().clean()
        if self.season:
            self.instance.season = self.season
        self.instance.allowed_charge_types = cleaned.get("allowed_charge_types") or []
        for name in ["model", "default_family_credit_percent", "participation_optional", "family_message", "notes"]:
            if name in cleaned:
                setattr(self.instance, name, cleaned.get(name))
        try:
            self.instance.clean()
        except ValidationError as exc:
            raise exc
        return cleaned


class FundraisingCampaignForm(forms.ModelForm):
    class Meta:
        model = FundraisingCampaign
        fields = ["name", "description", "start_date", "end_date", "goal_amount", "status", "notes"]
        widgets = {
            "start_date": DateInput(),
            "end_date": DateInput(),
            "description": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        self.instance.clean()
        return cleaned


class FundraisingContributionForm(forms.ModelForm):
    class Meta:
        model = FundraisingContribution
        fields = [
            "received_date", "donor_name", "amount", "beneficiary_membership",
            "family_credit_amount", "family_charge", "account", "category",
            "method", "reference", "notes",
        ]
        widgets = {
            "received_date": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "beneficiary_membership": "Rider / family attribution (optional)",
            "family_credit_amount": "Amount credited to family (optional)",
            "family_charge": "Family charge to reduce",
        }

    def __init__(self, *args, campaign=None, policy=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.campaign = campaign
        self.policy = policy
        if campaign:
            self.instance.campaign = campaign
            self.fields["beneficiary_membership"].queryset = (
                SeasonMembership.objects.filter(season=campaign.season)
                .select_related("rider")
                .order_by("rider__last_name", "rider__first_name")
            )
            self.fields["family_charge"].queryset = (
                FamilyCharge.objects.filter(membership__season=campaign.season)
                .select_related("membership__rider")
                .order_by("membership__rider__last_name", "membership__rider__first_name", "due_date", "id")
            )
            self.fields["account"].queryset = FinancialAccount.objects.filter(team=campaign.team, active=True)
            self.fields["category"].queryset = FinancialCategory.objects.filter(
                team=campaign.team,
                active=True,
                kind__in=[FinancialCategory.Kind.INCOME, FinancialCategory.Kind.BOTH],
            )
        self.fields["beneficiary_membership"].required = False
        self.fields["family_charge"].required = False
        self.fields["family_credit_amount"].required = False
        if not self.instance.pk:
            self.initial["family_credit_amount"] = None
        if self.policy:
            self.fields["family_credit_amount"].help_text = (
                f"Season policy: {self.policy.get_model_display()} · "
                f"default family credit {self.policy.default_family_credit_percent:.2f}%. "
                "The Treasurer may override the amount when circumstances require it."
            )
        else:
            self.fields["family_credit_amount"].help_text = (
                "Leave at $0 when the contribution stays entirely with the team. "
                "If entered, select the rider/family and the specific charge to reduce."
            )

    def clean(self):
        cleaned = super().clean()
        if self.campaign:
            self.instance.campaign = self.campaign
        for name in [
            "received_date", "amount", "beneficiary_membership", "family_credit_amount",
            "family_charge", "account", "category",
        ]:
            if name in cleaned:
                setattr(self.instance, name, cleaned.get(name))
        try:
            self.instance.clean()
        except ValidationError as exc:
            raise exc

        credit_amount = cleaned.get("family_credit_amount")
        beneficiary = cleaned.get("beneficiary_membership")
        amount = cleaned.get("amount")

        if credit_amount in (None, "") and self.policy and beneficiary and amount:
            credit_amount = self.policy.default_credit_for(amount)
            cleaned["family_credit_amount"] = credit_amount
            self.instance.family_credit_amount = credit_amount
        credit_amount = credit_amount or 0

        charge = cleaned.get("family_charge")
        if self.policy and charge and not self.policy.charge_type_allowed(charge):
            self.add_error(
                "family_charge",
                f"This season's fundraising policy does not allow credits against {charge.get_charge_type_display()} charges.",
            )
        if self.policy and self.policy.model == FundraisingPolicy.Model.TEAM_WIDE and credit_amount:
            self.add_error(
                "family_credit_amount",
                "This season uses Team-wide fundraising, so family credits are not permitted.",
            )

        # Persist an explicit zero rather than None for contributions that do
        # not create a family credit.
        if not credit_amount:
            credit_amount = Decimal("0")
            cleaned["family_credit_amount"] = credit_amount
            self.instance.family_credit_amount = credit_amount

        if charge and not credit_amount:
            self.add_error("family_credit_amount", "Enter the amount of the contribution to credit to this family charge.")
        if credit_amount and charge:
            available = charge.balance
            existing_credit = getattr(self.instance, "family_credit", None)
            if existing_credit and existing_credit.charge_id == charge.pk and existing_credit.status == FamilyCredit.Status.APPLIED:
                available += existing_credit.amount
            if credit_amount > available:
                self.add_error(
                    "family_credit_amount",
                    f"Family fundraising credit cannot exceed this charge's available balance of ${available:.2f}.",
                )
        return cleaned


class ShowBudgetLineForm(forms.ModelForm):
    class Meta:
        model = ShowBudgetLine
        fields = ["scope", "kind", "category", "description", "amount", "notes"]

    def __init__(self, *args, show=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.show = show
        if show:
            self.instance.show = show
            self.fields["category"].queryset = FinancialCategory.objects.filter(
                team=show.team, active=True
            )
            if show.financial_role != Show.FinancialRole.HOSTING_ATTENDING:
                self.fields["scope"].choices = [
                    (ShowBudgetLine.Scope.PARTICIPATION, "Our team participation")
                ]

    def clean(self):
        cleaned = super().clean()
        if self.show:
            self.instance.show = self.show

        scope = cleaned.get("scope")
        kind = cleaned.get("kind")
        category = cleaned.get("category")

        if (
            self.show
            and scope == ShowBudgetLine.Scope.HOSTING
            and self.show.financial_role != Show.FinancialRole.HOSTING_ATTENDING
        ):
            self.add_error(
                "scope",
                "Hosting budget lines require a show marked Hosting & attending.",
            )

        if category and kind:
            allowed = {
                FinancialCategory.Kind.INCOME: {FinancialTransaction.Kind.INCOME},
                FinancialCategory.Kind.EXPENSE: {FinancialTransaction.Kind.EXPENSE},
                FinancialCategory.Kind.BOTH: {
                    FinancialTransaction.Kind.INCOME,
                    FinancialTransaction.Kind.EXPENSE,
                },
            }[category.kind]
            if kind not in allowed:
                self.add_error(
                    "kind",
                    f"{category.name} is configured as {category.get_kind_display().lower()} "
                    "and cannot be used for this budget type.",
                )



        return cleaned


class ReimbursementRequestForm(forms.ModelForm):
    class Meta:
        model = ReimbursementRequest
        fields = ["season", "show", "show_finance_scope", "payee_name", "expense_date", "category", "amount", "description", "receipt", "notes"]
        widgets = {"expense_date": DateInput()}

    def __init__(self, *args, team=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team:
            self.fields["season"].queryset = Season.objects.filter(team=team)
            self.fields["show"].queryset = Show.objects.filter(team=team)
            self.fields["category"].queryset = FinancialCategory.objects.filter(team=team, active=True).exclude(kind=FinancialCategory.Kind.INCOME)
        self.fields["show_finance_scope"].required = False
        self.fields["show_finance_scope"].help_text = "If this expense belongs to a show, choose Hosting operations or Our team participation."
        if user and not self.instance.pk:
            self.fields["payee_name"].initial = user.get_full_name() or user.username


class ReimbursementReviewForm(forms.ModelForm):
    class Meta:
        model = ReimbursementRequest
        fields = ["status", "rejection_reason", "paid_date", "payment_account", "notes"]
        widgets = {"paid_date": DateInput()}

    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            (ReimbursementRequest.Status.SUBMITTED, "Submitted"),
            (ReimbursementRequest.Status.APPROVED, "Approved"),
            (ReimbursementRequest.Status.REJECTED, "Rejected"),
            (ReimbursementRequest.Status.PAID, "Paid"),
        ]
        if team:
            self.fields["payment_account"].queryset = FinancialAccount.objects.filter(team=team, active=True)


class ShowFundingPolicyForm(forms.ModelForm):
    class Meta:
        model = Season
        fields = [
            "regular_show_fee_policy", "regional_show_fee_policy", "zone_show_fee_policy",
            "national_show_fee_policy", "other_show_fee_policy", "default_rider_show_fee",
            "dues_coverage_notes",
        ]
        labels = {
            "regular_show_fee_policy": "Regular-season shows",
            "regional_show_fee_policy": "Region Finals",
            "zone_show_fee_policy": "Zone Finals",
            "national_show_fee_policy": "National Finals",
            "other_show_fee_policy": "Other / special events",
            "default_rider_show_fee": "Default rider show fee",
            "dues_coverage_notes": "What dues / show package covers",
        }


class ShowTransactionAllocationForm(forms.ModelForm):
    class Meta:
        model = ShowTransactionAllocation
        fields = ["show", "scope", "budget_line", "amount", "notes"]
        labels = {"budget_line": "Budget item (optional)"}

    def __init__(self, *args, transaction=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.transaction = transaction
        self.fields["budget_line"].required = False
        self.fields["budget_line"].help_text = (
            "Optional. Assign this allocation to a specific show budget item so Plan vs Actual "
            "tracks items such as Insurance, Judge fee, Food, or Facility rental separately."
        )
        self.fields["budget_line"].queryset = ShowBudgetLine.objects.none()

        if transaction:
            self.fields["show"].queryset = Show.objects.filter(
                team=transaction.team, season=transaction.season
            ).order_by("show_date", "name")
            self.fields["amount"].help_text = (
                f"Transaction total: ${transaction.amount}. "
                "The sum of all show allocations cannot exceed this amount."
            )

            show_id = None
            scope = None
            if self.is_bound:
                show_id = self.data.get(self.add_prefix("show"))
                scope = self.data.get(self.add_prefix("scope"))
            elif self.instance and self.instance.pk:
                show_id = self.instance.show_id
                scope = self.instance.scope

            if show_id:
                qs = ShowBudgetLine.objects.filter(
                    show_id=show_id,
                    category=transaction.category,
                    kind=transaction.kind,
                )
                if scope:
                    qs = qs.filter(scope=scope)
                self.fields["budget_line"].queryset = qs.select_related("category").order_by(
                    "description", "id"
                )

    def clean(self):
        cleaned = super().clean()
        if self.transaction:
            self.instance.transaction = self.transaction
        try:
            self.instance.clean()
        except ValidationError as exc:
            raise exc
        return cleaned
