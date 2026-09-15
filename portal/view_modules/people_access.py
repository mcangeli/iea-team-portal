from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from portal.people_forms import PersonLoginAccessForm
from portal.people_services import person_for_user, require_people_manager


@login_required
def person_login_create(request, pk):
    require_people_manager(request.user)
    person = person_for_user(request.user, pk)
    if not person:
        from django.http import Http404
        raise Http404
    if person.user_id:
        messages.info(request, f"{person.display_name} already has login access. Manage that account instead.")
        return redirect("user_edit", pk=person.user_id)
    form = PersonLoginAccessForm(request.POST or None, person=person, actor=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Login access created for {person.display_name}. They must change the temporary password at first login.")
        return redirect("person_detail", pk=person.pk)
    return render(request, "portal/people/subrecord_form.html", {
        "person": person,
        "form": form,
        "title": "Create login access",
        "eyebrow": "ACCESS",
        "description": "Create ArenaLine credentials for this Person. Their identity, relationships, and participation remain managed from People.",
    })
