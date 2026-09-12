"""Role-oriented dashboards introduced in v2.0.0 Preview 3."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from ..host_show_models import ShowManagerAssignment
from ..models import (
    ActionItem,
    CommitteeAssignment,
    EventRSVP,
    Lesson,
    SeasonMembership,
    Show,
    ShowAvailability,
    ShowDayRiderStatus,
    ShowEntry,
    ShowPlanningItem,
    UserProfile,
    VolunteerLog,
)
from .common import (
    _active_committee_roles,
    _active_season,
    _can_manage,
    _can_manage_points,
    _is_admin,
    _is_show_lead,
    _qualification_rows,
    _team,
    _team_scoring_rows,
    _visible_action_items,
    _visible_riders,
    _volunteer_progress_rows,
)
from .roster_helpers import _visible_announcements


def _workspace_links(user, team, season):
    """Return only dashboards the current user is explicitly authorized to open.

    Administrators may review every operational workspace. Coaches receive the
    Coach workspace by role, and additional workspaces only when they hold the
    corresponding committee/show assignment.
    """
    links = []
    profile_role = getattr(getattr(user, "profile", None), "role", None)
    roles = _active_committee_roles(user, season)
    admin = _is_admin(user)

    if admin:
        links.append({"label": "Team overview", "url": reverse("dashboard_general")})

    if admin or profile_role == UserProfile.Role.COACH:
        links.append({"label": "Coach", "url": reverse("dashboard_coach")})

    parent_roles = {
        CommitteeAssignment.Role.FUTURES_PARENT,
        CommitteeAssignment.Role.UPPER_PARENT,
    }
    if admin or roles.intersection(parent_roles):
        links.append({"label": "Team Parent", "url": reverse("dashboard_team_parent")})

    if admin or CommitteeAssignment.Role.POINTS_SECRETARY in roles:
        links.append({"label": "Points Secretary", "url": reverse("dashboard_secretary")})

    has_lead_assignment = False
    if season:
        has_lead_assignment = season.shows.filter(
            lead_assignments__user=user,
            lead_assignments__active=True,
        ).exists()
    if admin or has_lead_assignment:
        links.append({"label": "Show Lead", "url": reverse("dashboard_show_lead")})

    has_manager_assignment = bool(
        team
        and ShowManagerAssignment.objects.filter(
            show__team=team,
            user=user,
            active=True,
        ).exists()
    )
    if admin or has_manager_assignment:
        if has_manager_assignment and not links:
            links.append({"label": "Team overview", "url": reverse("dashboard_general")})
        show_manager_url = reverse("dashboard_show_manager")
        if not any(link.get("url") == show_manager_url for link in links):
            links.append({"label": "Show Manager", "url": show_manager_url})

    return links


def _dashboard_shell(user, team, season, role_key, role_label, role_subtitle):
    now = timezone.now()
    today = timezone.localdate()
    return {
        "dashboard_role": role_key,
        "dashboard_role_label": role_label,
        "dashboard_role_subtitle": role_subtitle,
        "season": season,
        "announcements": _visible_announcements(user, team)[:4],
        "events": team.events.filter(starts_at__gte=now).order_by("starts_at")[:5],
        "shows": (
            season.shows.filter(show_date__gte=today).order_by("show_date", "name")[:5]
            if season else Show.objects.none()
        ),
        "workspace_links": _workspace_links(user, team, season),
    }


def _general_context(request, team, season):
    now = timezone.now()
    today = timezone.localdate()
    announcements = _visible_announcements(request.user, team)[:5]
    events = team.events.filter(starts_at__gte=now)[:6]
    riders = _visible_riders(request.user, team).filter(active=True)
    shows = team.shows.filter(show_date__gte=today).order_by("show_date")[:4]
    memberships = season.memberships.select_related("rider") if season else SeasonMembership.objects.none()
    upcoming_lessons = Lesson.objects.none()
    volunteer_due = 0
    pending_volunteer = 0
    pending_availability = 0

    if season:
        upcoming_lessons = season.lessons.filter(
            starts_at__gte=now, cancelled=False
        ).order_by("starts_at")
        if not _can_manage(request.user):
            upcoming_lessons = upcoming_lessons.filter(
                attendance__rider__in=riders
            ).distinct()

        progress = _volunteer_progress_rows(season, riders)
        volunteer_due = sum(1 for row in progress if not row["complete"])
        pending_volunteer = VolunteerLog.objects.filter(
            season=season,
            rider__in=riders,
            status=VolunteerLog.Status.PENDING,
        ).count()

        upcoming_shows_qs = season.shows.filter(show_date__gte=today)
        for show in upcoming_shows_qs:
            for rider in riders:
                ShowAvailability.objects.get_or_create(show=show, rider=rider)

        pending_availability = ShowAvailability.objects.filter(
            show__in=upcoming_shows_qs,
            rider__in=riders,
            status=ShowAvailability.Status.PENDING,
        ).count()

    action_items = _visible_action_items(request.user, team).filter(completed=False)
    my_action_items = action_items.filter(
        Q(assigned_to=request.user)
        | Q(claimed_by=request.user)
        | Q(rider__in=riders)
    ).distinct().order_by("due_at", "-created_at")[:6]

    rsvp_events = list(
        team.events.filter(
            starts_at__gte=now,
            rsvp_requested=True,
            visible_to_all=True,
        )
    )
    rider_list = list(riders)
    responded_pairs = set(
        EventRSVP.objects.filter(
            event__in=rsvp_events,
            rider__in=rider_list,
        ).exclude(status=EventRSVP.Status.PENDING).values_list("event_id", "rider_id")
    )
    pending_event_rsvps = sum(
        1
        for event in rsvp_events
        for rider in rider_list
        if (event.pk, rider.pk) not in responded_pairs
    )

    unclaimed_actions = 0
    overdue_actions = 0
    if _can_manage(request.user):
        unclaimed_actions = action_items.filter(
            claimable=True,
            claimed_by__isnull=True,
            assigned_to__isnull=True,
        ).count()
        overdue_actions = action_items.filter(
            due_at__lt=now,
            completed=False,
        ).count()

    next_show = shows.first() if shows else None
    qualifier_count = 0
    if season:
        qualifier_count = sum(
            1
            for row in _qualification_rows(season)
            if row["qualified"] and row["rider"] in riders
        )

    return {
        "season": season,
        "announcements": announcements,
        "events": events,
        "riders": riders,
        "shows": shows,
        "can_manage": _can_manage(request.user),
        "futures_count": memberships.filter(
            team_level=SeasonMembership.TeamLevel.FUTURES
        ).count(),
        "upper_count": memberships.filter(
            team_level=SeasonMembership.TeamLevel.UPPER
        ).count(),
        "upcoming_lessons": upcoming_lessons[:4],
        "lesson_count": upcoming_lessons.count(),
        "volunteer_due": volunteer_due,
        "pending_volunteer": pending_volunteer,
        "pending_availability": pending_availability,
        "my_action_items": my_action_items,
        "pending_event_rsvps": pending_event_rsvps,
        "unclaimed_actions": unclaimed_actions,
        "overdue_actions": overdue_actions,
        "next_show": next_show,
        "roster_count": memberships.count() if season else riders.count(),
        "qualifier_count": qualifier_count,
        "attention_count": pending_availability + pending_event_rsvps + len(my_action_items),
        "workspace_links": _workspace_links(request.user, team, season),
    }


def _preferred_dashboard(user, team, season):
    """Choose a useful landing workspace while preserving explicit role links."""
    profile_role = getattr(getattr(user, "profile", None), "role", None)
    if profile_role == UserProfile.Role.COACH:
        return "coach"

    if season and season.shows.filter(
        lead_assignments__user=user,
        lead_assignments__active=True,
        show_date__gte=timezone.localdate(),
    ).exists():
        return "show_lead"

    roles = _active_committee_roles(user, season)
    if CommitteeAssignment.Role.POINTS_SECRETARY in roles:
        return "secretary"
    if roles.intersection({
        CommitteeAssignment.Role.FUTURES_PARENT,
        CommitteeAssignment.Role.UPPER_PARENT,
    }):
        return "team_parent"
    return "general"


def _course_summary(show):
    if not show:
        return {"course_count": 0, "course_media_count": 0, "course_walk_count": 0, "course_status": "No upcoming show"}
    courses = list(show.courses.filter(active=True))
    media_count = sum(1 for course in courses if course.course_file or course.external_link)
    walk_count = sum(1 for course in courses if course.course_walk_at)
    if not courses:
        status = "Course information pending"
    elif media_count:
        status = "Course posted"
    else:
        status = "Course details added · media pending"
    return {
        "course_count": len(courses),
        "course_media_count": media_count,
        "course_walk_count": walk_count,
        "course_status": status,
    }


def _render_coach(request, team, season):
    if not _can_manage(request.user):
        raise PermissionDenied

    context = _dashboard_shell(
        request.user,
        team,
        season,
        "coach",
        "Coach Dashboard",
        "Season readiness, rider progress, and team items that need a decision.",
    )
    today = timezone.localdate()
    now = timezone.now()
    next_show = None

    if season:
        next_show = season.shows.filter(show_date__gte=today).order_by("show_date", "name").first()
        active_riders = season.memberships.filter(rider__active=True).values_list("rider_id", flat=True)
        qualification = _qualification_rows(season)
        context.update({
            "roster_count": season.memberships.filter(rider__active=True).count(),
            "pending_availability": ShowAvailability.objects.filter(
                show__season=season,
                show__show_date__gte=today,
                rider_id__in=active_riders,
                status=ShowAvailability.Status.PENDING,
            ).count(),
            "pending_volunteer": VolunteerLog.objects.filter(
                season=season,
                status=VolunteerLog.Status.PENDING,
            ).count(),
            "overdue_actions": _visible_action_items(request.user, team).filter(
                completed=False,
                due_at__lt=now,
            ).count(),
            "unclaimed_actions": _visible_action_items(request.user, team).filter(
                completed=False,
                claimable=True,
                claimed_by__isnull=True,
                assigned_to__isnull=True,
            ).count(),
            "qualified_count": sum(1 for row in qualification if row["qualified"]),
            "near_qualification": sorted(
                [
                    row for row in qualification
                    if not row["qualified"] and row["points"] > 0
                ],
                key=lambda row: (row["threshold"] - row["points"], row["rider"].last_name),
            )[:8],
            "upcoming_lessons": season.lessons.filter(
                starts_at__gte=now,
                cancelled=False,
            ).select_related("group").order_by("starts_at")[:5],
            "course_show": next_show,
            **_course_summary(next_show),
        })
    else:
        context.update({
            "roster_count": 0,
            "pending_availability": 0,
            "pending_volunteer": 0,
            "overdue_actions": 0,
            "unclaimed_actions": 0,
            "qualified_count": 0,
            "near_qualification": [],
            "upcoming_lessons": Lesson.objects.none(),
            "course_show": None,
            **_course_summary(None),
        })
    return render(request, "portal/dashboard_role.html", context)


def _team_parent_levels(user, season):
    roles = _active_committee_roles(user, season)
    levels = []
    if CommitteeAssignment.Role.FUTURES_PARENT in roles:
        levels.append(SeasonMembership.TeamLevel.FUTURES)
    if CommitteeAssignment.Role.UPPER_PARENT in roles:
        levels.append(SeasonMembership.TeamLevel.UPPER)
    return levels


def _render_team_parent(request, team, season):
    if not season:
        if not _is_admin(request.user):
            raise PermissionDenied
        levels = []
    elif _is_admin(request.user):
        levels = [
            SeasonMembership.TeamLevel.FUTURES,
            SeasonMembership.TeamLevel.UPPER,
        ]
    else:
        levels = _team_parent_levels(request.user, season)
        if not levels:
            raise PermissionDenied

    labels = dict(SeasonMembership.TeamLevel.choices)
    scope_label = " + ".join(labels[level] for level in levels) if levels else "Team"
    context = _dashboard_shell(
        request.user,
        team,
        season,
        "team_parent",
        "Team Parent Dashboard",
        f"{scope_label} coordination, volunteers, and show-day readiness.",
    )
    today = timezone.localdate()

    if season:
        rider_qs = season.memberships.filter(
            team_level__in=levels,
            rider__active=True,
        ).select_related("rider")
        rider_ids = list(rider_qs.values_list("rider_id", flat=True))
        progress = _volunteer_progress_rows(
            season,
            team.riders.filter(pk__in=rider_ids),
        )
        upcoming_shows = list(
            season.shows.filter(show_date__gte=today).order_by("show_date")[:5]
        )
        planning_levels = list(levels)
        planning_levels.append(ShowPlanningItem.TeamLevel.ALL)
        context.update({
            "scope_label": scope_label,
            "scope_levels": levels,
            "roster_count": len(rider_ids),
            "volunteer_due": sum(1 for row in progress if not row["complete"]),
            "pending_availability": ShowAvailability.objects.filter(
                show__in=upcoming_shows,
                rider_id__in=rider_ids,
                status=ShowAvailability.Status.PENDING,
            ).count(),
            "planning_items": ShowPlanningItem.objects.filter(
                show__in=upcoming_shows,
                team_level__in=planning_levels,
                family_visible=True,
                completed=False,
            ).select_related("show", "assigned_to", "claimed_by").order_by(
                "show__show_date", "sort_order", "title"
            )[:10],
        })
    else:
        context.update({
            "scope_label": scope_label,
            "scope_levels": levels,
            "roster_count": 0,
            "volunteer_due": 0,
            "pending_availability": 0,
            "planning_items": ShowPlanningItem.objects.none(),
        })
    return render(request, "portal/dashboard_role.html", context)


def _show_lead_queryset(user, season):
    if not season:
        return Show.objects.none()
    qs = season.shows.filter(show_date__gte=timezone.localdate())
    if not _is_admin(user):
        qs = qs.filter(lead_assignments__user=user, lead_assignments__active=True)
    return qs.distinct().order_by("show_date", "name")


def _render_show_lead(request, team, season):
    lead_shows = _show_lead_queryset(request.user, season)
    if not _is_admin(request.user):
        any_assignment = bool(
            season and season.shows.filter(
                lead_assignments__user=request.user,
                lead_assignments__active=True,
            ).exists()
        )
        if not any_assignment:
            raise PermissionDenied

    context = _dashboard_shell(
        request.user,
        team,
        season,
        "show_lead",
        "Show Lead Dashboard",
        "A mobile-first view of show readiness, rider arrival, volunteers, and open tasks.",
    )
    lead_shows = list(lead_shows[:6])
    next_show = lead_shows[0] if lead_shows else None
    open_planning = ShowPlanningItem.objects.none()
    status_counts = {}
    if next_show:
        open_planning = next_show.planning_items.filter(completed=False).select_related(
            "assigned_to", "claimed_by"
        ).order_by("sort_order", "title")
        status_counts = {
            row["status"]: row["total"]
            for row in next_show.rider_statuses.values("status").annotate(total=Count("id"))
        }

    context.update({
        "lead_shows": lead_shows,
        "next_show": next_show,
        "open_planning": open_planning[:12],
        "open_planning_count": open_planning.count() if next_show else 0,
        "status_counts": status_counts,
        "arrived_count": status_counts.get(ShowDayRiderStatus.Status.ARRIVED, 0),
        "late_count": status_counts.get(ShowDayRiderStatus.Status.RUNNING_LATE, 0),
        "scratched_count": status_counts.get(ShowDayRiderStatus.Status.SCRATCHED, 0),
        "course_show": next_show,
        **_course_summary(next_show),
    })
    return render(request, "portal/dashboard_role.html", context)


def _render_secretary(request, team, season):
    roles = _active_committee_roles(request.user, season)
    if not (_is_admin(request.user) or CommitteeAssignment.Role.POINTS_SECRETARY in roles):
        raise PermissionDenied

    context = _dashboard_shell(
        request.user,
        team,
        season,
        "secretary",
        "Secretary / Points Dashboard",
        "Result completion, qualification progress, and scoring records that need review.",
    )
    today = timezone.localdate()

    if season:
        qualification = _qualification_rows(season)
        _, team_summary = _team_scoring_rows(season, include_riders=False)
        missing_results = ShowEntry.objects.filter(
            show_class__show__season=season,
            show_class__show__show_date__lte=today,
            result__isnull=True,
        ).exclude(status=ShowEntry.Status.SCRATCHED).select_related(
            "rider", "show_class__show", "show_class"
        ).order_by("-show_class__show__show_date", "rider__last_name")

        context.update({
            "qualification_rows": sorted(
                qualification,
                key=lambda row: (
                    not row["qualified"],
                    row["threshold"] - row["points"],
                    row["rider"].last_name,
                    row["season_class"].name,
                ),
            )[:12],
            "qualified_count": sum(1 for row in qualification if row["qualified"]),
            "qualification_total": len(qualification),
            "missing_results": missing_results[:10],
            "missing_results_count": missing_results.count(),
            "team_summary": team_summary,
            "completed_show_count": season.shows.filter(
                status=Show.Status.COMPLETE
            ).count(),
        })
    else:
        context.update({
            "qualification_rows": [],
            "qualified_count": 0,
            "qualification_total": 0,
            "missing_results": ShowEntry.objects.none(),
            "missing_results_count": 0,
            "team_summary": [],
            "completed_show_count": 0,
        })

    return render(request, "portal/dashboard_role.html", context)


@login_required
def dashboard(request):
    team = _team(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    season = _active_season(team)

    preferred = _preferred_dashboard(request.user, team, season)
    if preferred == "coach":
        return _render_coach(request, team, season)
    if preferred == "show_lead":
        return _render_show_lead(request, team, season)
    if preferred == "secretary":
        return _render_secretary(request, team, season)
    if preferred == "team_parent":
        return _render_team_parent(request, team, season)

    context = _general_context(request, team, season)
    return render(request, "portal/dashboard.html", context)


@login_required
def dashboard_general(request):
    team = _team(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    season = _active_season(team)
    return render(request, "portal/dashboard.html", _general_context(request, team, season))


@login_required
def dashboard_coach(request):
    team = _team(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    return _render_coach(request, team, _active_season(team))


@login_required
def dashboard_team_parent(request):
    team = _team(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    return _render_team_parent(request, team, _active_season(team))


@login_required
def dashboard_show_lead(request):
    team = _team(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    return _render_show_lead(request, team, _active_season(team))


@login_required
def dashboard_secretary(request):
    team = _team(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    return _render_secretary(request, team, _active_season(team))
