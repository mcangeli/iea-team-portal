from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.lessons import LessonAttendanceRecord, LessonEnrollment, LessonParticipantMove, LessonProgram, LessonSeries
from portal.model_modules.people import Person
from portal.models import Team
from portal.services.lesson_preparation import prepare_lesson_occurrence
from portal.services.lesson_scheduling import generate_lesson_occurrences


class LessonParticipantMoveUITests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Scheduling Barn")
        self.admin = User.objects.create_superuser("scheduleadmin", "schedule@example.com", "test")
        self.admin.profile.team = self.team
        self.admin.profile.role = "admin"
        self.admin.profile.save()
        self.rider = Person.objects.create(team=self.team, first_name="Avery", last_name="Rider")
        self.program = LessonProgram.objects.create(team=self.team, name="Barn Lessons")
        self.series = LessonSeries.objects.create(program=self.program, name="Tuesday Group", weekday=1, starts_at_time=time(17), duration_minutes=60, start_date=date(2026, 9, 1), end_date=date(2026, 10, 31))
        LessonEnrollment.objects.create(series=self.series, person=self.rider)
        generated = generate_lesson_occurrences(self.series, date(2026, 9, 22), date(2026, 9, 29)).created
        self.source, self.destination = generated[0], generated[1]
        prepare_lesson_occurrence(self.source)
        self.client.force_login(self.admin)

    def test_lesson_day_exposes_move_makeup_action(self):
        response = self.client.get(reverse("lesson_day_workspace", args=[self.source.pk]))
        self.assertContains(response, "Move / Make-up")
        self.assertContains(response, reverse("lesson_participant_move", args=[self.source.pk, self.rider.pk]))

    def test_move_screen_lists_eligible_upcoming_lesson(self):
        response = self.client.get(reverse("lesson_participant_move", args=[self.source.pk, self.rider.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose another lesson")
        self.assertContains(response, self.destination.title)
        self.assertContains(response, "Trainer / Assistant Trainer")

    def test_makeup_post_records_history_and_returns_to_lesson(self):
        response = self.client.post(reverse("lesson_participant_move", args=[self.source.pk, self.rider.pk]), {
            "destination_occurrence": str(self.destination.pk),
            "kind": LessonParticipantMove.Kind.MAKEUP,
            "source_status": LessonAttendanceRecord.Status.EXCUSED,
            "reason": "School event",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "make-up scheduled")
        move = LessonParticipantMove.objects.get(person=self.rider)
        self.assertEqual(move.source_occurrence, self.source)
        self.assertEqual(move.destination_occurrence, self.destination)
        self.assertEqual(LessonAttendanceRecord.objects.get(occurrence=self.destination, person=self.rider).status, LessonAttendanceRecord.Status.MAKEUP)

    def test_rider_already_on_destination_is_not_offered(self):
        prepare_lesson_occurrence(self.destination)
        response = self.client.get(reverse("lesson_participant_move", args=[self.source.pk, self.rider.pk]))
        self.assertNotContains(response, f'value="{self.destination.pk}"')
