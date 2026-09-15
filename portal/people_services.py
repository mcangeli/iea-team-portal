"""People-domain services for the v3.2 canonical Person foundation."""

from django.core.exceptions import PermissionDenied

from portal.model_modules.people import Person, PersonRelationship
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

    # Canonical family authorization: an active directional Parent / Guardian
    # relationship grants the parent access to the related person's private
    # People profile. Ended/inactive relationships grant no access.
    return has_active_parent_relationship(viewer, person)


def require_people_manager(user):
    if not can_manage_people(user):
        raise PermissionDenied