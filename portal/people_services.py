"""People-domain services for the v3.2 canonical Person foundation."""

from django.core.exceptions import PermissionDenied
from django.db.models import Q

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
        .prefetch_related(
            "role_assignments",
            "committee_memberships__committee",
            "horse_relationships__horse",
        )
        .order_by("last_name", "first_name", "id")
    )


def person_for_user(user, pk):
    return people_for_user(user).filter(pk=pk).first()


def can_manage_people(user):
    return _can_manage(user)


def _person_for_login(user):
    """Resolve the canonical Person for a login without relying on legacy identity records."""
    if not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.arena_person
    except Person.DoesNotExist:
        return None


def has_active_parent_relationship(parent_person, child_person):
    """Return whether People records an active Parent / Guardian -> child relationship."""
    if not parent_person or not child_person:
        return False
    if parent_person.team_id != child_person.team_id:
        return False
    return PersonRelationship.objects.filter(
        from_person=parent_person,
        to_person=child_person,
        relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        active=True,
        end_date__isnull=True,
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
    """Return legacy Rider ids reached through active canonical People family relationships."""
    viewer = _person_for_login(user)
    if not viewer or viewer.team_id != team.id:
        return []

    child_person_ids = PersonRelationship.objects.filter(
        from_person=viewer,
        to_person__team=team,
        relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        active=True,
        end_date__isnull=True,
    ).values_list("to_person_id", flat=True)

    return list(
        LegacyPersonLink.objects.filter(
            person_id__in=child_person_ids,
            rider__team=team,
            rider__isnull=False,
        ).values_list("rider_id", flat=True)
    )


def personal_riders_for_user(user, team):
    """Resolve a user's riders People-first, retaining legacy family links as a compatibility fallback."""
    canonical_ids = canonical_rider_ids_for_parent(user, team)
    return team.riders.filter(
        Q(id__in=canonical_ids)
        | Q(user=user)
        | Q(guardians=user)
        | Q(guardian_links__guardian__user=user)
    ).distinct()


def can_view_private_rider(user, rider):
    """Authorize rider private data through People first and legacy links second."""
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

    if has_active_parent_relationship(viewer, rider_person):
        return True

    # v3.2 compatibility fallback. These paths can be removed only after legacy
    # GuardianContact/RiderGuardian authorization has been fully retired.
    return (
        rider.guardians.filter(pk=user.pk).exists()
        or rider.guardian_links.filter(guardian__user=user).exists()
    )


def require_people_manager(user):
    if not can_manage_people(user):
        raise PermissionDenied