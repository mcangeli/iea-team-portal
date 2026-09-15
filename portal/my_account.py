from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from portal.model_modules.people import Person


class MyAccountForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            "preferred_name",
            "email",
            "phone",
            "school",
            "graduation_year",
            "bio",
            "photo",
            "website_url",
            "instagram_url",
            "facebook_url",
            "tiktok_url",
            "youtube_url",
            "public_profile_enabled",
        ]
        widgets = {"bio": forms.Textarea(attrs={"rows": 5})}


@login_required
def my_account(request):
    try:
        person = request.user.arena_person
    except Person.DoesNotExist:
        person = None

    if person is None:
        return render(request, "portal/people/my_account_unavailable.html", status=404)

    form = MyAccountForm(request.POST or None, request.FILES or None, instance=person)
    if request.method == "POST" and form.is_valid():
        person = form.save()
        user = request.user
        if user.email != person.email:
            user.email = person.email
            user.save(update_fields=["email"])
        messages.success(request, "Your account details have been updated.")
        return redirect("my_account")

    roles = person.role_assignments.filter(active=True).order_by("role")
    relationships = person.outgoing_relationships.filter(active=True).select_related("to_person")
    incoming_relationships = person.incoming_relationships.filter(active=True).select_related("from_person")
    committees = person.committee_memberships.filter(active=True).select_related("committee", "committee__group")
    horses = person.horse_relationships.filter(active=True).select_related("horse")

    legacy = getattr(person, "legacy_identity", None)
    programs = []
    if legacy and legacy.rider_id:
        memberships = legacy.rider.season_memberships.select_related("season").order_by("-season__start_date")
        programs = list(memberships)

    return render(
        request,
        "portal/people/my_account.html",
        {
            "person": person,
            "form": form,
            "roles": roles,
            "relationships": relationships,
            "incoming_relationships": incoming_relationships,
            "committees": committees,
            "horses": horses,
            "programs": programs,
        },
    )
