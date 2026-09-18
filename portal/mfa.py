import hashlib
import secrets

import pyotp
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone


def new_totp_secret():
    return pyotp.random_base32()


def provisioning_uri(user, secret):
    label = user.email or user.username
    return pyotp.TOTP(secret).provisioning_uri(name=label, issuer_name="ArenaLine")


def verify_totp(secret, code):
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(str(code).replace(" ", ""), valid_window=1)


def generate_recovery_codes(count=8):
    return [f"{secrets.token_hex(4)}-{secrets.token_hex(4)}" for _ in range(count)]


def hash_recovery_codes(codes):
    return [make_password(code) for code in codes]


def consume_recovery_code(profile, code):
    code = (code or "").strip().lower()
    for index, encoded in enumerate(profile.mfa_recovery_codes or []):
        if check_password(code, encoded):
            remaining = list(profile.mfa_recovery_codes)
            remaining.pop(index)
            profile.mfa_recovery_codes = remaining
            profile.save(update_fields=["mfa_recovery_codes"])
            return True
    return False


def enable_mfa(profile, secret, code):
    if not verify_totp(secret, code):
        return None
    recovery_codes = generate_recovery_codes()
    profile.mfa_secret = secret
    profile.mfa_enabled = True
    profile.mfa_confirmed_at = timezone.now()
    profile.mfa_recovery_codes = hash_recovery_codes(recovery_codes)
    profile.save(update_fields=["mfa_secret", "mfa_enabled", "mfa_confirmed_at", "mfa_recovery_codes"])
    return recovery_codes


def disable_mfa(profile):
    profile.mfa_enabled = False
    profile.mfa_secret = ""
    profile.mfa_recovery_codes = []
    profile.mfa_confirmed_at = None
    profile.save(update_fields=["mfa_enabled", "mfa_secret", "mfa_recovery_codes", "mfa_confirmed_at"])
