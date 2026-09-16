from datetime import date, datetime, time

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone

from portal.model_modules.equine_care import HorseCareRecord
from portal.model_modules.equine_documents import HorseDocument
from portal.model_modules.horses import Horse, HorseCogginsRecord
from portal.model_modules.lessons import IEALessonSeriesContext, LessonOccurrence, LessonProgram, LessonSeries
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import CalendarEvent, Lesson, LessonGroup, Season, SeasonClass, SeasonMembership, Show, ShowClass, Team
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
        self.assertEqual({item.title for item in self._items()}, {"Barn Tuesday", "Upper Team", "Parent Meeting"})

    def test_native_lessons_route_to_occurrence_workspace(self):
        native = [item for item in self._items(selected_kind="lessons") if item.source == "lesson_occurrence"]
        self.assertEqual(len(native), 2)
        self.assertTrue(all("lesson-occurrences" in item.url for item in native))

    def test_lesson_filter_distinguishes_barn_and_iea(self):
        self.assertEqual([item.title for item in self._items(selected_kind="barn_lesson")], ["Barn Tuesday"])
        self.assertEqual([item.title for item in self._items(selected_kind="iea_lesson")], ["Upper Team"])

    def test_iea_team_filter_excludes_organization_wide_barn_lessons(self):
        upper = self._items(selected_team=SeasonMembership.TeamLevel.UPPER)
        self.assertIn("Upper Team", [item.title for item in upper])
        self.assertNotIn("Barn Tuesday", [item.title for item in upper])

    def test_cancelled_lesson_remains_visible_with_status(self):
        self.barn_occurrence.status = LessonOccurrence.Status.CANCELLED; self.barn_occurrence.save(update_fields=["status"])
        self.assertEqual(self._items(selected_kind="barn_lesson")[0].status, LessonOccurrence.Status.CANCELLED)

    def test_unconverted_legacy_lesson_remains_visible(self):
        group = LessonGroup.objects.create(season=self.season, name="Legacy Futures", team_level=SeasonMembership.TeamLevel.FUTURES)
        lesson = Lesson.objects.create(team=self.team, season=self.season, group=group, title="Legacy Lesson", starts_at=self._at(23, 17))
        CalendarEvent.objects.create(team=self.team, lesson=lesson, title="Legacy Lesson", kind=CalendarEvent.Kind.LESSON, starts_at=lesson.starts_at)
        item = next(item for item in self._items(selected_kind="lessons") if item.title == "Legacy Lesson")
        self.assertEqual(item.kind, "legacy_lesson")

    def test_horse_care_due_date_projects_as_all_day_item(self):
        horse = Horse.objects.create(team=self.team, name="Scout")
        record = HorseCareRecord.objects.create(horse=horse, care_type=HorseCareRecord.CareType.FARRIER, title="Front shoes", performed_date=date(2026, 8, 20), next_due_date=date(2026, 9, 28))
        item = self._items(selected_kind="horse_care")[0]
        self.assertEqual(item.source_id, record.pk); self.assertTrue(item.all_day); self.assertEqual(item.kind_label, "Farrier due")

    def test_coggins_expiration_projects_from_authoritative_record(self):
        horse = Horse.objects.create(team=self.team, name="Scout")
        record = HorseCogginsRecord.objects.create(horse=horse, test_date=date(2025, 9, 29), expiration_date=date(2026, 9, 29))
        item = self._items(selected_kind="coggins")[0]
        self.assertEqual(item.source_id, record.pk); self.assertEqual(item.title, "Scout — Coggins expires"); self.assertTrue(item.all_day)

    def test_document_expiration_projects_without_copying_document(self):
        horse = Horse.objects.create(team=self.team, name="Scout")
        document = HorseDocument(horse=horse, document_type=HorseDocument.DocumentType.INSURANCE, title="Insurance", effective_date=date(2026, 1, 1), expiration_date=date(2026, 9, 30))
        document.file.save("insurance.txt", ContentFile(b"test"), save=True)
        item = self._items(selected_kind="horse_document")[0]
        self.assertEqual(item.source_id, document.pk); self.assertEqual(item.source, "horse_document"); self.assertTrue(item.all_day)

    def test_horse_filter_collects_all_horse_calendar_sources(self):
        horse = Horse.objects.create(team=self.team, name="Scout")
        HorseCareRecord.objects.create(horse=horse, care_type=HorseCareRecord.CareType.DENTAL, title="Dental float", performed_date=date(2026, 8, 1), next_due_date=date(2026, 9, 26))
        HorseCogginsRecord.objects.create(horse=horse, test_date=date(2025, 9, 27), expiration_date=date(2026, 9, 27))
        self.assertEqual({item.kind for item in self._items(selected_kind="horses")}, {"horse_care", "coggins"})

    def test_show_team_filter_uses_show_class_team_level(self):
        show = Show.objects.create(team=self.team, season=self.season, name="September Show", show_date=date(2026, 9, 26))
        futures_class = SeasonClass.objects.create(season=self.season, name="Future Beginner", team_level=SeasonClass.TeamLevel.FUTURES)
        ShowClass.objects.create(show=show, season_class=futures_class, name=futures_class.name)
        CalendarEvent.objects.create(team=self.team, show=show, title=show.name, kind=CalendarEvent.Kind.SHOW, starts_at=self._at(26, 8))
        self.assertIn("September Show", [item.title for item in self._items(selected_team=SeasonMembership.TeamLevel.FUTURES)])
        self.assertNotIn("September Show", [item.title for item in self._items(selected_team=SeasonMembership.TeamLevel.UPPER)])
