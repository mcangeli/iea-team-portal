"""First Community feed and authoring preview."""
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .community_services import visible_community_posts
from .model_modules.people import Person
from .models import CommunityPost, CommunityPostAudience
from .platform import organization_for_user


class CommunityPostForm(forms.ModelForm):
    publish = forms.BooleanField(required=False, label="Publish now")

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
    form = CommunityPostForm(request.POST or None)
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
        CommunityPostAudience.objects.create(
            post=post, scope=CommunityPostAudience.Scope.ORGANIZATION
        )
        return redirect("community_detail", pk=post.pk) if post.status == CommunityPost.Status.PUBLISHED else redirect("community_feed")
    return render(request, "portal/form.html", {"form": form, "title": "Create community post", "eyebrow": "COMMUNITY"})
