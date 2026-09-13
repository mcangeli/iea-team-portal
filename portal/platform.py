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


def default_organization():
    """Return the legacy default tenant used by unauthenticated branded surfaces.

    The current application historically uses the first Team row to brand the
    login screen. Keeping that lookup here prevents generic shell code from
    depending directly on the persisted tenant model while preserving behavior.
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
