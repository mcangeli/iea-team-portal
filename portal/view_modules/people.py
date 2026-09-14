from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from portal.model_modules.people import (
    Committee,
    CommitteeMembership,
    OrganizationGroup,
    OrganizationRoleAssignment,
    PersonRelationship,
)
from portal.people_forms import (
    CommitteeForm,
    CommitteeMembershipForm,
    OrganizationGroupForm,
    OrganizationRoleAssignmentForm,
    PersonForm,
    PersonRelationshipForm,
)
from portal.people_services import (
    can_manage_people,
    can_view_private_person,
    people_for_user,
    person_for_user,
    require_people_manager,
)
from portal.view_modules.common import _team


@login_required
def people_directory(request):
    people = people_for_user(request.user)
    return render(
        request,
        "portal/people/directory.html",
        {
            "people": people,
            "can_manage_people": can_manage_people(request.user),
        },
    )


@login_required
def person_detail(request, pk):
    person = person_for_user(request.user, pk)
    if not person:
        raise Http404
    return render(
        request,
        "portal/people/detail.html",
        {
            "person": person,
            "can_manage_people": can_manage_people(request.user),
            "can_view_private": can_view_private_person(request.user, person),
        },
    )


@login_required
def person_create(request):
    require_people_manager(request.user)
    team = _team(request.user)
    form = PersonForm(request.POST or None, request.FILES or None, team=team)
    if request.method == "POST" and form.is_valid():
        person = form.save(commit=False)
        person.team = team
        person.full_clean()
        person.save()
        messages.success(request, f"Added {person.display_name} to People.")
        return redirect("person_detail", pk=person.pk)
    return render(request, "portal/people/form.html", {"form": form, "mode": "add"})


@login_required
def person_edit(request, pk):
    require_people_manager(request.user)
    person = person_for_user(request.user, pk)
    if not person:
        raise Http404
    form = PersonForm(
        request.POST or None,
        request.FILES or None,
        instance=person,
        team=person.team,
    )
    if request.method == "POST" and form.is_valid():
        person = form.save(commit=False)
        person.full_clean()
        person.save()
        messages.success(request, f"Updated {person.display_name}.")
        return redirect("person_detail", pk=person.pk)
    return render(
        request,
        "portal/people/form.html",
        {"form": form, "mode": "edit", "person": person},
    )


def _managed_person(request, pk):
    require_people_manager(request.user)
    person = person_for_user(request.user, pk)
    if not person:
        raise Http404
    return person


def _person_subrecord_form(request, *, person, form, title, eyebrow):
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.full_clean()
        record.save()
        messages.success(request, f"Updated {person.display_name}'s organization profile.")
        return redirect("person_detail", pk=person.pk)
    return render(
        request,
        "portal/people/subrecord_form.html",
        {"person": person, "form": form, "title": title, "eyebrow": eyebrow},
    )


@login_required
def person_role_add(request, pk):
    person = _managed_person(request, pk)
    form = OrganizationRoleAssignmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        role = form.save(commit=False)
        role.team = person.team
        role.person = person
        role.full_clean()
        role.save()
        messages.success(request, f"Added {role.get_role_display()} role to {person.display_name}.")
        return redirect("person_detail", pk=person.pk)
    return render(request, "portal/people/subrecord_form.html", {
        "person": person, "form": form, "title": "Add role", "eyebrow": "PARTICIPATION"
    })


@login_required
def person_role_edit(request, pk, role_pk):
    person = _managed_person(request, pk)
    role = get_object_or_404(OrganizationRoleAssignment, pk=role_pk, person=person, team=person.team)
    form = OrganizationRoleAssignmentForm(request.POST or None, instance=role)
    return _person_subrecord_form(
        request, person=person, form=form, title="Edit role", eyebrow="PARTICIPATION"
    )


@login_required
def person_relationship_add(request, pk):
    person = _managed_person(request, pk)
    form = PersonRelationshipForm(
        request.POST or None, team=person.team, source_person=person
    )
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
    relationship = get_object_or_404(
        PersonRelationship, pk=relationship_pk, from_person=person
    )
    form = PersonRelationshipForm(
        request.POST or None,
        instance=relationship,
        team=person.team,
        source_person=person,
    )
    return _person_subrecord_form(
        request, person=person, form=form, title="Edit relationship", eyebrow="RELATIONSHIPS"
    )


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
    membership = get_object_or_404(
        CommitteeMembership, pk=membership_pk, person=person, committee__team=person.team
    )
    form = CommitteeMembershipForm(
        request.POST or None, instance=membership, team=person.team
    )
    return _person_subrecord_form(
        request, person=person, form=form, title="Edit committee membership", eyebrow="COMMITTEES"
    )


@login_required
def people_structure(request):
    require_people_manager(request.user)
    team = _team(request.user)
    groups = OrganizationGroup.objects.filter(team=team).select_related("parent").order_by("sort_order", "name")
    committees = Committee.objects.filter(team=team).select_related("group").order_by("group__name", "sort_order", "name")
    return render(request, "portal/people/structure.html", {"groups": groups, "committees": committees})


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
