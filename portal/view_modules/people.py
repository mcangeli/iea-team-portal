from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from portal.model_modules.barn_participation import HorsePersonRelationship
from portal.model_modules.people import (
    Committee,
    CommitteeMembership,
    OrganizationGroup,
    OrganizationRoleAssignment,
    PersonRelationship,
    IEAParticipant,
)
from portal.model_modules.station import WorkShiftEntry
from portal.people_forms import (
    CommitteeForm,
    CommitteeMembershipForm,
    OrganizationGroupForm,
    OrganizationRoleAssignmentForm,
    PersonForm,
    PersonCreateForm,
    PersonRelationshipForm,
    PersonRolesForm,

)
from portal.forms import SeasonMembershipForm
from portal.models import Season, SeasonMembership
from portal.people_services import (
    can_manage_people,
    can_view_private_person,
    people_for_user,
    person_for_user,
    require_people_manager,
)
from portal.view_modules.common import _team


def _shift_minutes(shift):
    if not shift.clock_out:
        return 0
    return max(0, int((shift.clock_out - shift.clock_in).total_seconds() // 60))


def _format_minutes(minutes):
    hours, remainder = divmod(int(minutes or 0), 60)
    if hours and remainder:
        return f"{hours}h {remainder}m"
    if hours:
        return f"{hours}h"
    return f"{remainder}m"


def _can_view_work_history(user, person):
    """Work-time records are operational data: managers and the person themself only."""
    if can_manage_people(user):
        return True
    try:
        return user.arena_person.pk == person.pk
    except AttributeError:
        return False


def _effective_today(queryset):
    """Limit dated participation records to those effective today."""
    today = timezone.localdate()
    return queryset.filter(active=True).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today),
        Q(end_date__isnull=True) | Q(end_date__gt=today),
    )


@login_required
def people_directory(request):
    people = people_for_user(request.user)
    return render(
        request,
        "portal/people/directory.html",
        {"people": people, "can_manage_people": can_manage_people(request.user)},
    )


@login_required
def barn_operations(request):
    team = _team(request.user)
    can_manage = can_manage_people(request.user)
    assignments = list(
        _effective_today(OrganizationRoleAssignment.objects.filter(team=team, person__active=True))
        .select_related("person")
        .order_by("person__last_name", "person__first_name", "role")
    )
    horse_links = list(
        _effective_today(HorsePersonRelationship.objects.filter(team=team, person__active=True, horse__active=True))
        .select_related("person", "horse")
        .order_by("horse__name", "relationship_type")
    )
    links_by_person = {}
    for relationship in horse_links:
        links_by_person.setdefault(relationship.person_id, []).append(relationship)

    role_sections = [
        ("training", "Training team", (OrganizationRoleAssignment.Role.TRAINER, OrganizationRoleAssignment.Role.ASSISTANT_TRAINER)),
        ("staff", "Barn management & staff", (OrganizationRoleAssignment.Role.BARN_MANAGER, OrganizationRoleAssignment.Role.BARN_STAFF)),
        ("working_students", "Working students", (OrganizationRoleAssignment.Role.WORKING_STUDENT,)),
        ("boarders", "Boarders", (OrganizationRoleAssignment.Role.BOARDER,)),
        ("board", "Board members", (OrganizationRoleAssignment.Role.BOARD_MEMBER,)),
    ]
    sections = []
    for key, label, roles in role_sections:
        rows = []
        seen = set()
        for assignment in assignments:
            if assignment.role not in roles or assignment.person_id in seen:
                continue
            seen.add(assignment.person_id)
            rows.append({
                "person": assignment.person,
                "roles": [item for item in assignments if item.person_id == assignment.person_id and item.role in roles],
                "horse_relationships": links_by_person.get(assignment.person_id, []),
            })
        sections.append({"key": key, "label": label, "rows": rows})

    return render(
        request,
        "portal/people/barn_operations.html",
        {"sections": sections, "can_manage_people": can_manage},
    )


@login_required
def person_detail(request, pk):
    person = person_for_user(request.user, pk)
    if not person:
        raise Http404
    can_manage = can_manage_people(request.user)
    can_view_private = can_view_private_person(request.user, person)
    can_view_work_history = _can_view_work_history(request.user, person)
    iea_participant = IEAParticipant.objects.filter(team=person.team, person=person).first()
    iea_memberships = SeasonMembership.objects.none()
    if iea_participant:
        iea_memberships = iea_participant.season_memberships.select_related("season", "home_barn").prefetch_related("classes").order_by("-season__start_date")
    work_summary = None
    recent_work_shifts = []
    incoming_family_relationships = _effective_today(PersonRelationship.objects.filter(
        to_person=person,
        relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        from_person__active=True,
    )).select_related("from_person").order_by("-primary_contact", "from_person__last_name", "from_person__first_name")
    if can_view_work_history:
        shifts = list(
            WorkShiftEntry.objects.filter(team=person.team, person=person)
            .select_related("station", "approved_by")
            .order_by("-clock_in")
        )
        total_minutes = approved_minutes = working_student_minutes = 0
        completed_count = pending_count = open_count = 0
        for shift in shifts:
            shift.duration_minutes = _shift_minutes(shift)
            shift.duration_display = _format_minutes(shift.duration_minutes)
            total_minutes += shift.duration_minutes
            if shift.clock_out:
                completed_count += 1
                if shift.approved_at:
                    approved_minutes += shift.duration_minutes
                else:
                    pending_count += 1
            else:
                open_count += 1
            if shift.role == WorkShiftEntry.Role.WORKING_STUDENT:
                working_student_minutes += shift.duration_minutes
        if shifts:
            work_summary = {
                "total": _format_minutes(total_minutes),
                "approved": _format_minutes(approved_minutes),
                "working_student": _format_minutes(working_student_minutes),
                "completed_count": completed_count,
                "pending_count": pending_count,
                "open_count": open_count,
            }
            recent_work_shifts = shifts[:8]
    return render(
        request,
        "portal/people/detail.html",
        {
            "person": person,
            "can_manage_people": can_manage,
            "can_view_private": can_view_private,
            "can_view_work_history": can_view_work_history,
            "iea_participant": iea_participant,
            "iea_memberships": iea_memberships,
            "work_summary": work_summary,
            "recent_work_shifts": recent_work_shifts,
            "incoming_family_relationships": incoming_family_relationships,
        },
    )


def _managed_person(request, pk):
    require_people_manager(request.user)
    team = _team(request.user)
    return get_object_or_404(people_for_user(request.user), pk=pk, team=team)


@login_required
def person_create(request):
    require_people_manager(request.user)
    team = _team(request.user)
    form = PersonCreateForm(request.POST or None, request.FILES or None, team=team)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            person = form.save(commit=False)
            person.team = team
            person.full_clean()
            person.save()

            today = timezone.localdate()
            involvement = set(form.cleaned_data.get("involvement", []))
            season = form.cleaned_data.get("iea_season")
            if season:
                involvement.add(OrganizationRoleAssignment.Role.RIDER)

            for role in involvement:
                assignment, _ = OrganizationRoleAssignment.objects.get_or_create(
                    team=team,
                    person=person,
                    role=role,
                    start_date=today,
                    defaults={"active": True},
                )
                if not assignment.active or assignment.end_date is not None:
                    assignment.active = True
                    assignment.end_date = None
                    assignment.save(update_fields=["active", "end_date"])

            if season:
                participant, _ = IEAParticipant.objects.get_or_create(team=team, person=person)
                membership = SeasonMembership.objects.create(
                    season=season,
                    iea_participant=participant,
                    team_level=form.cleaned_data["iea_team_level"],
                )
                membership.classes.set(form.cleaned_data.get("iea_classes"))

        messages.success(request, f"Added {person.display_name} to People.")
        return redirect("person_detail", pk=person.pk)
    return render(request, "portal/people/form.html", {"form": form, "title": "Add person", "eyebrow": "PEOPLE"})



@login_required
def person_iea_membership_edit(request, pk, season_pk=None):
    person = _managed_person(request, pk)
    season = get_object_or_404(Season, pk=season_pk, team=person.team) if season_pk else Season.objects.filter(team=person.team, is_active=True).order_by("-start_date").first()
    if not season:
        messages.error(request, "Create or activate an IEA season first.")
        return redirect("person_detail", pk=person.pk)

    participant, _ = IEAParticipant.objects.get_or_create(team=person.team, person=person)
    membership, _ = SeasonMembership.objects.get_or_create(
        season=season,
        iea_participant=participant,
    )
    form = SeasonMembershipForm(request.POST or None, instance=membership, season=season)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            membership = form.save(commit=False)
            membership.iea_participant = participant
            membership.full_clean()
            membership.save()
            form.save_m2m()
            OrganizationRoleAssignment.objects.get_or_create(
                team=person.team,
                person=person,
                role=OrganizationRoleAssignment.Role.RIDER,
                active=True,
            )
        messages.success(request, f"{season.name} IEA participation updated for {person.display_name}.")
        return redirect("person_detail", pk=person.pk)
    return render(request, "portal/people/subrecord_form.html", {
        "person": person,
        "form": form,
        "title": f"{season.name} IEA participation",
        "eyebrow": "IEA PARTICIPATION",
        "description": "Manage this Person's team level, classes, home barn, and season notes without creating a separate Rider identity.",
    })


@login_required
def person_edit(request, pk):
    person = _managed_person(request, pk)
    form = PersonForm(request.POST or None, request.FILES or None, instance=person, team=person.team)
    if request.method == "POST" and form.is_valid():
        person = form.save()
        messages.success(request, f"Updated {person.display_name}.")
        return redirect("person_detail", pk=person.pk)
    return render(request, "portal/people/form.html", {"form": form, "person": person, "title": f"Edit {person.display_name}", "eyebrow": "PEOPLE"})


def _person_subrecord_form(request, *, person, form, title, eyebrow, description=""):
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        if hasattr(item, "person_id"):
            item.person = person
        item.full_clean()
        item.save()
        messages.success(request, f"Updated {title.lower()} for {person.display_name}.")
        return redirect("person_detail", pk=person.pk)
    return render(request, "portal/people/subrecord_form.html", {
        "person": person, "form": form, "title": title, "eyebrow": eyebrow, "description": description
    })


@login_required
def person_role_add(request, pk):
    person = _managed_person(request, pk)
    form = PersonRolesForm(request.POST or None, person=person)
    if request.method == "POST" and form.is_valid():
        selected_roles = set(form.cleaned_data["roles"])
        today = timezone.localdate()
        for role_value, _label in OrganizationRoleAssignment.Role.choices:
            assignment = OrganizationRoleAssignment.objects.filter(person=person, team=person.team, role=role_value).order_by("-active", "-id").first()
            if role_value in selected_roles:
                if assignment:
                    assignment.active = True
                    assignment.end_date = None
                    if not assignment.start_date:
                        assignment.start_date = today
                    assignment.full_clean()
                    assignment.save(update_fields=["active", "start_date", "end_date"])
                else:
                    OrganizationRoleAssignment.objects.create(
                        team=person.team,
                        person=person,
                        role=role_value,
                        start_date=today,
                        active=True,
                    )
            elif assignment and assignment.active:
                assignment.active = False
                if not assignment.end_date:
                    assignment.end_date = today
                assignment.full_clean()
                assignment.save(update_fields=["active", "end_date"])

        messages.success(request, f"Updated current roles for {person.display_name}.")
        return redirect("person_detail", pk=person.pk)

    return render(
        request,
        "portal/people/subrecord_form.html",
        {
            "person": person,
            "form": form,
            "title": "Manage roles",
            "eyebrow": "PARTICIPATION",
            "description": "Select every role this person currently holds. Roles are independent, so Parent / Guardian, Rider, Boarder, and other responsibilities can be active together.",
        },
    )


@login_required
def person_role_edit(request, pk, role_pk):
    person = _managed_person(request, pk)
    role = get_object_or_404(OrganizationRoleAssignment, pk=role_pk, person=person, team=person.team)
    form = OrganizationRoleAssignmentForm(request.POST or None, instance=role)
    return _person_subrecord_form(
        request,
        person=person,
        form=form,
        title=f"Edit {role.get_role_display()} details",
        eyebrow="PARTICIPATION",
        description="The role itself is managed from Manage roles. Use this page for dates, status, and notes for this specific role assignment.",
    )


@login_required
def person_relationship_add(request, pk):
    person = _managed_person(request, pk)
    form = PersonRelationshipForm(request.POST or None, team=person.team, source_person=person)
    if request.method == "POST" and form.is_valid():
        relationship = form.save(commit=False)
        relationship.from_person = person
        relationship.full_clean()
        relationship.save()
        messages.success(request, f"Added relationship for {person.display_name}.")
        return redirect("person_detail", pk=person.pk)
    return render(request, "portal/people/subrecord_form.html", {
        "person": person, "form": form, "title": "Add relationship", "eyebrow": "RELATIONSHIPS"
    })


@login_required
def person_relationship_edit(request, pk, relationship_pk):
    person = _managed_person(request, pk)
    relationship = get_object_or_404(PersonRelationship, pk=relationship_pk, from_person=person)
    form = PersonRelationshipForm(request.POST or None, instance=relationship, team=person.team, source_person=person)
    return _person_subrecord_form(request, person=person, form=form, title="Edit relationship", eyebrow="RELATIONSHIPS")


@login_required
def person_committee_add(request, pk):
    person = _managed_person(request, pk)
    form = CommitteeMembershipForm(request.POST or None, team=person.team)
    if request.method == "POST" and form.is_valid():
        membership = form.save(commit=False)
        membership.person = person
        membership.full_clean()
        membership.save()
        messages.success(request, f"Added committee membership for {person.display_name}.")
        return redirect("person_detail", pk=person.pk)
    return render(request, "portal/people/subrecord_form.html", {
        "person": person, "form": form, "title": "Add committee membership", "eyebrow": "COMMITTEES"
    })


@login_required
def person_committee_edit(request, pk, membership_pk):
    person = _managed_person(request, pk)
    membership = get_object_or_404(CommitteeMembership, pk=membership_pk, person=person, committee__team=person.team)
    if membership.legacy_committee_assignment_id:
        messages.info(request, "This membership is managed by its IEA assignment and cannot be edited here.")
        return redirect("person_detail", pk=person.pk)
    form = CommitteeMembershipForm(request.POST or None, instance=membership, team=person.team)
    return _person_subrecord_form(request, person=person, form=form, title="Edit committee membership", eyebrow="COMMITTEES")


@login_required
def people_structure(request):
    require_people_manager(request.user)
    team = _team(request.user)
    groups = OrganizationGroup.objects.filter(team=team).select_related("parent").order_by("sort_order", "name")
    committees = Committee.objects.filter(team=team).select_related("group").order_by("group__name", "sort_order", "name")
    return render(request, "portal/people/structure.html", {"groups": groups, "committees": committees})


@login_required
def organization_group_detail(request, group_pk):
    require_people_manager(request.user)
    team = _team(request.user)
    group = get_object_or_404(OrganizationGroup, pk=group_pk, team=team)
    committees = list(group.committees.filter(team=team).prefetch_related("memberships__person").order_by("sort_order", "name"))
    today = timezone.localdate()
    active_memberships = []
    for committee in committees:
        for membership in committee.memberships.all():
            if (
                membership.active
                and membership.person.active
                and (membership.start_date is None or membership.start_date <= today)
                and (membership.end_date is None or membership.end_date > today)
            ):
                active_memberships.append(membership)
    people = []
    seen = set()
    for membership in active_memberships:
        if membership.person_id not in seen:
            seen.add(membership.person_id)
            people.append(membership.person)
    subgroups = group.subgroups.filter(team=team).order_by("sort_order", "name")
    return render(request, "portal/people/group_detail.html", {
        "group": group,
        "committees": committees,
        "active_memberships": active_memberships,
        "people": people,
        "subgroups": subgroups,
    })


@login_required
def committee_detail(request, committee_pk):
    require_people_manager(request.user)
    team = _team(request.user)
    committee = get_object_or_404(Committee.objects.select_related("group"), pk=committee_pk, team=team)
    memberships = committee.memberships.select_related("person").order_by("position", "person__last_name", "person__first_name")
    today = timezone.localdate()
    active_memberships = [
        membership
        for membership in memberships
        if (
            membership.active
            and membership.person.active
            and (membership.start_date is None or membership.start_date <= today)
            and (membership.end_date is None or membership.end_date > today)
        )
    ]
    return render(request, "portal/people/committee_detail.html", {
        "committee": committee,
        "memberships": memberships,
        "active_memberships": active_memberships,
    })


@login_required
def organization_group_add(request):
    require_people_manager(request.user)
    team = _team(request.user)
    form = OrganizationGroupForm(request.POST or None, team=team)
    if request.method == "POST" and form.is_valid():
        group = form.save(commit=False)
        group.team = team
        group.full_clean()
        group.save()
        messages.success(request, f"Added group {group.name}.")
        return redirect("people_structure")
    return render(request, "portal/people/structure_form.html", {"form": form, "title": "Add group", "eyebrow": "GROUPS & PROGRAMS"})


@login_required
def organization_group_edit(request, group_pk):
    require_people_manager(request.user)
    team = _team(request.user)
    group = get_object_or_404(OrganizationGroup, pk=group_pk, team=team)
    form = OrganizationGroupForm(request.POST or None, instance=group, team=team)
    if request.method == "POST" and form.is_valid():
        group = form.save(commit=False)
        group.full_clean()
        group.save()
        messages.success(request, f"Updated {group.name}.")
        return redirect("people_structure")
    return render(request, "portal/people/structure_form.html", {"form": form, "title": "Edit group", "eyebrow": "GROUPS & PROGRAMS"})


@login_required
def committee_add(request):
    require_people_manager(request.user)
    team = _team(request.user)
    form = CommitteeForm(request.POST or None, team=team)
    if request.method == "POST" and form.is_valid():
        committee = form.save(commit=False)
        committee.team = team
        committee.full_clean()
        committee.save()
        messages.success(request, f"Added committee {committee.name}.")
        return redirect("people_structure")
    return render(request, "portal/people/structure_form.html", {"form": form, "title": "Add committee", "eyebrow": "COMMITTEES"})


@login_required
def committee_edit(request, committee_pk):
    require_people_manager(request.user)
    team = _team(request.user)
    committee = get_object_or_404(Committee, pk=committee_pk, team=team)
    form = CommitteeForm(request.POST or None, instance=committee, team=team)
    if request.method == "POST" and form.is_valid():
        committee = form.save(commit=False)
        committee.full_clean()
        committee.save()
        messages.success(request, f"Updated {committee.name}.")
        return redirect("people_structure")
    return render(request, "portal/people/structure_form.html", {"form": form, "title": "Edit committee", "eyebrow": "COMMITTEES"})
