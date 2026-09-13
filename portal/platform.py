"""ArenaLine platform context helpers.

The persisted tenant is still ``Team`` in v2.9. Callers in generic platform code
should resolve tenant, role, and operating-period context through these helpers so
a later Organization/Program migration has a defined seam instead of requiring
another cross-application refactor.
"""

from django.core.exceptions import PermissionDenied

from .models import Season, Team, UserProfile


_UNASSIGNED_MESSAGE = "Your account is not assigned to a team."


def organization_for_user(user, *, required: bool = False):
    """Return the current persisted organization context for a user.

    In v2.9 this returns ``user.profile.team``. The return type is intentionally
    not renamed or wrapped; the helper is an application boundary, not a schema
    migration. ``required=True`` preserves the existing operational permission
    behavior and legacy error message used by authenticated views.
    """

    organization = user.profile.team if hasattr(user, "profile") else None
    if required and organization is None:
        raise PermissionDenied(_UNASSIGNED_MESSAGE)
    return organization


def organization_for_view_user(user):
    """Resolve organization context with legacy authenticated-view semantics.

    Existing generic views historically allowed an unassigned superuser to pass
    through tenant resolution while requiring ordinary accounts to be assigned
    to a Team. Preview 3 keeps that behavior intact behind a named platform seam.
    """

    return organization_for_user(
        user,
        required=not getattr(user, "is_superuser", False),
    )


def default_organization():
    """Return the legacy default tenant when an explicit compatibility caller needs it.

    Generic unauthenticated ArenaLine surfaces no longer use this fallback for
    branding. It remains available only for legacy callers that explicitly need
    the first persisted Team during the v2.9 transition.
    """

    return Team.objects.order_by("pk").first()


def active_period_for_organization(organization):
    """Return the active operating period for an organization.

    ``Season`` remains the persisted name in v2.9. Generic platform callers use
    an operating-period boundary so a future organization model does not require
    changing every shell/service lookup at once.
    """

    if organization is None:
        return None
    return Season.objects.filter(team=organization, is_active=True).first()


def role_for_user(user):
    """Return the user's organization role, if the account has a profile."""

    return user.profile.role if hasattr(user, "profile") else None


def can_manage_organization(user) -> bool:
    """Return whether the user has current organization-management authority."""

    role = role_for_user(user)
    return bool(
        getattr(user, "is_superuser", False)
        or role in {UserProfile.Role.ADMIN, UserProfile.Role.COACH}
    )
