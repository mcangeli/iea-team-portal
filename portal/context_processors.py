from .models import ActionItem, CommitteeAssignment, Season, Team
from django.conf import settings


PRODUCT_NAME = "ArenaLine"
PRODUCT_TAGLINE = "One team. One season. One place to manage it."

# Preview 2C: stable product-domain identifiers. These are intentionally
# presentation/application metadata only; Team remains the current tenant model.
ARENA_MODULES = {
    "core": {"label": "Core", "scope": "platform"},
    "people": {"label": "People & Families", "scope": "platform"},
    "horses": {"label": "Horses", "scope": "platform"},
    "competition_iea": {"label": "IEA Competition", "scope": "competition"},
    "operations": {"label": "Operations", "scope": "platform"},
    "finance": {"label": "Finance", "scope": "platform"},
    "communications": {"label": "Communications", "scope": "platform"},
}
DEFAULT_ENABLED_MODULES = tuple(ARENA_MODULES.keys())


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
            team = request.user.profile.team
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
    return {
        "portal_team": team,
        "portal_role": role,
        "portal_can_manage": can_manage,
        "portal_can_finance": can_finance,
        "product_name": PRODUCT_NAME,
        "product_tagline": PRODUCT_TAGLINE,
        "portal_modules": ARENA_MODULES,
        "portal_enabled_modules": DEFAULT_ENABLED_MODULES,
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
