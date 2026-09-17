from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from portal.model_modules.lessons import LegacyIEALessonOccurrenceLink, LessonOccurrence
from portal.model_modules.people import LegacyPersonLink, Person
from portal.models import Lesson, LessonAttendance, LessonGroup, Rider, Season, SeasonMembership, Team
from portal.services.legacy_iea_lessons import convert_legacy_iea_lessons

class LegacyIEALessonProvenanceTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Provenance Barn")
        self.season = Season.objects.create(team=self.team, name="2026-2027", start_date=datetime(2026,8,1).date(), end_date=datetime(2027,5,31).date(), is_active=True)
        self.coach = User.objects.create_user("provenance-coach", password="test")
        self.coach.profile.team = self.team; self.coach.profile.role = "coach"; self.coach.profile.save()
        Person.objects.create(team=self.team, user=self.coach, first_name="Casey", last_name="Coach")
        self.group = LessonGroup.objects.create(season=self.season, name="Upper Tuesday", team_level=LessonGroup.TeamLevel.UPPER, coach=self.coach)
        self.rider = Rider.objects.create(team=self.team, first_name="Alex", last_name="Rider", grade=10)
        person = Person.objects.create(team=self.team, first_name="Alex", last_name="Rider"); LegacyPersonLink.objects.create(person=person, rider=self.rider)
        SeasonMembership.objects.create(rider=self.rider, season=self.season, team_level=SeasonMembership.TeamLevel.UPPER); self.group.riders.add(self.rider)
        starts = timezone.make_aware(datetime(2026,9,15,17,0))
        self.lesson = Lesson.objects.create(team=self.team, season=self.season, group=self.group, coach=self.coach, title="Upper Team Lesson", starts_at=starts, ends_at=starts+timedelta(hours=1))
        LessonAttendance.objects.create(lesson=self.lesson, rider=self.rider, status=LessonAttendance.Status.PRESENT)

    def add_futures(self):
        rider = Rider.objects.create(team=self.team, first_name="Fin", last_name="Future", grade=7)
        person = Person.objects.create(team=self.team, first_name="Fin", last_name="Future"); LegacyPersonLink.objects.create(person=person, rider=rider)
        SeasonMembership.objects.create(rider=rider, season=self.season, team_level=SeasonMembership.TeamLevel.FUTURES); self.group.riders.add(rider)
        LessonAttendance.objects.create(lesson=self.lesson, rider=rider, status=LessonAttendance.Status.EXCUSED)

    def test_apply_creates_provenance(self):
        report = convert_legacy_iea_lessons(season=self.season, dry_run=False); link = LegacyIEALessonOccurrenceLink.objects.get()
        self.assertEqual(report.provenance_created,1); self.assertEqual(link.legacy_lesson,self.lesson); self.assertEqual(link.occurrence,LessonOccurrence.objects.get())

    def test_rescheduled_occurrence_remains_idempotent(self):
        convert_legacy_iea_lessons(season=self.season, dry_run=False); occurrence=LessonOccurrence.objects.get(); moved=occurrence.starts_at+timedelta(days=1); occurrence.starts_at=moved; occurrence.save(update_fields=["starts_at"])
        report=convert_legacy_iea_lessons(season=self.season,dry_run=False)
        self.assertEqual(report.occurrences_created,0); self.assertEqual(report.provenance_existing,1); self.assertEqual(LessonOccurrence.objects.get().starts_at,moved)

    def test_pre_provenance_occurrence_is_adopted(self):
        convert_legacy_iea_lessons(season=self.season,dry_run=False); occurrence=LessonOccurrence.objects.get(); LegacyIEALessonOccurrenceLink.objects.all().delete()
        report=convert_legacy_iea_lessons(season=self.season,dry_run=False)
        self.assertEqual(report.occurrences_created,0); self.assertEqual(report.provenance_created,1); self.assertEqual(LegacyIEALessonOccurrenceLink.objects.get().occurrence,occurrence)

    def test_mixed_lesson_has_two_partition_links(self):
        self.group.team_level=LessonGroup.TeamLevel.BOTH; self.group.save(update_fields=["team_level"]); self.add_futures(); report=convert_legacy_iea_lessons(season=self.season,dry_run=False)
        links=LegacyIEALessonOccurrenceLink.objects.filter(legacy_lesson=self.lesson)
        self.assertEqual(report.provenance_created,2); self.assertEqual(links.count(),2); self.assertEqual(set(links.values_list("team_level",flat=True)),{SeasonMembership.TeamLevel.FUTURES,SeasonMembership.TeamLevel.UPPER})
