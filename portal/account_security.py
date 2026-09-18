from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

EMAIL_VERIFICATION_SALT = "arenaline.email-verification.v1"
EMAIL_VERIFICATION_MAX_AGE = 60 * 60 * 24


def make_email_verification_token(user):
    profile = user.profile
    email = (profile.pending_email or user.email or "").strip().lower()
    return signing.dumps({"user_id": user.pk, "email": email}, salt=EMAIL_VERIFICATION_SALT)


def read_email_verification_token(token):
    return signing.loads(token, salt=EMAIL_VERIFICATION_SALT, max_age=EMAIL_VERIFICATION_MAX_AGE)


def send_email_verification(request, user):
    profile = user.profile
    email = (profile.pending_email or user.email or "").strip()
    if not email:
        return False
    token = make_email_verification_token(user)
    verify_url = request.build_absolute_uri(reverse("email_verify", kwargs={"token": token}))
    send_mail(
        "Verify your ArenaLine email address",
        (
            f"Verify {email} for your ArenaLine account by opening this link:\n\n"
            f"{verify_url}\n\n"
            "This link expires in 24 hours. If you did not request this, you can ignore this message."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
    return True


def begin_email_verification(user, email):
    profile = user.profile
    profile.pending_email = email.strip().lower()
    profile.pending_email_requested_at = timezone.now()
    profile.save(update_fields=["pending_email", "pending_email_requested_at"])


def complete_email_verification(user, token_email):
    profile = user.profile
    expected = (profile.pending_email or user.email or "").strip().lower()
    if not expected or expected != token_email.strip().lower():
        return False
    changed = bool(profile.pending_email)
    user.email = expected
    user.save(update_fields=["email"])
    profile.email_verified_at = timezone.now()
    profile.pending_email = ""
    profile.pending_email_requested_at = None
    profile.save(update_fields=["email_verified_at", "pending_email", "pending_email_requested_at"])
    return changed
