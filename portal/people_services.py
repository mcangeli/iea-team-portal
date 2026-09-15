"""People-domain services for the v3.2 canonical Person foundation."""

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from portal.model_modules.people import LegacyPersonLink, Person, PersonRelationship
from portal.view_modules.common import _can_manage, _team


def people_for_user(user):
    """Return canonical people in the caller's organization."""
    team = _team(user)
    if not team:
        return Person.objects.none()
    return (
        Person.objects.filter(team=team, active=True)
        .select_related("user")
        .prefetch_related("role_assignments", "committee_memberships__committee", "horse_relationships__horse")
        .order_by("last_name", "first_name", "id")
    )


def person_for_user(user, pk):
    return people_for_user(user).filter(pk=pk).first()


def can_manage_people(user):
    return _can_manage(user)


def _person_for_login(user):
    if not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.arena_person
    except Person.DoesNotExist:
        return None


def _active_parent_relationships():
    """Return parent/guardian relationships currently effective for access."""
    today = timezone.localdate()
    return PersonRelationship.objects.filter(
        relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        active=True,
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today),
        Q(end_date__isnull=True) | Q(end_date__gt=today),
    )


def has_active_parent_relationship(parent_person, child_person):
    if not parent_person or not child_person or parent_person.team_id != child_person.team_id:
        return False
    return _active_parent_relationships().filter(
        from_person=parent_person,
        to_person=child_person,
    ).exists()


def can_view_private_person(user, person):
    if not getattr(user, "is_authenticated", False):
        return False
    if can_manage_people(user):
        return True
    viewer = _person_for_login(user)
    if viewer and viewer.pk == person.pk:
        return True
    return has_active_parent_relationship(viewer, person)


def canonical_rider_ids_for_parent(user, team):
    viewer = _person_for_login(user)
    if not viewer or viewer.team_id != team.id:
        return []
    child_person_ids = _active_parent_relationships().filter(
        from_person=viewer,
        to_person__team=team,
    ).values_list("to_person_id", flat=True)
    return list(
        LegacyPersonLink.objects.filter(
            person_id__in=child_person_ids,
            rider__team=team,
            rider__isnull=False,
        ).values_list("rider_id", flat=True)
    )


def canonical_self_rider_ids_for_user(user, team):
    """Return Rider ids bridged to the login's canonical Person."""
    viewer = _person_for_login(user)
    if not viewer or viewer.team_id != team.id:
        return []
    return list(
        LegacyPersonLink.objects.filter(
            person=viewer,
            rider__team=team,
            rider__isnull=False,
        ).values_list("rider_id", flat=True)
    )


def personal_riders_for_user(user, team):
    parent_ids = canonical_rider_ids_for_parent(user, team)
    self_ids = canonical_self_rider_ids_for_user(user, team)
    return team.riders.filter(
        Q(id__in=parent_ids)
        | Q(id__in=self_ids)
        | Q(user=user)
        | Q(guardians=user)
        | Q(guardian_links__guardian__user=user)
    ).distinct()


def visible_riders_for_user(user, team):
    qs = team.riders.all()
    profile = getattr(user, "profile", None)
    if profile and profile.role == profile.Role.PARENT:
        return personal_riders_for_user(user, team)
    if profile and profile.role == profile.Role.RIDER:
        return qs.filter(Q(id__in=canonical_self_rider_ids_for_user(user, team)) | Q(user=user)).distinct()
    return qs


def can_view_private_rider(user, rider):
    if not getattr(user, "is_authenticated", False):
        return False
    if _can_manage(user):
        return True
    if rider.user_id == user.id:
        return True
    viewer = _person_for_login(user)
    try:
        rider_person = rider.person_bridge.person
    except LegacyPersonLink.DoesNotExist:
        rider_person = None
    if viewer and rider_person and viewer.pk == rider_person.pk:
        return True
    if has_active_parent_relationship(viewer, rider_person):
        return True
    return rider.guardians.filter(pk=user.pk).exists() or rider.guardian_links.filter(guardian__user=user).exists()


def can_view_family_account(user, membership):
    """Restrict family finance to finance users and actual family relationships."""
    from portal.view_modules.common import _can_finance, _is_rider_account

    if _is_rider_account(user):
        return False
    if _can_finance(user, membership.season):
        return True
    rider = membership.rider
    viewer = _person_for_login(user)
    try:
        rider_person = rider.person_bridge.person
    except LegacyPersonLink.DoesNotExist:
        rider_person = None
    if has_active_parent_relationship(viewer, rider_person):
        return True
    return rider.guardians.filter(pk=user.pk).exists() or rider.guardian_links.filter(guardian__user=user).exists()


def require_people_manager(user):
    if not can_manage_people(user):
        raise PermissionDenied
