from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from portal.model_modules.people import Committee, CommitteeMembership, OrganizationGroup
from portal.people_services import require_people_manager
from portal.view_modules.common import _team


def _active_memberships(committee):
    """Return committee memberships currently effective for operational dashboards."""
    today = timezone.localdate()
    memberships = (
        CommitteeMembership.objects.filter(committee=committee, active=True, person__active=True)
        .select_related("person", "committee", "committee__group")
        .order_by("position", "person__last_name", "person__first_name")
    )
    return [
        membership
        for membership in memberships
        if (membership.start_date is None or membership.start_date <= today)
        and (membership.end_date is None or membership.end_date > today)
    ]


@login_required
def organization_group_detail(request, group_pk):
    require_people_manager(request.user)
    team = _team(request.user)
    group = get_object_or_404(
        OrganizationGroup.objects.select_related("parent"), pk=group_pk, team=team
    )
    subgroups = list(group.subgroups.all().order_by("sort_order", "name"))
    committees = list(group.committees.all().order_by("sort_order", "name"))
    people = {}
    committee_rows = []
    for committee in committees:
        memberships = _active_memberships(committee)
        committee_rows.append({"committee": committee, "memberships": memberships})
        for membership in memberships:
            entry = people.setdefault(
                membership.person_id,
                {"person": membership.person, "responsibilities": []},
            )
            entry["responsibilities"].append(
                f"{committee.name} · {membership.get_position_display()}"
            )
    people_rows = sorted(
        people.values(), key=lambda row: (row["person"].last_name, row["person"].first_name)
    )
    return render(
        request,
        "portal/people/group_detail.html",
        {
            "group": group,
            "subgroups": subgroups,
            "committee_rows": committee_rows,
            "people_rows": people_rows,
        },
    )


@login_required
def committee_detail(request, committee_pk):
    require_people_manager(request.user)
    team = _team(request.user)
    committee = get_object_or_404(
        Committee.objects.select_related("group"), pk=committee_pk, team=team
    )
    memberships = _active_memberships(committee)
    return render(
        request,
        "portal/people/committee_detail.html",
        {"committee": committee, "memberships": memberships},
    )
