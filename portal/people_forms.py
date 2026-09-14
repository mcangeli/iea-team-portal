from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from portal.model_modules.people import (
    Committee,
    CommitteeMembership,
    OrganizationGroup,
    OrganizationRoleAssignment,
    Person,
    PersonRelationship,
)


class PersonForm(forms.ModelForm):
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team is not None:
            # The organization is trusted request context, not user-editable form
            # data. Set it before ModelForm validation so Person.clean() can
            # validate an attached Django account against the correct tenant.
            self.instance.team = team
        user_field = self.fields["user"]
        if team is None:
            user_field.queryset = User.objects.none()
        else:
            available = User.objects.filter(profile__team=team)
            current_user_id = getattr(self.instance, "user_id", None)
            if current_user_id:
                available = available.filter(
                    Q(arena_person__isnull=True) | Q(pk=current_user_id)
                )
            else:
                available = available.filter(arena_person__isnull=True)
            user_field.queryset = available.order_by(
                "last_name", "first_name", "username"
            )
        user_field.required = False
        user_field.help_text = (
            "Optional Django login for this person. One login can be connected to only one ArenaLine Person."
        )

    class Meta:
        model = Person
        fields = [
            "user",
            "first_name",
            "last_name",
            "preferred_name",
            "email",
            "phone",
            "birth_date",
            "school",
            "graduation_year",
            "bio",
            "photo",
            "website_url",
            "instagram_url",
            "facebook_url",
            "tiktok_url",
            "youtube_url",
            "public_profile_enabled",
            "active",
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "bio": forms.Textarea(attrs={"rows": 5}),
        }


class OrganizationRoleAssignmentForm(forms.ModelForm):
    class Meta:
        model = OrganizationRoleAssignment
        fields = ["role", "start_date", "end_date", "active", "notes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


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
        fields = [
            "to_person",
            "relationship_type",
            "label",
            "primary_contact",
            "start_date",
            "end_date",
            "active",
            "notes",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class OrganizationGroupForm(forms.ModelForm):
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team is not None:
            # Group.clean() validates parent-group tenant boundaries. Supply the
            # request-derived organization before ModelForm validation.
            self.instance.team = team
        qs = OrganizationGroup.objects.none()
        if team is not None:
            qs = OrganizationGroup.objects.filter(team=team, active=True)
            if getattr(self.instance, "pk", None):
                qs = qs.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = qs.order_by("sort_order", "name")

    class Meta:
        model = OrganizationGroup
        fields = ["name", "group_type", "parent", "description", "active", "sort_order"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class CommitteeForm(forms.ModelForm):
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team is not None:
            # Committee.clean() checks that its optional group belongs to the
            # same organization, so bind that trusted context before validation.
            self.instance.team = team
        self.fields["group"].queryset = (
            OrganizationGroup.objects.filter(team=team, active=True).order_by("sort_order", "name")
            if team is not None
            else OrganizationGroup.objects.none()
        )

    class Meta:
        model = Committee
        fields = ["name", "group", "purpose", "active", "sort_order"]
        widgets = {"purpose": forms.Textarea(attrs={"rows": 3})}


class CommitteeMembershipForm(forms.ModelForm):
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["committee"].queryset = (
            Committee.objects.filter(team=team, active=True)
            .select_related("group")
            .order_by("group__name", "sort_order", "name")
            if team is not None
            else Committee.objects.none()
        )

    class Meta:
        model = CommitteeMembership
        fields = ["committee", "position", "start_date", "end_date", "active", "notes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }
