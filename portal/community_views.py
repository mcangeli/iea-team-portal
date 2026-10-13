"""First Community feed and authoring preview."""
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .community_services import visible_community_posts
from .model_modules.people import Person, OrganizationGroup
from .models import CommunityPost, CommunityPostAudience
from .platform import organization_for_user


class CommunityPostForm(forms.ModelForm):
    publish = forms.BooleanField(required=False, label="Publish now")


    audience_scope = forms.ChoiceField(label="Audience", choices=CommunityPostAudience.Scope.choices, initial="organization")
    audience_people = forms.ModelMultipleChoiceField(label="People", queryset=Person.objects.none(), required=False)
    audience_groups = forms.ModelMultipleChoiceField(label="Groups", queryset=OrganizationGroup.objects.none(), required=False)

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields["audience_people"].queryset = Person.objects.filter(team=organization, active=True).order_by("last_name", "first_name")
            self.fields["audience_groups"].queryset = OrganizationGroup.objects.filter(team=organization, active=True).order_by("name")

    def clean(self):
        data = super().clean()
        scope = data.get("audience_scope")
        people = data.get("audience_people")
        groups = data.get("audience_groups")
        if scope == "person" and not people:
            self.add_error("audience_people", "Select at least one person.")
        if scope == "group" and not groups:
            self.add_error("audience_groups", "Select at least one group.")
        if scope != "person" and people:
            self.add_error("audience_people", "People are only allowed for a people audience.")
        if scope != "group" and groups:
            self.add_error("audience_groups", "Groups are only allowed for a group audience.")
        return data

    class Meta:
        model = CommunityPost
        fields = ("title", "body")
        widgets = {"body": forms.Textarea(attrs={"rows": 7})}


def _identity(request):
    organization = organization_for_user(request.user, required=True)
    person = Person.objects.filter(team=organization, user=request.user, active=True).first()
    if person is None:
        raise PermissionDenied("An active Person profile is required for Community.")
    return organization, person


@login_required
def community_feed(request):
    organization, person = _identity(request)
    posts = visible_community_posts(organization=organization, person=person).select_related("author")[:100]
    return render(request, "portal/community_feed.html", {"posts": posts})


@login_required
def community_detail(request, pk):
    organization, person = _identity(request)
    post = get_object_or_404(
        visible_community_posts(organization=organization, person=person).select_related("author"),
        pk=pk,
    )
    return render(request, "portal/community_detail.html", {"post": post})


@login_required
@transaction.atomic
def community_create(request):
    organization, person = _identity(request)
    # First preview: authoring restricted to staff; finer organization-specific
    # publishing capabilities will be added before general availability.
    if not request.user.is_staff:
        raise PermissionDenied
    form = CommunityPostForm(request.POST or None, organization=organization)
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.team = organization
        post.author = person
        post.created_by = request.user
        if form.cleaned_data["publish"]:
            post.status = CommunityPost.Status.PUBLISHED
            post.published_at = timezone.now()
        post.full_clean()
        post.save()
        scope = form.cleaned_data["audience_scope"]
        if scope == "organization":
            CommunityPostAudience.objects.create(post=post, scope=scope)
        elif scope == "person":
            for recipient in form.cleaned_data["audience_people"]:
                CommunityPostAudience.objects.create(post=post, scope=scope, person=recipient)
        else:
            for group in form.cleaned_data["audience_groups"]:
                CommunityPostAudience.objects.create(post=post, scope=scope, group=group)
        return redirect("community_detail", pk=post.pk) if post.status == CommunityPost.Status.PUBLISHED else redirect("community_feed")
    return render(request, "portal/community_editor.html", {"form": form})
