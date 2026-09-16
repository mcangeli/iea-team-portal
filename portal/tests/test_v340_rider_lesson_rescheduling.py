from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.lessons import LessonAttendanceRecord, LessonEnrollment, LessonParticipantMove, LessonProgram, LessonSeries
from portal.model_modules.people import OrganizationRoleAssignment, Person
from portal.models import Team
from portal.services.lesson_preparation import prepare_lesson_occurrence
from portal.services.lesson_scheduling import generate_lesson_occurrences


class RiderLessonReschedulingTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Self Service Barn")
        self.user = User.objects.create_user("avery", password="test")
        self.user.profile.team = self.team; self.user.profile.role = "rider"; self.user.profile.save()
        self.rider = Person.objects.create(team=self.team, user=self.user, first_name="Avery", last_name="Rider")
        OrganizationRoleAssignment.objects.create(team=self.team, person=self.rider, role=OrganizationRoleAssignment.Role.RIDER)
        self.program = LessonProgram.objects.create(team=self.team, name="Barn Lessons")
        self.series = LessonSeries.objects.create(program=self.program, name="Tuesday", weekday=1, starts_at_time=time(17), duration_minutes=60, capacity=4, start_date=date(2026,9,1), end_date=date(2026,10,31))
        LessonEnrollment.objects.create(series=self.series, person=self.rider)
        generated = generate_lesson_occurrences(self.series, date(2026,9,22), date(2026,10,6)).created
        self.source, self.destination, self.other_occurrence = generated[0], generated[1], generated[2]
        prepare_lesson_occurrence(self.source)
        self.client.force_login(self.user)

    def test_rider_sees_only_own_upcoming_lessons(self):
        response = self.client.get(reverse("my_lessons"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.source.title)
        self.assertContains(response, "Reschedule / Make-up")

    def test_rider_can_reschedule_self(self):
        response = self.client.post(reverse("my_lesson_reschedule", args=[self.source.pk]), {"destination_occurrence": self.destination.pk, "reason": "School event"}, follow=True)
        self.assertEqual(response.status_code, 200)
        move = LessonParticipantMove.objects.get(person=self.rider)
        self.assertEqual(move.initiated_by, LessonParticipantMove.Initiator.RIDER)
        self.assertEqual(move.initiated_by_user, self.user)
        self.assertEqual(LessonAttendanceRecord.objects.get(occurrence=self.destination, person=self.rider).status, LessonAttendanceRecord.Status.MAKEUP)

    def test_my_lessons_shows_reschedule_provenance(self):
        self.client.post(reverse("my_lesson_reschedule", args=[self.source.pk]), {"destination_occurrence": self.destination.pk, "reason": "School event"})
        response = self.client.get(reverse("my_lessons"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rescheduled:")
        self.assertContains(response, "Make-up:")
        self.assertContains(response, "School event")
        self.assertContains(response, self.destination.starts_at.strftime("%b").replace("Sep", "Sep"))

    def test_rescheduled_source_no_longer_offers_reschedule_action(self):
        self.client.post(reverse("my_lesson_reschedule", args=[self.source.pk]), {"destination_occurrence": self.destination.pk})
        response = self.client.get(reverse("my_lessons"))
        source_row = next(row for row in response.context["schedule"] if row["attendance"].occurrence_id == self.source.pk)
        self.assertIsNotNone(source_row["moved_to"])
        response = self.client.get(reverse("my_lesson_reschedule", args=[self.source.pk]))
        self.assertEqual(response.status_code, 403)

    def test_prepared_expected_destination_is_available_to_rider(self):
        prepare_lesson_occurrence(self.destination)
        attendance = LessonAttendanceRecord.objects.get(occurrence=self.destination, person=self.rider)
        self.assertEqual(attendance.status, LessonAttendanceRecord.Status.EXPECTED)
        response = self.client.get(reverse("my_lesson_reschedule", args=[self.source.pk]))
        self.assertContains(response, f'value="{self.destination.pk}"')

    def test_rider_cannot_reschedule_someone_elses_lesson(self):
        other_user = User.objects.create_user("blake", password="test")
        other = Person.objects.create(team=self.team, user=other_user, first_name="Blake", last_name="Rider")
        OrganizationRoleAssignment.objects.create(team=self.team, person=other, role=OrganizationRoleAssignment.Role.RIDER)
        LessonAttendanceRecord.objects.create(occurrence=self.other_occurrence, person=other)
        response = self.client.get(reverse("my_lesson_reschedule", args=[self.other_occurrence.pk]))
        self.assertEqual(response.status_code, 404)

    def test_non_rider_person_cannot_use_my_lessons(self):
        self.rider.role_assignments.all().delete()
        response = self.client.get(reverse("my_lessons"))
        self.assertEqual(response.status_code, 403)

    def test_full_destination_is_not_offered(self):
        self.destination.capacity = 1; self.destination.save()
        other = Person.objects.create(team=self.team, first_name="Blake", last_name="Rider")
        LessonAttendanceRecord.objects.create(occurrence=self.destination, person=other)
        response = self.client.get(reverse("my_lesson_reschedule", args=[self.source.pk]))
        self.assertNotContains(response, f'value="{self.destination.pk}"')
