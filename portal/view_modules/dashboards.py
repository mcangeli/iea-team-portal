"""Role-oriented dashboards introduced in v2.0.0 Preview 3."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from ..host_show_models import ShowManagerAssignment
from ..model_modules.lessons import LessonOccurrence
from ..model_modules.people import Person, OrganizationRoleAssignment
from ..model_modules.horses import Horse, HorseCogginsRecord
from ..services.finance_access import allowed_finance_domains
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
from ..platform import active_period_for_organization, organization_for_view_user
from .common import (
    _active_committee_roles,
    _can_manage,
    _can_manage_points,
    _is_admin,
    _is_show_lead,
    _qualification_rows,
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
        links.extend([
            {"label": "Team overview", "url": reverse("dashboard_general")},
            {"label": "Coach", "url": reverse("dashboard_coach")},
            {"label": "Team Parent", "url": reverse("dashboard_team_parent")},
            {"label": "Points Secretary", "url": reverse("dashboard_secretary")},
            {"label": "Show Lead", "url": reverse("dashboard_show_lead")},
            {"label": "Show Manager", "url": reverse("dashboard_show_manager")},
        ])
        return links

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
    # The general ArenaLine home is barn-wide. IEA season/show/volunteer
    # calculations belong to My Team and its role workspaces.

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

    person = Person.objects.filter(team=team, user=request.user, active=True).first()
    active_roles = []
    if person:
        active_roles = list(
            OrganizationRoleAssignment.objects.filter(
                team=team, person=person, active=True
            ).values_list("role", flat=True)
        )

    lesson_occurrences = LessonOccurrence.objects.filter(
        series__program__team=team,
        starts_at__gte=now,
        status=LessonOccurrence.Status.SCHEDULED,
    ).select_related("series__program", "instructor").order_by("starts_at")
    if not _can_manage(request.user):
        if person:
            lesson_occurrences = lesson_occurrences.filter(
                Q(series__enrollments__person=person, series__enrollments__status="active")
                | Q(assignments__person=person, assignments__role="participant")
                | Q(attendance_records__person=person)
            ).distinct()
        else:
            lesson_occurrences = lesson_occurrences.none()

    finance_domains = allowed_finance_domains(request.user, team)
    can_manage_horses = _is_admin(request.user) or bool(
        person and person.capability_assignments.filter(
            team=team, active=True, capability="manage_horses"
        ).exists()
    )

    operational_areas = [
        {"key": "calendar", "label": "Calendar", "url": reverse("calendar"), "summary": "Events, lessons, shows, and barn schedule."},
        {"key": "people", "label": "People", "url": reverse("people_directory"), "summary": "People, relationships, roles, and access."},
    ]

    quick_actions = [
        {"key": "calendar", "label": "Open calendar", "url": reverse("calendar"), "hint": "See the full program schedule."},
        {"key": "actions", "label": "Action items", "url": reverse("action_item_list"), "hint": "Review work that needs follow-up."},
    ]
    if _can_manage(request.user):
        quick_actions.append({"key": "people", "label": "Add person", "url": reverse("person_create"), "hint": "Add a rider, family member, staff member, or volunteer."})
    if lesson_occurrences.exists() or _can_manage(request.user) or any(role in active_roles for role in ("trainer", "assistant_trainer")):
        operational_areas.append({"key": "lessons", "label": "Lessons", "url": reverse("lesson_program_list"), "summary": "Barn programs, series, occurrences, and attendance."})
        quick_actions.append({"key": "lessons", "label": "Lesson programs", "url": reverse("lesson_program_list"), "hint": "Plan series, occurrences, attendance, and assignments."})
    if can_manage_horses:
        operational_areas.append({"key": "horses", "label": "Horses", "url": reverse("horse_list"), "summary": "Registry, care, compliance, and horse operations."})
        quick_actions.append({"key": "horses", "label": "Horse registry", "url": reverse("horse_list"), "hint": "Review horses, care, compliance, and relationships."})
    if finance_domains:
        finance_url = reverse("finance_workspace") if "general" in finance_domains else reverse("finance_dashboard")
        operational_areas.append({"key": "finance", "label": "Finance", "url": finance_url, "summary": "Receivables, reconciliation, exports, and reporting."})
        quick_actions.append({"key": "finance", "label": "Finance workspace", "url": finance_url, "hint": "Open the finance tools available to your role."})


    domain_snapshots = []
    if can_manage_horses:
        active_horses = Horse.objects.filter(team=team, active=True)
        coggins_attention = sum(
            1 for horse in active_horses.prefetch_related("coggins_records")
            if not horse.current_coggins or horse.current_coggins.status == "expiring"
        )
        domain_snapshots.append({
            "key": "horses", "label": "Horse operations", "value": active_horses.count(),
            "detail": f"{coggins_attention} need Coggins attention" if coggins_attention else "Coggins records look current",
            "url": reverse("horse_list"),
        })
    if lesson_occurrences.exists() or _can_manage(request.user):
        domain_snapshots.append({
            "key": "lessons", "label": "Lesson program", "value": lesson_occurrences[:5].count(),
            "detail": "upcoming scheduled occurrences", "url": reverse("lesson_program_list"),
        })
    if finance_domains:
        domain_snapshots.append({
            "key": "finance", "label": "Finance access", "value": len(finance_domains),
            "detail": "finance domain" + ("" if len(finance_domains) == 1 else "s") + " available",
            "url": finance_url,
        })

    schedule_items = []
    for event in events:
        schedule_items.append({
            "kind": "event",
            "label": event.get_kind_display(),
            "title": event.title,
            "starts_at": event.starts_at,
            "location": event.location,
            "url": reverse("calendar"),
        })
    for occurrence in lesson_occurrences[:5]:
        schedule_items.append({
            "kind": "lesson",
            "label": occurrence.series.program.name,
            "title": occurrence.series.name,
            "starts_at": occurrence.starts_at,
            "location": getattr(occurrence, "location", ""),
            "url": reverse("lesson_occurrence_detail", args=[occurrence.pk]),
        })
    schedule_items.sort(key=lambda item: item["starts_at"])
    schedule_items = schedule_items[:6]

    attention_items = []
    if pending_event_rsvps:
        attention_items.append({"key": "rsvp", "count": pending_event_rsvps, "label": "Event responses waiting", "url": reverse("my_team")})
    if overdue_actions and _can_manage(request.user):
        attention_items.append({"key": "overdue", "count": overdue_actions, "label": "Overdue action items", "url": reverse("action_item_list")})
    if unclaimed_actions and _can_manage(request.user):
        attention_items.append({"key": "unclaimed", "count": unclaimed_actions, "label": "Unclaimed team tasks", "url": reverse("action_item_list")})
    return {
        "season": season,
        "announcements": announcements,
        "events": events,
        "riders": riders,
        "can_manage": _can_manage(request.user),
        "my_action_items": my_action_items,
        "pending_event_rsvps": pending_event_rsvps,
        "unclaimed_actions": unclaimed_actions,
        "overdue_actions": overdue_actions,
        "attention_count": pending_event_rsvps + len(my_action_items),
        "schedule_items": schedule_items,
        "attention_items": attention_items,
        # IEA role workspaces belong to My Team, not the general barn dashboard.
        "workspace_links": [],
        "arena_person": person,
        "active_barn_roles": tuple(active_roles),
        "upcoming_lesson_occurrences": lesson_occurrences[:5],
        "finance_domains": finance_domains,
        "can_manage_horses": can_manage_horses,
        "active_horse_count": Horse.objects.filter(team=team, active=True).count() if can_manage_horses else None,
        "operational_areas": operational_areas,
        "quick_actions": quick_actions[:6],
        "domain_snapshots": domain_snapshots,
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
    team = organization_for_view_user(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    season = active_period_for_organization(team)

    # The product Dashboard is the stable ArenaLine operations home. Role
    # workspaces remain explicitly available from the dashboard switcher rather
    # than silently replacing the user's home page.
    return render(request, "portal/dashboard.html", _general_context(request, team, season))


@login_required
def dashboard_general(request):
    team = organization_for_view_user(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    season = active_period_for_organization(team)
    return render(request, "portal/dashboard.html", _general_context(request, team, season))


@login_required
def dashboard_coach(request):
    team = organization_for_view_user(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    return _render_coach(request, team, active_period_for_organization(team))


@login_required
def dashboard_team_parent(request):
    team = organization_for_view_user(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    return _render_team_parent(request, team, active_period_for_organization(team))


@login_required
def dashboard_show_lead(request):
    team = organization_for_view_user(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    return _render_show_lead(request, team, active_period_for_organization(team))


@login_required
def dashboard_secretary(request):
    team = organization_for_view_user(request.user)
    if not team:
        return render(request, "portal/no_team.html")
    return _render_secretary(request, team, active_period_for_organization(team))
