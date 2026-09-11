from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .account_forms import MyAccountForm
from .forms import NotificationPreferenceForm


@login_required
def my_account(request):
    profile = getattr(request.user, "profile", None)
    return render(request, "portal/my_account.html", {
        "profile": profile,
        "team": getattr(profile, "team", None) if profile else None,
        "linked_rider": getattr(request.user, "rider_record", None),
        "linked_guardian": getattr(request.user, "guardian_contact", None),
    })


@login_required
def my_account_edit(request):
    form = MyAccountForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        rider = getattr(user, "rider_record", None)
        if rider:
            rider.email = user.email
            rider.save(update_fields=["email"])
        guardian = getattr(user, "guardian_contact", None)
        if guardian:
            guardian.email = user.email
            guardian.first_name = user.first_name
            guardian.last_name = user.last_name
            guardian.save(update_fields=["email", "first_name", "last_name"])
        messages.success(request, "Your account information has been updated.")
        return redirect("my_account")
    return render(request, "portal/form.html", {
        "form": form, "title": "Account information", "eyebrow": "MY ACCOUNT",
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
