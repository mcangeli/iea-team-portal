from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render

from portal.people_forms import PersonForm
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
