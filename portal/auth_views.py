from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .mfa import consume_recovery_code, verify_totp

MFA_PENDING_USER_ID = "mfa_pending_user_id"
MFA_PENDING_BACKEND = "mfa_pending_backend"
MFA_PENDING_NEXT = "mfa_pending_next"


class ArenaLineLoginView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        user = form.get_user()
        profile = getattr(user, "profile", None)
        if not profile or not profile.mfa_enabled:
            return super().form_valid(form)

        self.request.session[MFA_PENDING_USER_ID] = user.pk
        self.request.session[MFA_PENDING_BACKEND] = user.backend
        self.request.session[MFA_PENDING_NEXT] = self.get_success_url()
        return redirect("mfa_login_challenge")


class MFALoginChallengeForm(forms.Form):
    code = forms.CharField(label="Authenticator or recovery code", max_length=32)


def mfa_login_challenge(request):
    from django.contrib.auth import get_user_model, login

    user_id = request.session.get(MFA_PENDING_USER_ID)
    backend = request.session.get(MFA_PENDING_BACKEND)
    if not user_id or not backend:
        return redirect("login")

    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if not user or not hasattr(user, "profile") or not user.profile.mfa_enabled:
        _clear_pending(request)
        return redirect("login")

    form = MFALoginChallengeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["code"].strip()
        accepted = verify_totp(user.profile.mfa_secret, code)
        if not accepted:
            accepted = consume_recovery_code(user.profile, code)
        if accepted:
            destination = request.session.get(MFA_PENDING_NEXT) or "/"
            _clear_pending(request)
            login(request, user, backend=backend)
            request.session["mfa_verified"] = True
            return redirect(destination)
        form.add_error("code", "That verification code is not valid.")

    return render(request, "registration/mfa_challenge.html", {"form": form})


def _clear_pending(request):
    for key in (MFA_PENDING_USER_ID, MFA_PENDING_BACKEND, MFA_PENDING_NEXT):
        request.session.pop(key, None)
