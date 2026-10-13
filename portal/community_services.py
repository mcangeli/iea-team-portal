"""Private, request-time community audience resolution."""
from django.db.models import Q, Case, When, Value, IntegerField
from django.utils import timezone

from .models import CommunityPost, CommunityPostAudience, UserProfile
from .model_modules.people import OrganizationGroupMembership


def community_permissions(user, organization):
    """Tenant-scoped authoring and publication permissions."""
    if not user.is_authenticated or not organization:
        return False, False
    profile = getattr(user, "profile", None)
    if profile is None or profile.team_id != organization.pk:
        return False, False
    publisher = bool(user.is_superuser or profile.role == UserProfile.Role.ADMIN)
    author = bool(publisher or profile.role == UserProfile.Role.COACH)
    return author, publisher


def can_publish_community(user, organization):
    return community_permissions(user, organization)[1]


def can_author_community(user, organization):
    return community_permissions(user, organization)[0]


def can_manage_community_post(user, organization, post):
    author, publisher = community_permissions(user, organization)
    return bool(author and post.team_id == organization.pk and
                (publisher or (post.created_by_id == user.pk and post.status == CommunityPost.Status.DRAFT)))


def can_archive_community_post(user, organization, post):
    return bool(can_publish_community(user, organization) and post.team_id == organization.pk)


def can_review_community_post(user, organization, post):
    return can_manage_community_post(user, organization, post)


def can_view_all_community_posts(user, organization):
    return can_publish_community(user, organization)


def visible_community_posts(*, organization, person, at=None, user=None):
    """Return published posts visible to a canonical Person in this organization.

    This is a read-scope helper, not publishing or moderation authorization.
    """
    if person is None or not person.active or person.team_id != organization.pk:
        return CommunityPost.objects.none()
    at = at or timezone.now()
    day = timezone.localdate(at)
    active_group_ids = OrganizationGroupMembership.objects.filter(
        team=organization,
        person=person,
        active=True,
        status=OrganizationGroupMembership.Status.ACTIVE,
        group__active=True,
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=day),
        Q(end_date__isnull=True) | Q(end_date__gt=day),
    ).values("group_id")
    posts = CommunityPost.objects.filter(
        team=organization,
        status=CommunityPost.Status.PUBLISHED,
        published_at__isnull=False,
        published_at__lte=at,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=at),
    )
    posts = posts.annotate(notice_rank=Case(When(is_notice=True, notice_until__isnull=True, then=Value(1)), When(is_notice=True, notice_until__gt=at, then=Value(1)), default=Value(0), output_field=IntegerField()))
    if user is not None and user.is_authenticated and can_view_all_community_posts(user, organization):
        return posts.order_by("-notice_rank", "-published_at", "-pk")
    return posts.filter(
        Q(audiences__scope=CommunityPostAudience.Scope.ORGANIZATION)
        | Q(audiences__scope=CommunityPostAudience.Scope.PERSON, audiences__person=person)
        | Q(audiences__scope=CommunityPostAudience.Scope.GROUP, audiences__group_id__in=active_group_ids)
    ).distinct().order_by("-notice_rank", "-published_at", "-pk")
