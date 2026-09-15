from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from portal.model_modules.people import (
    Committee,
    CommitteeMembership,
    OrganizationGroup,
    OrganizationRoleAssignment,
    Person,
    PersonRelationship,
)
from portal.models import UserProfile


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            "user", "first_name", "last_name", "preferred_name", "email", "phone", "birth_date",
            "school", "graduation_year", "bio", "photo", "website_url", "instagram_url",
            "youtube_url", "public_profile_enabled", "active",
        ]
        widgets = {"birth_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = User.objects.none()
        if team is not None:
            qs = User.objects.filter(profile__team=team).filter(
                Q(arena_person__isnull=True) | Q(arena_person=self.instance if getattr(self.instance, "pk", None) else None)
            ).order_by("last_name", "first_name", "username")
        self.fields["user"].queryset = qs
        self.fields["user"].required = False
        self.fields["user"].help_text = "Optional login account for this person. Identity and participation remain on the Person record."


class PersonLoginAccessForm(forms.Form):
    username = forms.CharField(max_length=150)
    role = forms.ChoiceField(choices=UserProfile.Role.choices)
    temporary_password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    def __init__(self, *args, person=None, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.person = person
        self.actor = actor
        if person is not None and not self.is_bound:
            self.fields["username"].initial = self._suggest_username(person)

    @staticmethod
    def _suggest_username(person):
        base = ".".join(part.lower() for part in [person.preferred_name or person.first_name, person.last_name] if part).replace(" ", "")
        return base or f"person{person.pk or ''}"

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is already in use.")
        return username

    def clean_role(self):
        role = self.cleaned_data["role"]
        actor_role = getattr(getattr(self.actor, "profile", None), "role", None)
        if role == UserProfile.Role.ADMIN and not (getattr(self.actor, "is_superuser", False) or actor_role == UserProfile.Role.ADMIN):
            raise ValidationError("Only an administrator can grant administrator access.")
        return role


class PersonRolesForm(forms.Form):
    roles = forms.MultipleChoiceField(
        choices=OrganizationRoleAssignment.Role.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select every role this person currently holds.",
    )

    def __init__(self, *args, person=None, **kwargs):
        super().__init__(*args, **kwargs)
        if person is not None and not self.is_bound:
            today = timezone.localdate()
            current_roles = OrganizationRoleAssignment.objects.filter(
                person=person,
                team=person.team,
                active=True,
            ).filter(
                Q(start_date__isnull=True) | Q(start_date__lte=today),
                Q(end_date__isnull=True) | Q(end_date__gt=today),
            ).values_list("role", flat=True)
            self.fields["roles"].initial = list(current_roles)


class OrganizationRoleAssignmentForm(forms.ModelForm):
    class Meta:
        model = OrganizationRoleAssignment
        fields = ["start_date", "end_date", "active", "notes"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"})}


class PersonRelationshipForm(forms.ModelForm):
    def __init__(self, *args, team=None, source_person=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Person.objects.none()
        if team is not None:
            qs = Person.objects.filter(team=team, active=True)
            if source_person is not None:
                qs = qs.exclude(pk=source_person.pk)
        self.fields["to_person"].queryset = qs.order_by("last_name", "first_name")
        self.fields["to_person"].label = "Related person"
    class Meta:
        model = PersonRelationship
        fields = ["to_person", "relationship_type", "label", "primary_contact", "start_date", "end_date", "active", "notes"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"})}


class OrganizationGroupForm(forms.ModelForm):
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team is not None: self.instance.team = team
        qs = OrganizationGroup.objects.none()
        if team is not None:
            qs = OrganizationGroup.objects.filter(team=team, active=True)
            if getattr(self.instance, "pk", None): qs = qs.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = qs.order_by("sort_order", "name")
    class Meta:
        model = OrganizationGroup
        fields = ["name", "group_type", "parent", "description", "active", "sort_order"]


class CommitteeForm(forms.ModelForm):
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team is not None: self.instance.team = team
        self.fields["group"].queryset = OrganizationGroup.objects.filter(team=team, active=True).order_by("sort_order", "name") if team is not None else OrganizationGroup.objects.none()
    class Meta:
        model = Committee
        fields = ["name", "group", "purpose", "active", "sort_order"]


class CommitteeMembershipForm(forms.ModelForm):
    def __init__(self, *args, team=None, person=None, **kwargs):
        super().__init__(*args, **kwargs)
        if person is not None:
            self.instance.person = person
            self.fields.pop("person", None)
        elif team is not None:
            self.fields["person"].queryset = Person.objects.filter(team=team, active=True).order_by("last_name", "first_name")
        else:
            self.fields["person"].queryset = Person.objects.none()
        if team is not None:
            self.fields["committee"].queryset = Committee.objects.filter(team=team, active=True).order_by("sort_order", "name")
        else:
            self.fields["committee"].queryset = Committee.objects.none()
    class Meta:
        model = CommitteeMembership
        fields = ["committee", "person", "position", "start_date", "end_date", "active", "notes"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"})}
