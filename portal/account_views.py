from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .account_forms import MyAccountForm
from .forms import NotificationPreferenceForm
from .model_modules.people import Person


def _account_person(user):
    try:
        return user.arena_person
    except Person.DoesNotExist:
        return None


@login_required
def my_account(request):
    profile = getattr(request.user, "profile", None)
    person = _account_person(request.user)
    roles = person.role_assignments.filter(active=True).order_by("role") if person else []
    relationships = person.outgoing_relationships.filter(active=True).select_related("to_person") if person else []
    incoming_relationships = person.incoming_relationships.filter(active=True).select_related("from_person") if person else []
    committees = person.committee_memberships.filter(active=True).select_related("committee", "committee__group") if person else []
    return render(request, "portal/my_account.html", {
        "profile": profile,
        "team": getattr(profile, "team", None) if profile else None,
        "person": person,
        "roles": roles,
        "relationships": relationships,
        "incoming_relationships": incoming_relationships,
        "committees": committees,
        "linked_rider": getattr(request.user, "rider_record", None),
        "linked_guardian": getattr(request.user, "guardian_contact", None),
    })


@login_required
def my_account_edit(request):
    person = _account_person(request.user)
    if person is None:
        messages.error(request, "Your login has not yet been linked to a Person profile. Please contact an ArenaLine administrator.")
        return redirect("my_account")
    form = MyAccountForm(request.POST or None, request.FILES or None, instance=person)
    if request.method == "POST" and form.is_valid():
        person = form.save()
        if request.user.email != person.email:
            request.user.email = person.email
            request.user.save(update_fields=["email"])
        rider = getattr(request.user, "rider_record", None)
        if rider:
            rider.email = person.email
            rider.save(update_fields=["email"])
        guardian = getattr(request.user, "guardian_contact", None)
        if guardian:
            guardian.email = person.email
            guardian.save(update_fields=["email"])
        messages.success(request, "Your profile information has been updated.")
        return redirect("my_account")
    return render(request, "portal/form.html", {
        "form": form, "title": "Profile information", "eyebrow": "MY ACCOUNT",
    })


@login_required
def my_password_change(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        if hasattr(user, "profile") and user.profile.must_change_password:
            user.profile.must_change_password = False
            user.profile.save(update_fields=["must_change_password"])
        messages.success(request, "Your password has been changed.")
        return redirect("my_account")
    return render(request, "portal/form.html", {
        "form": form, "title": "Change password", "eyebrow": "MY ACCOUNT",
    })


@login_required
def my_notification_preferences(request):
    if not hasattr(request.user, "profile"):
        raise PermissionDenied
    form = NotificationPreferenceForm(request.POST or None, instance=request.user.profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Notification preferences updated.")
        return redirect("my_account")
    return render(request, "portal/form.html", {
        "form": form, "title": "Notification preferences", "eyebrow": "MY ACCOUNT",
    })
