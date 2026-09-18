from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.core import signing
from django.shortcuts import redirect, render
from django.db import transaction

from .account_forms import EmailChangeForm, MFAConfirmForm, MFADisableForm, MyAccountForm
from .account_security import begin_email_verification, complete_email_verification, read_email_verification_token, send_email_verification
from .mfa import disable_mfa, enable_mfa, new_totp_secret, provisioning_uri
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


@login_required
def email_change(request):
    form = EmailChangeForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                begin_email_verification(request.user, form.cleaned_data["email"])
                send_email_verification(request, request.user)
        except Exception:
            messages.error(request, "ArenaLine could not send the verification email. Your current email address is unchanged.")
            return render(request, "portal/form.html", {
                "form": form, "title": "Change email address", "eyebrow": "ACCOUNT SECURITY",
            })
        messages.success(request, "Verification sent to your new email address. Your current email remains active until verification is complete.")
        return redirect("my_account")
    return render(request, "portal/form.html", {
        "form": form, "title": "Change email address", "eyebrow": "ACCOUNT SECURITY",
    })


@login_required
def email_verification_resend(request):
    if request.method == "POST":
        if send_email_verification(request, request.user):
            messages.success(request, "A new verification email has been sent.")
        else:
            messages.error(request, "Add an email address before requesting verification.")
    return redirect("my_account")


@login_required
def email_verify(request, token):
    try:
        payload = read_email_verification_token(token)
    except signing.SignatureExpired:
        messages.error(request, "That verification link has expired. Request a new one from My Account.")
        return redirect("my_account")
    except signing.BadSignature:
        messages.error(request, "That verification link is invalid.")
        return redirect("my_account")

    if payload.get("user_id") != request.user.pk:
        messages.error(request, "That verification link belongs to a different ArenaLine account.")
        return redirect("my_account")
    if not complete_email_verification(request.user, payload.get("email", "")):
        messages.error(request, "That verification request is no longer current.")
        return redirect("my_account")

    # Synchronize canonical contact records only after the new login email is verified.
    email = request.user.email
    person = _account_person(request.user)
    if person and person.email != email:
        person.email = email
        person.save(update_fields=["email"])
    rider = getattr(request.user, "rider_record", None)
    if rider and rider.email != email:
        rider.email = email
        rider.save(update_fields=["email"])
    guardian = getattr(request.user, "guardian_contact", None)
    if guardian and guardian.email != email:
        guardian.email = email
        guardian.save(update_fields=["email"])

    messages.success(request, "Your email address has been verified.")
    return redirect("my_account")


@login_required
def mfa_setup(request):
    if request.user.profile.mfa_enabled:
        messages.info(request, "Multi-factor authentication is already enabled.")
        return redirect("my_account")
    secret = request.session.get("mfa_enrollment_secret")
    if not secret:
        secret = new_totp_secret()
        request.session["mfa_enrollment_secret"] = secret
    form = MFAConfirmForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        recovery_codes = enable_mfa(request.user.profile, secret, form.cleaned_data["code"])
        if recovery_codes is None:
            form.add_error("code", "That authenticator code is not valid. Check your device time and try again.")
        else:
            request.session.pop("mfa_enrollment_secret", None)
            # Do not rotate or re-save the session during the enrollment POST.
            # Django's session middleware persists this payload after the
            # response; forcing save here can be overwritten by middleware.
            request.session["mfa_recovery_codes_once"] = recovery_codes
            return redirect("mfa_recovery_codes")
    return render(request, "portal/mfa_setup.html", {
        "form": form, "secret": secret, "provisioning_uri": provisioning_uri(request.user, secret),
    })


@login_required
def mfa_recovery_codes(request):
    codes = request.session.pop("mfa_recovery_codes_once", None)
    if not codes:
        return redirect("my_account")
    return render(request, "portal/mfa_recovery_codes.html", {"recovery_codes": codes})


@login_required
def mfa_disable(request):
    if not request.user.profile.mfa_enabled:
        return redirect("my_account")
    form = MFADisableForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        disable_mfa(request.user.profile)
        request.session.pop("mfa_enrollment_secret", None)
        messages.success(request, "Multi-factor authentication has been disabled.")
        return redirect("my_account")
    return render(request, "portal/form.html", {
        "form": form, "title": "Disable multi-factor authentication", "eyebrow": "ACCOUNT SECURITY",
    })
