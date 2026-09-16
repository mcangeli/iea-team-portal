from datetime import date, datetime, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.equine_care import HorseCareRecord
from portal.model_modules.horses import Horse
from portal.model_modules.lessons import LessonOccurrence, LessonProgram, LessonSeries
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import CalendarEvent, Team


class UnifiedCalendarUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Calendar UI Barn")
        self.user = User.objects.create_user("calendar-admin", password="test")
        self.user.profile.team = self.team
        self.user.profile.role = "admin"
        self.user.profile.save()
        self.person = Person.objects.create(team=self.team, user=self.user, first_name="Taylor", last_name="Trainer")
        OrganizationRoleAssignment.objects.create(team=self.team, person=self.person, role=OrganizationRoleAssignment.Role.TRAINER)
        self.program = LessonProgram.objects.create(team=self.team, name="Barn Program")
        self.series = LessonSeries.objects.create(program=self.program, name="Tuesday Lesson", instructor=self.person, weekday=1, starts_at_time=time(17), duration_minutes=60)
        self.occurrence = LessonOccurrence.objects.create(series=self.series, title="Tuesday Lesson", instructor=self.person, starts_at=self._at(22, 17), ends_at=self._at(22, 18), location="Indoor")
        self.horse = Horse.objects.create(team=self.team, name="Scout")
        self.care = HorseCareRecord.objects.create(horse=self.horse, care_type=HorseCareRecord.CareType.FARRIER, title="Front shoes", performed_date=date(2026, 8, 20), next_due_date=date(2026, 9, 23))
        CalendarEvent.objects.create(team=self.team, title="Barn Meeting", kind=CalendarEvent.Kind.MEETING, starts_at=self._at(24, 19), visible_to_all=True)
        self.client.login(username="calendar-admin", password="test")

    def _at(self, day, hour):
        return timezone.make_aware(datetime(2026, 9, day, hour), timezone.get_current_timezone())

    def _get(self, **params):
        params.setdefault("month", "2026-09")
        return self.client.get(reverse("calendar"), params)

    def test_month_view_renders_native_lesson_horse_care_and_organization_event(self):
        response = self._get(view="month")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tuesday Lesson")
        self.assertContains(response, "Scout — Front shoes")
        self.assertContains(response, "Barn Meeting")
        self.assertContains(response, reverse("lesson_occurrence_detail", args=[self.occurrence.pk]))
        self.assertContains(response, reverse("horse_care_history", args=[self.horse.pk]))

    def test_agenda_view_renders_domain_labels_and_status(self):
        response = self._get(view="agenda")
        self.assertContains(response, "Barn Lesson")
        self.assertContains(response, "Farrier due")
        self.assertContains(response, self.care.due_status.title())

    def test_calendar_filter_is_grouped_by_operational_domain(self):
        response = self._get()
        self.assertContains(response, '<optgroup label="Lessons">')
        self.assertContains(response, '<optgroup label="Horses">')
        self.assertContains(response, '<optgroup label="Competition">')
        self.assertContains(response, '<optgroup label="Organization">')

    def test_horse_filter_hides_lesson_and_organization_items(self):
        response = self._get(kind="horses")
        self.assertContains(response, "Scout — Front shoes")
        self.assertNotContains(response, "Tuesday Lesson")
        self.assertNotContains(response, "Barn Meeting")

    def test_cancelled_lesson_has_visual_status_hook(self):
        self.occurrence.status = LessonOccurrence.Status.CANCELLED
        self.occurrence.save(update_fields=["status"])
        response = self._get(view="agenda", kind="barn_lesson")
        self.assertContains(response, "status-cancelled")
        self.assertContains(response, "Cancelled")
