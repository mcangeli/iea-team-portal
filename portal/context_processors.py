from .models import ActionItem, CommitteeAssignment
from .modules import (
    ARENA_MODULES,
    enabled_modules_for_organization,
)
from .platform import (
    active_period_for_organization,
    can_manage_organization,
    default_organization,
    organization_for_user,
    role_for_user,
)
from django.conf import settings


PRODUCT_NAME = "ArenaLine"
PRODUCT_TAGLINE = "One team. One season. One place to manage it."


def portal_context(request):
    organization = None
    role = None
    can_manage = False
    unread_notifications = 0
    can_finance = False
    assigned_actions = []

    if request.user.is_authenticated:
        organization = organization_for_user(request.user)
        role = role_for_user(request.user)
        can_manage = can_manage_organization(request.user)
        period = active_period_for_organization(organization)

        can_finance = False if role == "rider" else (request.user.is_superuser or role == "admin")
        if role != "rider" and not can_finance and period:
            can_finance = CommitteeAssignment.objects.filter(
                user=request.user,
                season=period,
                role=CommitteeAssignment.Role.TREASURER,
                active=True,
            ).exists()

        unread_notifications = (
            request.user.portal_notifications.filter(read_at__isnull=True).count()
            if hasattr(request.user, "portal_notifications")
            else 0
        )
        assigned_actions = list(
            ActionItem.objects.filter(
                team=organization,
                assigned_to=request.user,
                completed=False,
            )
            .select_related("show", "rider")
            .order_by("due_at", "-created_at")[:8]
        ) if organization else []

    elif request.path.startswith("/accounts/login"):
        organization = default_organization()

    # Preview 3: Team remains the v2.9 persisted tenant, but module availability
    # is resolved through an organization-neutral platform boundary.
    enabled_modules = enabled_modules_for_organization(organization)

    return {
        "portal_organization": organization,
        # Compatibility alias retained through v2.9 for feature templates that
        # still use the persisted Team vocabulary.
        "portal_team": organization,
        "portal_role": role,
        "portal_can_manage": can_manage,
        "portal_can_finance": can_finance,
        "product_name": PRODUCT_NAME,
        "product_tagline": PRODUCT_TAGLINE,
        "portal_modules": ARENA_MODULES,
        "portal_enabled_modules": enabled_modules,
        "portal_organization_label": "Organization",
        "site_version": settings.SITE_VERSION,
        "site_version_docs_url": (
            f"{settings.PORTAL_REPOSITORY_URL}/tree/v{settings.SITE_VERSION}"
            if settings.PORTAL_REPOSITORY_URL and settings.SITE_VERSION != "dev"
            else settings.PORTAL_REPOSITORY_URL
        ),
        "unread_notifications": unread_notifications,
        "portal_assigned_actions": assigned_actions,
    }
