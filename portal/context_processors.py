from .models import ActionItem, CommitteeAssignment, Season, Team
from .modules import (
    ARENA_MODULES,
    DEFAULT_ENABLED_MODULES,
    enabled_modules_for_organization,
)
from .platform import organization_for_user
from django.conf import settings


PRODUCT_NAME = "ArenaLine"
PRODUCT_TAGLINE = "One team. One season. One place to manage it."


def portal_context(request):
    team = None
    role = None
    can_manage = False
    unread_notifications = 0
    can_finance = False
    assigned_actions = []
    if request.user.is_authenticated:
        can_manage = request.user.is_superuser
        if hasattr(request.user, "profile"):
            team = organization_for_user(request.user)
            role = request.user.profile.role
            can_manage = can_manage or role in {"admin", "coach"}
        season = Season.objects.filter(team=team, is_active=True).first() if team else None
        can_finance = False if role == "rider" else (request.user.is_superuser or role == "admin")
        if role != "rider" and not can_finance and season:
            can_finance = CommitteeAssignment.objects.filter(
                user=request.user, season=season, role=CommitteeAssignment.Role.TREASURER, active=True
            ).exists()
        unread_notifications = request.user.portal_notifications.filter(read_at__isnull=True).count() if hasattr(request.user, "portal_notifications") else 0
        assigned_actions = list(
            ActionItem.objects.filter(
                team=team,
                assigned_to=request.user,
                completed=False,
            ).select_related("show", "rider").order_by("due_at", "-created_at")[:8]
        ) if team else []
    elif request.path.startswith("/accounts/login"):
        team = Team.objects.order_by("pk").first()

    # Preview 3: Team remains the v2.9 persisted tenant, but module availability
    # is now resolved through an organization-neutral platform boundary.
    enabled_modules = enabled_modules_for_organization(team)

    return {
        "portal_team": team,
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
