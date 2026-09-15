"""Private helpers for the communications view domain."""

from django.conf import settings
from django.core.mail import send_mail

from ..models import Notification
from ..people_communications import announcement_recipients
from .common import _active_season


def _announcement_recipients(announcement):
    """Compatibility entry point backed by People-aware recipient discovery."""
    return announcement_recipients(announcement, active_season_resolver=_active_season)


def _deliver_announcement(announcement):
    recipients = list(_announcement_recipients(announcement))
    Notification.objects.filter(announcement=announcement).delete()
    Notification.objects.bulk_create([
        Notification(user=user, announcement=announcement, title=announcement.title, body=announcement.body, link="/")
        for user in recipients
    ])
    if announcement.send_email and settings.EMAIL_HOST:
        for user in recipients:
            profile = getattr(user, "profile", None)
            if not user.email or (profile and not profile.email_announcements):
                continue
            send_mail(
                subject=f"{announcement.team.short_name or announcement.team.name}: {announcement.title}",
                message=announcement.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
    return len(recipients)
