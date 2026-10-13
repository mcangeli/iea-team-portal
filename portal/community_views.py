"""First Community feed and authoring preview."""
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .community_services import (visible_community_posts, community_permissions, can_manage_community_post, can_archive_community_post)
from .model_modules.people import Person, OrganizationGroup
from .models import CommunityPost, CommunityPostAudience
from .platform import organization_for_user


class CommunityPostForm(forms.ModelForm):
    publish = forms.BooleanField(required=False, label="Publish / schedule")
    publish_at = forms.SplitDateTimeField(required=False, label="Publish at (blank means now)", widget=forms.SplitDateTimeWidget(date_attrs={"type":"date"}, time_attrs={"type":"time"}))
    is_notice = forms.BooleanField(required=False, label="Priority notice")
    notice_until = forms.SplitDateTimeField(required=False, label="Priority until (optional)", widget=forms.SplitDateTimeWidget(date_attrs={"type":"date"}, time_attrs={"type":"time"}))



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
        if data.get("publish_at") and not data.get("publish"):
            self.add_error("publish_at", "Enable publishing to schedule this post.")
        if data.get("notice_until") and not data.get("is_notice"):
            self.add_error("notice_until", "Enable priority notice first.")
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
    posts = list(visible_community_posts(organization=organization, person=person, user=request.user).select_related("author")[:100])
    notices = [post for post in posts if post.notice_rank]
    regular_posts = [post for post in posts if not post.notice_rank]
    can_author, can_publish = community_permissions(request.user, organization)
    return render(request, "portal/community_feed.html", {"notices": notices, "posts": regular_posts, "now": timezone.now(), "can_author": can_author})


@login_required
def community_detail(request, pk):
    organization, person = _identity(request)
    post = get_object_or_404(
        visible_community_posts(organization=organization, person=person, user=request.user).select_related("author"),
        pk=pk,
    )
    return render(request, "portal/community_detail.html", {"post": post})


@login_required
@transaction.atomic
def community_create(request):
    organization, person = _identity(request)
    can_author, can_publish = community_permissions(request.user, organization)
    if not can_author:
        raise PermissionDenied
    form = CommunityPostForm(request.POST or None, organization=organization)
    if not can_publish:
        form.fields["publish"].disabled = True
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.team = organization
        post.author = person
        post.created_by = request.user
        if form.cleaned_data["publish"]:
            post.status = CommunityPost.Status.PUBLISHED
            post.published_at = form.cleaned_data["publish_at"] or timezone.now()
        post.is_notice = form.cleaned_data["is_notice"]
        post.notice_until = form.cleaned_data["notice_until"]
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
        return redirect("community_manage")
    return render(request, "portal/community_editor.html", {"form": form, "editing": False, "can_publish": can_publish})


def _require_editor(request):
    organization, person = _identity(request)
    if not community_permissions(request.user, organization)[0]:
        raise PermissionDenied
    return organization, person


def _audience_initial(post):
    audiences = post.audiences.all()
    first = audiences.first()
    return {
        "audience_scope": first.scope if first else CommunityPostAudience.Scope.ORGANIZATION,
        "audience_people": list(audiences.filter(scope="person").values_list("person_id", flat=True)),
        "audience_groups": list(audiences.filter(scope="group").values_list("group_id", flat=True)),
        "publish": post.status == CommunityPost.Status.PUBLISHED,
        "publish_at": post.published_at,
        "is_notice": post.is_notice,
        "notice_until": post.notice_until,
    }


def _replace_audiences(post, cleaned):
    scope = cleaned["audience_scope"]
    post.audiences.all().delete()
    if scope == "organization":
        CommunityPostAudience.objects.create(post=post, scope=scope)
    elif scope == "person":
        for person in cleaned["audience_people"]:
            CommunityPostAudience.objects.create(post=post, scope=scope, person=person)
    else:
        for group in cleaned["audience_groups"]:
            CommunityPostAudience.objects.create(post=post, scope=scope, group=group)


@login_required
def community_manage(request):
    organization, _ = _require_editor(request)
    can_publish = community_permissions(request.user, organization)[1]
    posts = CommunityPost.objects.filter(team=organization)
    if not can_publish:
        posts = posts.filter(created_by=request.user, status=CommunityPost.Status.DRAFT)
    posts = list(posts.select_related("author").order_by("-created_at", "-pk")[:150])
    now = timezone.now()
    posts.sort(key=lambda post: (not (post.status == CommunityPost.Status.PUBLISHED and post.published_at and post.published_at <= now and post.is_notice and (post.notice_until is None or post.notice_until > now)), -(post.created_at.timestamp()), -post.pk))
    return render(request, "portal/community_manage.html", {"posts": posts, "now": now, "can_publish": can_publish})


@login_required
@transaction.atomic
def community_edit(request, pk):
    organization, _ = _require_editor(request)
    post = get_object_or_404(CommunityPost, team=organization, pk=pk)
    if not can_manage_community_post(request.user, organization, post):
        raise PermissionDenied
    can_publish = community_permissions(request.user, organization)[1]
    if post.status in (CommunityPost.Status.ARCHIVED, CommunityPost.Status.REMOVED):
        raise PermissionDenied("Archived or removed posts cannot be edited.")
    form = CommunityPostForm(
        request.POST or None, instance=post, organization=organization,
        initial=_audience_initial(post) if request.method != "POST" else None,
    )
    if not can_publish:
        form.fields["publish"].disabled = True
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        publishing = form.cleaned_data["publish"]
        updated.status = CommunityPost.Status.PUBLISHED if publishing else CommunityPost.Status.DRAFT
        if publishing:
            updated.published_at = form.cleaned_data["publish_at"] or updated.published_at or timezone.now()
        if not publishing:
            updated.published_at = None
        updated.is_notice = form.cleaned_data["is_notice"]
        updated.notice_until = form.cleaned_data["notice_until"]
        updated.full_clean()
        updated.save()
        _replace_audiences(updated, form.cleaned_data)
        return redirect("community_manage")
    return render(request, "portal/community_editor.html", {"form": form, "editing": True, "post": post, "can_publish": can_publish})


@login_required
@transaction.atomic
def community_archive(request, pk):
    organization, _ = _require_editor(request)
    post = get_object_or_404(CommunityPost, team=organization, pk=pk)
    if not can_archive_community_post(request.user, organization, post):
        raise PermissionDenied
    if request.method != "POST":
        raise PermissionDenied("Archiving requires confirmation by POST.")
    if post.status not in (CommunityPost.Status.ARCHIVED, CommunityPost.Status.REMOVED):
        post.status = CommunityPost.Status.ARCHIVED
        post.save(update_fields=["status", "updated_at"])
    return redirect("community_manage")
