"""ArenaLine platform context helpers.

The persisted tenant is still ``Team`` in v2.9. Callers in generic platform code
should resolve that tenant through organization-oriented helpers so a later
Organization/Program migration has a defined seam instead of requiring another
cross-application terminology refactor.
"""

from django.core.exceptions import PermissionDenied


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
