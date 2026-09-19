from datetime import date, datetime, timezone as dt_timezone

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.horses import Horse
from portal.model_modules.lessons import IEALessonOccurrenceParticipant, LessonAssignment, LessonOccurrence
from portal.model_modules.people import LegacyPersonLink, Person
from portal.models import Rider, Season, SeasonMembership, Team


class IEALessonOccurrenceSchedulingTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Flexible IEA Barn")
        self.admin = User.objects.create_superuser("scheduler", "scheduler@example.com", "test")
        self.admin.profile.team = self.team
        self.admin.profile.role = "admin"
        self.admin.profile.save()
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.client.force_login(self.admin)

    def _member(self, first, last, level):
        rider = Rider.objects.create(team=self.team, first_name=first, last_name=last)
        person = Person.objects.create(team=self.team, first_name=first, last_name=last)
        LegacyPersonLink.objects.create(person=person, rider=rider)
        SeasonMembership.objects.create(rider=rider, season=self.season, team_level=level)
        return person

    def _payload(self, participants):
        return {
            "title": "September Team Lesson",
            "starts_at": "2026-09-26T14:00",
            "ends_at": "2026-09-26T15:00",
            "instructor": "",
            "location": "Main Arena",
            "capacity": "8",
            "notes": "",
            "participants": [str(person.pk) for person in participants],
        }

    def test_schedule_occurrence_can_mix_futures_and_upper(self):
        futures = self._member("Finn", "Future", "futures")
        upper = self._member("Uma", "Upper", "upper")
        response = self.client.post(
            reverse("iea_lesson_occurrence_create"),
            self._payload([futures, upper]),
        )
        self.assertEqual(response.status_code, 302)
        occurrence = LessonOccurrence.objects.get(title="September Team Lesson")
        self.assertTrue(occurrence.iea_roster_configured)
        self.assertEqual(occurrence.series.iea_context.team_level, "mixed")
        self.assertSetEqual(
            set(occurrence.iea_participants.values_list("person_id", flat=True)),
            {futures.pk, upper.pk},
        )

    def test_schedule_occurrence_allows_intentionally_empty_roster(self):
        self._member("Uma", "Upper", "upper")
        response = self.client.post(reverse("iea_lesson_occurrence_create"), self._payload([]))
        self.assertEqual(response.status_code, 302)
        occurrence = LessonOccurrence.objects.get(title="September Team Lesson")
        self.assertTrue(occurrence.iea_roster_configured)
        self.assertEqual(occurrence.iea_participants.count(), 0)

    def test_schedule_form_only_offers_active_season_members(self):
        eligible = self._member("Eli", "Eligible", "upper")
        outsider = Person.objects.create(team=self.team, first_name="Not", last_name="Eligible")
        response = self.client.get(reverse("iea_lesson_occurrence_create"))
        self.assertContains(response, eligible.display_name)
        self.assertNotContains(response, outsider.display_name)

    def test_occurrence_rosters_are_independent(self):
        first = self._member("First", "Rider", "futures")
        second = self._member("Second", "Rider", "upper")
        self.client.post(reverse("iea_lesson_occurrence_create"), self._payload([first]))
        first_occurrence = LessonOccurrence.objects.get(title="September Team Lesson")
        payload = self._payload([second])
        payload["title"] = "October Team Lesson"
        payload["starts_at"] = "2026-10-03T14:00"
        payload["ends_at"] = "2026-10-03T15:00"
        self.client.post(reverse("iea_lesson_occurrence_create"), payload)
        second_occurrence = LessonOccurrence.objects.get(title="October Team Lesson")
        self.assertSetEqual(set(first_occurrence.iea_participants.values_list("person_id", flat=True)), {first.pk})
        self.assertSetEqual(set(second_occurrence.iea_participants.values_list("person_id", flat=True)), {second.pk})


    def test_schedule_another_does_not_copy_roster_by_default(self):
        rider = self._member("Repeat", "Rider", "upper")
        self.client.post(reverse("iea_lesson_occurrence_create"), self._payload([rider]))
        source = LessonOccurrence.objects.get(title="September Team Lesson")
        response = self.client.get(reverse("iea_lesson_occurrence_duplicate", args=[source.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(rider.pk, list(response.context["form"].fields["participants"].initial or []))

    def test_schedule_another_can_explicitly_copy_roster(self):
        rider = self._member("Repeat", "Rider", "upper")
        self.client.post(reverse("iea_lesson_occurrence_create"), self._payload([rider]))
        source = LessonOccurrence.objects.get(title="September Team Lesson")
        response = self.client.get(
            reverse("iea_lesson_occurrence_duplicate", args=[source.pk]) + "?copy_roster=1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(rider.pk, list(response.context["form"].initial["participants"]))

    def test_scheduling_can_plan_horse_assignments(self):
        rider = self._member("Horse", "Planner", "futures")
        horse = Horse.objects.create(team=self.team, name="Scout")
        payload = self._payload([rider])
        payload["horses"] = [str(horse.pk)]
        response = self.client.post(reverse("iea_lesson_occurrence_create"), payload)
        self.assertEqual(response.status_code, 302)
        occurrence = LessonOccurrence.objects.get(title="September Team Lesson")
        assignment = LessonAssignment.objects.get(
            occurrence=occurrence, person=rider, role=LessonAssignment.Role.PARTICIPANT
        )
        self.assertEqual(assignment.horse, horse)


    def test_team_lesson_list_month_view_shows_occurrence_and_navigation(self):
        rider = self._member("Month", "Rider", "futures")
        self.client.post(reverse("iea_lesson_occurrence_create"), self._payload([rider]))
        response = self.client.get(reverse("iea_lesson_list") + "?month=2026-09")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "September 2026")
        self.assertContains(response, "September Team Lesson")
        self.assertContains(response, "1")
        self.assertEqual(response.context["month_cursor"], date(2026, 9, 1))

    def test_team_lesson_list_month_view_excludes_other_months(self):
        rider = self._member("Month", "Rider", "upper")
        self.client.post(reverse("iea_lesson_occurrence_create"), self._payload([rider]))
        response = self.client.get(reverse("iea_lesson_list") + "?month=2026-10")
        self.assertEqual(response.status_code, 200)
        titles = [occurrence.title for occurrence in response.context["month_occurrences"]]
        self.assertNotIn("September Team Lesson", titles)
