"""People-domain services for the v3.2 canonical Person foundation."""

from django.core.exceptions import PermissionDenied

from portal.model_modules.people import Person
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


def can_view_private_person(user, person):
    if not getattr(user, "is_authenticated", False):
        return False
    if can_manage_people(user):
        return True
    return bool(person.user_id and person.user_id == user.id)


def require_people_manager(user):
    if not can_manage_people(user):
        raise PermissionDenied