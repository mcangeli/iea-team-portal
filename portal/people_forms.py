from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
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
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team is not None:
            self.instance.team = team
        user_field = self.fields["user"]
        if team is None:
            user_field.queryset = User.objects.none()
        else:
            available = User.objects.filter(profile__team=team)
            current_user_id = getattr(self.instance, "user_id", None)
            if current_user_id:
                available = available.filter(Q(arena_person__isnull=True) | Q(pk=current_user_id))
            else:
                available = available.filter(arena_person__isnull=True)
            user_field.queryset = available.order_by("last_name", "first_name", "username")
        user_field.required = False
        user_field.help_text = "Optional existing login access for this person. New access should be created from the Person profile."

    class Meta:
        model = Person
        fields = ["user", "first_name", "last_name", "preferred_name", "email", "phone", "birth_date", "school", "graduation_year", "bio", "photo", "website_url", "instagram_url", "youtube_url", "public_profile_enabled", "active"]
        widgets = {"birth_date": forms.DateInput(attrs={"type": "date"}), "bio": forms.Textarea(attrs={"rows": 5})}


class PersonLoginAccessForm(forms.Form):
    username = forms.CharField(max_length=150)
    role = forms.ChoiceField(choices=UserProfile.Role.choices, label="Access role")
    temporary_password = forms.CharField(required=False, widget=forms.PasswordInput(render_value=False), help_text="Leave blank to use DEFAULT_TEMP_PASSWORD from the server environment.")

    def __init__(self, *args, person=None, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.person = person
        self.actor = actor
        if person:
            suggested = f"{person.first_name}.{person.last_name}".lower().replace(" ", "")
            self.fields["username"].initial = suggested
        if actor and not (actor.is_superuser or (hasattr(actor, "profile") and actor.profile.role == UserProfile.Role.ADMIN)):
            self.fields["role"].choices = [(UserProfile.Role.PARENT, "Parent/Guardian"), (UserProfile.Role.RIDER, "Rider")]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already in use.")
        return username

    def clean(self):
        cleaned = super().clean()
        if self.person and self.person.user_id:
            self.add_error(None, "This Person already has login access. Manage the existing account instead.")
        role = cleaned.get("role")
        if role in {UserProfile.Role.ADMIN, UserProfile.Role.COACH}:
            is_admin = self.actor and (self.actor.is_superuser or (hasattr(self.actor, "profile") and self.actor.profile.role == UserProfile.Role.ADMIN))
            if not is_admin:
                self.add_error("role", "Only administrators can create Coach or Administrator access.")
        temp = cleaned.get("temporary_password") or settings.DEFAULT_TEMP_PASSWORD
        if not temp:
            self.add_error("temporary_password", "Enter a temporary password or configure DEFAULT_TEMP_PASSWORD on the server.")
        else:
            candidate = User(username=cleaned.get("username", ""), first_name=getattr(self.person, "first_name", ""), last_name=getattr(self.person, "last_name", ""), email=getattr(self.person, "email", ""))
            try:
                validate_password(temp, user=candidate)
            except ValidationError as exc:
                self.add_error("temporary_password", exc)
            cleaned["resolved_password"] = temp
        return cleaned

    @transaction.atomic
    def save(self):
        person = Person.objects.select_for_update().get(pk=self.person.pk, team=self.person.team)
        if person.user_id:
            raise ValidationError("This Person already has login access.")
        user = User.objects.create_user(username=self.cleaned_data["username"], email=person.email, password=self.cleaned_data["resolved_password"], first_name=person.first_name, last_name=person.last_name)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.team = person.team
        profile.role = self.cleaned_data["role"]
        profile.must_change_password = True
        profile.save(update_fields=["team", "role", "must_change_password"])
        person.user = user
        person.save(update_fields=["user", "updated_at"])
        bridge = getattr(person, "legacy_identity", None)
        if bridge:
            if bridge.rider_id:
                bridge.rider.user = user
                bridge.rider.save(update_fields=["user"])
            if bridge.guardian_id:
                bridge.guardian.user = user
                bridge.guardian.save(update_fields=["user"])
                for link in bridge.guardian.rider_links.select_related("rider").all():
                    link.rider.guardians.add(user)
        return user


class PersonRolesForm(forms.Form):
    roles = forms.MultipleChoiceField(choices=OrganizationRoleAssignment.Role.choices, required=False, widget=forms.CheckboxSelectMultiple, help_text="Choose every role this person currently holds. Multiple roles may be active at the same time.")

    def __init__(self, *args, person=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.person = person
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
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team is not None:
            self.fields["person"].queryset = Person.objects.filter(team=team, active=True).order_by("last_name", "first_name")
            self.fields["committee"].queryset = Committee.objects.filter(team=team, active=True).order_by("sort_order", "name")
        else:
            self.fields["person"].queryset = Person.objects.none()
            self.fields["committee"].queryset = Committee.objects.none()
    class Meta:
        model = CommitteeMembership
        fields = ["committee", "person", "position", "start_date", "end_date", "active", "notes"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}), "end_date": forms.DateInput(attrs={"type": "date"})}