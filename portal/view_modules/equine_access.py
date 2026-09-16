from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..equine_access_forms import HorseManagementCapabilityForm
from ..model_modules.capabilities import OrganizationCapabilityAssignment
from ..model_modules.people import Person
from ..people_services import require_people_manager
from ..platform import organization_for_view_user


@login_required
def person_horse_access(request, person_pk):
    """Manage explicit horse authorization separately from organizational roles."""
    require_people_manager(request.user)
    team = organization_for_view_user(request.user)
    person = get_object_or_404(Person, pk=person_pk, team=team)
    assignment = OrganizationCapabilityAssignment.objects.filter(
        team=team,
        person=person,
        capability=OrganizationCapabilityAssignment.Capability.MANAGE_HORSES,
    ).first()
    form = HorseManagementCapabilityForm(
        request.POST or None,
        instance=assignment,
        person=person,
        initial={"active": False} if assignment is None else None,
    )
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.team = team
        item.person = person
        item.capability = OrganizationCapabilityAssignment.Capability.MANAGE_HORSES
        item.save()
        messages.success(request, f"Horse management access updated for {person.display_name}.")
        return redirect("person_detail", pk=person.pk)
    return render(
        request,
        "portal/people/horse_access_form.html",
        {
            "form": form,
            "person": person,
            "assignment": assignment,
        },
    )
