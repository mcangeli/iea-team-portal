from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from .model_modules.barn_participation import HorsePersonRelationship
from .model_modules.capabilities import OrganizationCapabilityAssignment
from .models import UserProfile


def _legacy_horse_manager(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and (
            user.is_superuser
            or (
                hasattr(user, "profile")
                and user.profile.role in {UserProfile.Role.ADMIN, UserProfile.Role.COACH}
            )
        )
    )


def _current(queryset, *, today=None):
    today = today or timezone.localdate()
    return queryset.filter(active=True).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today),
        Q(end_date__isnull=True) | Q(end_date__gt=today),
    )


def can_manage_horses(user):
    """Organization-wide horse management from legacy manager access or explicit capability."""
    if _legacy_horse_manager(user):
        return True
    if not getattr(user, "is_authenticated", False):
        return False
    try:
        person = user.arena_person
    except AttributeError:
        return False
    return _current(
        OrganizationCapabilityAssignment.objects.filter(
            team=person.team,
            person=person,
            capability=OrganizationCapabilityAssignment.Capability.MANAGE_HORSES,
        )
    ).exists()


def can_manage_horse(user, horse):
    """Horse-scoped management, including a current Boarder / Responsible Party relationship."""
    if can_manage_horses(user):
        return True
    if not getattr(user, "is_authenticated", False):
        return False
    try:
        person = user.arena_person
    except AttributeError:
        return False
    if person.team_id != horse.team_id:
        return False
    return _current(
        HorsePersonRelationship.objects.filter(
            team=horse.team,
            horse=horse,
            person=person,
            relationship_type=HorsePersonRelationship.RelationshipType.BOARDER,
        )
    ).exists()


def require_horse_management(user, horse=None, *, organization_wide=False):
    allowed = can_manage_horses(user) if organization_wide or horse is None else can_manage_horse(user, horse)
    if not allowed:
        raise PermissionDenied
