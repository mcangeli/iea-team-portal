from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.facilities import Facility, FacilitySpace, ResourceReservation
from portal.model_modules.lessons import LessonOccurrence, LessonProgram, LessonSeries
from portal.models import Team, UserProfile
from portal.services.lesson_resources import (
    LESSON_OCCURRENCE_SOURCE,
    assign_lesson_resource,
    current_lesson_resource_reservation,
    release_lesson_resource,
)
from portal.services.lesson_scheduling import reschedule_lesson_occurrence


class LessonResourceSchedulingTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Lesson Resource Barn")
        self.other_team = Team.objects.create(name="Other Lesson Barn")
        self.admin = User.objects.create_user(username="lesson-resource-admin", password="pass12345")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.program = LessonProgram.objects.create(team=self.team, name="Academy")
        self.series = LessonSeries.objects.create(program=self.program, name="Tuesday Lessons")
        self.starts = timezone.now() + timedelta(days=2)
        self.occurrence = LessonOccurrence.objects.create(
            series=self.series, title="Intermediate Lesson",
            starts_at=self.starts, ends_at=self.starts + timedelta(hours=1),
        )
        self.facility = Facility.objects.create(team=self.team, name="Main Farm")
        self.indoor = FacilitySpace.objects.create(
            facility=self.facility, name="Indoor Arena",
            space_type=FacilitySpace.SpaceType.ARENA, reservable=True,
        )
        self.outdoor = FacilitySpace.objects.create(
            facility=self.facility, name="Outdoor Arena",
            space_type=FacilitySpace.SpaceType.ARENA, reservable=True,
        )

    def test_assign_resource_creates_linked_reservation(self):
        reservation = assign_lesson_resource(self.occurrence, self.indoor)
        self.occurrence.refresh_from_db()
        self.assertEqual(reservation.source_type, LESSON_OCCURRENCE_SOURCE)
        self.assertEqual(reservation.source_id, self.occurrence.pk)
        self.assertEqual(self.occurrence.location, "Indoor Arena")
        self.assertEqual(current_lesson_resource_reservation(self.occurrence), reservation)

    def test_move_indoor_to_outdoor_preserves_old_reservation(self):
        old = assign_lesson_resource(self.occurrence, self.indoor)
        new = assign_lesson_resource(self.occurrence, self.outdoor)
        old.refresh_from_db()
        self.occurrence.refresh_from_db()
        self.assertIsNotNone(old.cancelled_at)
        self.assertIsNone(new.cancelled_at)
        self.assertEqual(new.space, self.outdoor)
        self.assertEqual(self.occurrence.location, "Outdoor Arena")

    def test_failed_move_preserves_indoor_reservation(self):
        indoor_reservation = assign_lesson_resource(self.occurrence, self.indoor)
        ResourceReservation.objects.create(
            space=self.outdoor, title="Existing outdoor lesson",
            starts_at=self.occurrence.starts_at, ends_at=self.occurrence.ends_at,
        )
        with self.assertRaises(ValidationError):
            assign_lesson_resource(self.occurrence, self.outdoor)
        indoor_reservation.refresh_from_db()
        self.assertIsNone(indoor_reservation.cancelled_at)
        self.assertEqual(current_lesson_resource_reservation(self.occurrence).pk, indoor_reservation.pk)

    def test_release_resource_allows_free_text_actual_location(self):
        reservation = assign_lesson_resource(self.occurrence, self.indoor)
        release_lesson_resource(self.occurrence, location="Grass field")
        reservation.refresh_from_db()
        self.occurrence.refresh_from_db()
        self.assertIsNotNone(reservation.cancelled_at)
        self.assertIsNone(current_lesson_resource_reservation(self.occurrence))
        self.assertEqual(self.occurrence.location, "Grass field")

    def test_cross_organization_resource_is_rejected(self):
        other_facility = Facility.objects.create(team=self.other_team, name="Other Farm")
        other_ring = FacilitySpace.objects.create(
            facility=other_facility, name="Other Ring",
            space_type=FacilitySpace.SpaceType.ARENA, reservable=True,
        )
        with self.assertRaises(ValidationError):
            assign_lesson_resource(self.occurrence, other_ring)
        self.assertFalse(ResourceReservation.objects.filter(
            source_type=LESSON_OCCURRENCE_SOURCE, source_id=self.occurrence.pk
        ).exists())

    def test_reschedule_conflict_keeps_original_lesson_and_reservation_times(self):
        reservation = assign_lesson_resource(self.occurrence, self.indoor)
        original_start, original_end = self.occurrence.starts_at, self.occurrence.ends_at
        new_start = original_start + timedelta(hours=2)
        new_end = original_end + timedelta(hours=2)
        ResourceReservation.objects.create(
            space=self.indoor, title="Conflicting booking",
            starts_at=new_start, ends_at=new_end,
        )
        with self.assertRaises(ValidationError):
            reschedule_lesson_occurrence(
                self.occurrence, starts_at=new_start, ends_at=new_end
            )
        self.occurrence.refresh_from_db()
        reservation.refresh_from_db()
        self.assertEqual(self.occurrence.starts_at, original_start)
        self.assertEqual(self.occurrence.ends_at, original_end)
        self.assertEqual(reservation.starts_at, original_start)
        self.assertEqual(reservation.ends_at, original_end)

    def test_cancel_lesson_releases_resource_and_preserves_history(self):
        from portal.services.lesson_scheduling import cancel_lesson_occurrence

        reservation = assign_lesson_resource(self.occurrence, self.indoor)
        cancel_lesson_occurrence(self.occurrence, notes="Weather cancellation")
        reservation.refresh_from_db()
        self.occurrence.refresh_from_db()
        self.assertEqual(self.occurrence.status, LessonOccurrence.Status.CANCELLED)
        self.assertIsNotNone(reservation.cancelled_at)
        self.assertIsNone(current_lesson_resource_reservation(self.occurrence))
        self.assertTrue(ResourceReservation.objects.filter(pk=reservation.pk).exists())

    def test_successful_reschedule_moves_active_reservation_times(self):
        reservation = assign_lesson_resource(self.occurrence, self.indoor)
        new_start = self.occurrence.starts_at + timedelta(hours=2)
        new_end = self.occurrence.ends_at + timedelta(hours=2)
        reschedule_lesson_occurrence(self.occurrence, starts_at=new_start, ends_at=new_end)
        self.occurrence.refresh_from_db()
        reservation.refresh_from_db()
        self.assertEqual(self.occurrence.starts_at, new_start)
        self.assertEqual(self.occurrence.ends_at, new_end)
        self.assertEqual(reservation.starts_at, new_start)
        self.assertEqual(reservation.ends_at, new_end)
        self.assertIsNone(reservation.cancelled_at)

    def test_indoor_to_outdoor_history_remains_after_completion(self):
        from portal.services.lesson_completion import complete_lesson_occurrence

        indoor_reservation = assign_lesson_resource(self.occurrence, self.indoor)
        outdoor_reservation = assign_lesson_resource(self.occurrence, self.outdoor)
        indoor_reservation.refresh_from_db()
        self.assertIsNotNone(indoor_reservation.cancelled_at)
        # Completion must not erase either the historical Indoor reservation or
        # the active Outdoor reservation used for the lesson.
        complete_lesson_occurrence(self.occurrence)
        self.assertTrue(ResourceReservation.objects.filter(pk=indoor_reservation.pk).exists())
        self.assertTrue(ResourceReservation.objects.filter(pk=outdoor_reservation.pk).exists())
        outdoor_reservation.refresh_from_db()
        self.assertIsNone(outdoor_reservation.cancelled_at)

    def test_manager_can_move_resource_through_occurrence_workflow(self):
        assign_lesson_resource(self.occurrence, self.indoor)
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("lesson_occurrence_resource_assign", args=[self.occurrence.pk]),
            {"space": self.outdoor.pk},
        )
        self.assertRedirects(response, reverse("lesson_occurrence_detail", args=[self.occurrence.pk]))
        self.assertEqual(current_lesson_resource_reservation(self.occurrence).space, self.outdoor)

    def test_resource_form_does_not_offer_other_organization_spaces(self):
        other_facility = Facility.objects.create(team=self.other_team, name="Other Farm")
        other_ring = FacilitySpace.objects.create(
            facility=other_facility, name="Other Ring",
            space_type=FacilitySpace.SpaceType.ARENA, reservable=True,
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("lesson_occurrence_resource_assign", args=[self.occurrence.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Indoor Arena")
        self.assertNotContains(response, other_ring.name)
