from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """Keep temporary-password accounts out of the portal until they choose a new password."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and hasattr(user, "profile") and user.profile.must_change_password:
            allowed = {
                reverse("password_change_required"),
                reverse("logout"),
            }
            if request.path not in allowed and not request.path.startswith("/static/") and not request.path.startswith("/media/"):
                return redirect("password_change_required")
        return self.get_response(request)
