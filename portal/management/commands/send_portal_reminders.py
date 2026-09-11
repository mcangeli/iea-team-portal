from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db.models import Q, Sum
from django.utils import timezone

from portal.models import ActionItem, CalendarEvent, EventRSVP, GuardianContact, Notification, Rider, SeasonMembership, ShowAvailability, UserProfile, VolunteerLog


class Command(BaseCommand):
    help = "Send in-app/email reminders for show availability, event RSVPs, action items, and volunteer requirements. Safe to run daily."

    def notify(self, user, title, body, link):
        today = timezone.localdate()
        exists = Notification.objects.filter(user=user, title=title, created_at__date=today).exists()
        if exists:
            return False
        Notification.objects.create(user=user, title=title, body=body, link=link)
        profile = getattr(user, "profile", None)
        if settings.EMAIL_HOST and user.email and (not profile or profile.email_reminders):
            send_mail(title, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
        return True

    def handle(self, *args, **options):
        today = timezone.localdate()
        end = today + timedelta(days=7)
        sent = 0
        active_profiles = UserProfile.objects.filter(team__seasons__is_active=True).select_related("team", "user").distinct()
        teams = {p.team for p in active_profiles if p.team_id}
        for team in teams:
            season = team.seasons.filter(is_active=True).first()
            if not season:
                continue
            # Show availability: remind rider + linked guardians only when still pending.
            pending = ShowAvailability.objects.filter(show__season=season, show__show_date__range=(today, end), status=ShowAvailability.Status.PENDING).select_related("show", "rider")
            for row in pending:
                recipient_ids = set()
                if row.rider.user_id:
                    recipient_ids.add(row.rider.user_id)
                recipient_ids.update(row.rider.guardian_links.filter(guardian__user__isnull=False).values_list("guardian__user_id", flat=True))
                recipient_ids.update(row.rider.guardians.values_list("id", flat=True))
                for user in User.objects.filter(id__in=recipient_ids, is_active=True):
                    sent += int(self.notify(user, f"Availability needed: {row.show.name}", f"Please update availability for {row.rider} for {row.show.name} on {row.show.show_date:%B %d}.", f"/shows/{row.show_id}/availability/"))
            # General event RSVP reminders.
            now = timezone.now()
            rsvp_events = CalendarEvent.objects.filter(
                team=team,
                rsvp_requested=True,
                visible_to_all=True,
                starts_at__gte=now,
                starts_at__date__lte=end,
            )
            for event in rsvp_events:
                riders = Rider.objects.filter(team=team, active=True)
                for rider in riders:
                    existing = EventRSVP.objects.filter(event=event, rider=rider).exclude(status=EventRSVP.Status.PENDING).exists()
                    if existing:
                        continue
                    recipient_ids = set()
                    if rider.user_id:
                        recipient_ids.add(rider.user_id)
                    recipient_ids.update(rider.guardian_links.filter(guardian__user__isnull=False).values_list("guardian__user_id", flat=True))
                    recipient_ids.update(rider.guardians.values_list("id", flat=True))
                    for user in User.objects.filter(id__in=recipient_ids, is_active=True):
                        sent += int(self.notify(
                            user,
                            f"RSVP needed: {event.title}",
                            f"Please respond for {rider.display_name} for {event.title}.",
                            "/my-team/",
                        ))

            # Due action items assigned to a user or rider/family.
            due_actions = ActionItem.objects.filter(
                team=team,
                completed=False,
                due_at__isnull=False,
                due_at__gte=now,
                due_at__date__lte=end,
            ).select_related("assigned_to", "rider")
            for item in due_actions:
                recipient_ids = set()
                if item.assigned_to_id:
                    recipient_ids.add(item.assigned_to_id)
                if item.rider_id:
                    if item.rider.user_id:
                        recipient_ids.add(item.rider.user_id)
                    recipient_ids.update(item.rider.guardian_links.filter(guardian__user__isnull=False).values_list("guardian__user_id", flat=True))
                    recipient_ids.update(item.rider.guardians.values_list("id", flat=True))
                for user in User.objects.filter(id__in=recipient_ids, is_active=True):
                    sent += int(self.notify(
                        user,
                        f"Action item due: {item.title}",
                        f"{item.title} is due {timezone.localtime(item.due_at):%B %d at %I:%M %p}.",
                        "/team-hub/actions/",
                    ))

            # Volunteer hours: one weekly-ish reminder per day command is run; duplicate protected per day.
            memberships = SeasonMembership.objects.filter(season=season).select_related("rider")
            for membership in memberships:
                required = season.futures_volunteer_hours_required if membership.team_level == SeasonMembership.TeamLevel.FUTURES else season.upper_volunteer_hours_required
                approved = VolunteerLog.objects.filter(season=season, rider=membership.rider, status=VolunteerLog.Status.APPROVED).aggregate(total=Sum("hours"))["total"] or 0
                remaining = max(required - approved, 0)
                if remaining <= 0:
                    continue
                recipient_ids = set()
                if membership.rider.user_id:
                    recipient_ids.add(membership.rider.user_id)
                recipient_ids.update(membership.rider.guardian_links.filter(guardian__user__isnull=False).values_list("guardian__user_id", flat=True))
                recipient_ids.update(membership.rider.guardians.values_list("id", flat=True))
                for user in User.objects.filter(id__in=recipient_ids, is_active=True):
                    sent += int(self.notify(user, f"Volunteer hours remaining for {membership.rider.display_name}", f"{membership.rider.display_name} has {remaining} volunteer hours remaining for {season.name}.", "/volunteer/"))
        self.stdout.write(self.style.SUCCESS(f"Created {sent} reminder notification(s)."))
