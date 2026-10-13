"""Private, request-time community audience resolution."""
from django.db.models import Q, Case, When, Value, IntegerField
from django.utils import timezone

from .models import CommunityPost, CommunityPostAudience
from .model_modules.people import OrganizationGroupMembership


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
    if user is not None and user.is_authenticated and (user.is_staff or user.is_superuser):
        return posts.order_by("-notice_rank", "-published_at", "-pk")
    return posts.filter(
        Q(audiences__scope=CommunityPostAudience.Scope.ORGANIZATION)
        | Q(audiences__scope=CommunityPostAudience.Scope.PERSON, audiences__person=person)
        | Q(audiences__scope=CommunityPostAudience.Scope.GROUP, audiences__group_id__in=active_group_ids)
    ).distinct().order_by("-notice_rank", "-published_at", "-pk")
