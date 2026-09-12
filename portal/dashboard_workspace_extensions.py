"""v2.5 dashboard workspace integration for Show Manager assignments.

The role-dashboard selector predates the v2.5 Show Manager assignment model. Keep
this compatibility bridge small and isolated until the dashboard modules are
normalized in the planned v2.9 cleanup.
"""

from django.urls import reverse

from .host_show_models import ShowManagerAssignment
from .view_modules import dashboards
from .view_modules.common import _is_admin


_base_workspace_links = dashboards._workspace_links


def _workspace_links_with_show_manager(user, team, season):
    links = list(_base_workspace_links(user, team, season))

    has_manager_assignment = bool(
        team
        and ShowManagerAssignment.objects.filter(
            show__team=team,
            user=user,
            active=True,
        ).exists()
    )

    if not (_is_admin(user) or has_manager_assignment):
        return links

    # A Show Manager who has no other role dashboard still needs a two-way
    # workspace switcher: Team overview <-> Show Manager. The dashboard
    # templates intentionally hide the selector when fewer than two links are
    # available.
    if has_manager_assignment and not links:
        links.append({"label": "Team overview", "url": reverse("dashboard_general")})

    show_manager_url = reverse("dashboard_show_manager")
    if not any(link.get("url") == show_manager_url for link in links):
        links.append({"label": "Show Manager", "url": show_manager_url})

    return links


dashboards._workspace_links = _workspace_links_with_show_manager
