from datetime import date, datetime, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from portal.model_modules.lessons import IEALessonSeriesContext, LessonOccurrence, LessonProgram, LessonSeries
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import CalendarEvent, Season, SeasonMembership, Team
from portal.services.calendar_items_v340 import calendar_items


class UnifiedCalendarItemTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Calendar Barn")
        self.trainer = self._person("trainer", person_role=OrganizationRoleAssignment.Role.TRAINER)
        self.coach = self._person("coach", profile_role="coach")
        self.barn_program = LessonProgram.objects.create(team=self.team, name="Barn Lessons")
        self.barn_series = LessonSeries.objects.create(program=self.barn_program, name="Barn Tuesday", instructor=self.trainer, weekday=1, starts_at_time=time(17), duration_minutes=60)
        self.iea_program = LessonProgram.objects.create(team=self.team, name="IEA Team Lessons")
        self.iea_series = LessonSeries.objects.create(program=self.iea_program, name="Upper Team", instructor=self.coach, weekday=3, starts_at_time=time(18), duration_minutes=60)
        self.season = Season.objects.create(team=self.team, name="2026 IEA", start_date=date(2026, 8, 1), end_date=date(2027, 5, 31), is_active=True)
        IEALessonSeriesContext.objects.create(series=self.iea_series, season=self.season, team_level=SeasonMembership.TeamLevel.UPPER)
        self.barn_occurrence = LessonOccurrence.objects.create(series=self.barn_series, title="Barn Tuesday", instructor=self.trainer, starts_at=self._at(22, 17), ends_at=self._at(22, 18), location="Indoor")
        self.iea_occurrence = LessonOccurrence.objects.create(series=self.iea_series, title="Upper Team", instructor=self.coach, starts_at=self._at(24, 18), ends_at=self._at(24, 19), location="Main Ring")
        self.meeting = CalendarEvent.objects.create(team=self.team, title="Parent Meeting", kind=CalendarEvent.Kind.MEETING, starts_at=self._at(25, 19))

    def _person(self, username, profile_role="rider", person_role=None):
        user = User.objects.create_user(username)
        user.profile.team = self.team; user.profile.role = profile_role; user.profile.save()
        person = Person.objects.create(team=self.team, user=user, first_name=username.title(), last_name="User")
        if person_role:
            OrganizationRoleAssignment.objects.create(team=self.team, person=person, role=person_role)
        return person

    def _at(self, day, hour):
        return timezone.make_aware(datetime(2026, 9, day, hour), timezone.get_current_timezone())

    def _items(self, **kwargs):
        return calendar_items(self.team, self._at(1, 0), timezone.make_aware(datetime(2026, 10, 1, 0), timezone.get_current_timezone()), include_private=True, **kwargs)

    def test_calendar_aggregates_manual_and_native_lesson_items(self):
        items = self._items()
        self.assertEqual({item.title for item in items}, {"Barn Tuesday", "Upper Team", "Parent Meeting"})

    def test_native_lessons_route_to_occurrence_workspace(self):
        items = self._items(selected_kind="lessons")
        self.assertEqual({item.source for item in items}, {"lesson_occurrence"})
        self.assertTrue(all("lesson-occurrences" in item.url for item in items))

    def test_lesson_filter_distinguishes_barn_and_iea(self):
        self.assertEqual([item.title for item in self._items(selected_kind="barn_lesson")], ["Barn Tuesday"])
        self.assertEqual([item.title for item in self._items(selected_kind="iea_lesson")], ["Upper Team"])

    def test_iea_team_filter_excludes_organization_wide_barn_lessons(self):
        upper = self._items(selected_team=SeasonMembership.TeamLevel.UPPER)
        self.assertIn("Upper Team", [item.title for item in upper])
        self.assertNotIn("Barn Tuesday", [item.title for item in upper])

    def test_cancelled_lesson_remains_visible_with_status(self):
        self.barn_occurrence.status = LessonOccurrence.Status.CANCELLED
        self.barn_occurrence.save(update_fields=["status"])
        item = self._items(selected_kind="barn_lesson")[0]
        self.assertEqual(item.status, LessonOccurrence.Status.CANCELLED)

    def test_legacy_calendar_lesson_is_not_duplicated_into_unified_stream(self):
        CalendarEvent.objects.create(team=self.team, title="Legacy Lesson", kind=CalendarEvent.Kind.LESSON, starts_at=self._at(23, 17))
        self.assertNotIn("Legacy Lesson", [item.title for item in self._items()])
