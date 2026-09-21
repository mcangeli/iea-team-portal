from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from portal.models import Team
from portal.model_modules.horses import Horse

# Preview 1 contract tests intentionally import the new models before migration/model
# implementation. They define the v3.8.0 foundation boundary first.
from portal.model_modules.facilities import (
    Facility,
    FacilitySpace,
    HorsePastureAssignment,
    HorseStallAssignment,
    ResourceReservation,
)


class FacilityFoundationContractTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Foundation Barn")
        self.other_team = Team.objects.create(name="Other Barn")
        self.facility = Facility.objects.create(team=self.team, name="Main Farm")
        self.other_facility = Facility.objects.create(team=self.other_team, name="Other Farm")
        self.horse = Horse.objects.create(team=self.team, name="Atlas")
        self.stall = FacilitySpace.objects.create(
            facility=self.facility, name="Stall 14", space_type=FacilitySpace.SpaceType.STALL,
            housing_capable=True,
        )
        self.pasture = FacilitySpace.objects.create(
            facility=self.facility, name="North Pasture", space_type=FacilitySpace.SpaceType.PASTURE,
            turnout_capable=True,
        )
        self.ring = FacilitySpace.objects.create(
            facility=self.facility, name="Indoor Arena", space_type=FacilitySpace.SpaceType.ARENA,
            reservable=True,
        )

    def test_stall_and_pasture_are_independent_assignments(self):
        stall = HorseStallAssignment(horse=self.horse, space=self.stall, start_date=date.today())
        pasture = HorsePastureAssignment(horse=self.horse, space=self.pasture, start_date=date.today())
        stall.full_clean()
        pasture.full_clean()

    def test_pasture_board_horse_does_not_require_stall(self):
        assignment = HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, start_date=date.today()
        )
        self.assertEqual(assignment.horse, self.horse)
        self.assertFalse(HorseStallAssignment.objects.filter(horse=self.horse).exists())

    def test_assignment_capabilities_are_enforced(self):
        with self.assertRaises(ValidationError):
            HorseStallAssignment(horse=self.horse, space=self.pasture, start_date=date.today()).full_clean()
        with self.assertRaises(ValidationError):
            HorsePastureAssignment(horse=self.horse, space=self.stall, start_date=date.today()).full_clean()

    def test_cross_organization_assignment_is_rejected(self):
        other_stall = FacilitySpace.objects.create(
            facility=self.other_facility, name="Other Stall", space_type=FacilitySpace.SpaceType.STALL,
            housing_capable=True,
        )
        with self.assertRaises(ValidationError):
            HorseStallAssignment(horse=self.horse, space=other_stall, start_date=date.today()).full_clean()

    def test_end_before_start_is_rejected(self):
        with self.assertRaises(ValidationError):
            HorseStallAssignment(
                horse=self.horse, space=self.stall, start_date=date.today(),
                end_date=date.today() - timedelta(days=1),
            ).full_clean()

    def test_space_parent_must_stay_in_same_facility(self):
        other_barn = FacilitySpace.objects.create(
            facility=self.other_facility, name="Other Barn", space_type=FacilitySpace.SpaceType.BARN
        )
        child = FacilitySpace(
            facility=self.facility, parent=other_barn, name="Bad Child",
            space_type=FacilitySpace.SpaceType.STORAGE,
        )
        with self.assertRaises(ValidationError):
            child.full_clean()

    def test_space_cannot_parent_itself(self):
        space = FacilitySpace.objects.create(
            facility=self.facility, name="Feed Room", space_type=FacilitySpace.SpaceType.FEED_ROOM
        )
        space.parent = space
        with self.assertRaises(ValidationError):
            space.full_clean()

    def test_reservation_requires_reservable_space_and_valid_interval(self):
        starts = timezone.now()
        ResourceReservation(
            space=self.ring, starts_at=starts, ends_at=starts + timedelta(hours=1), title="Lesson"
        ).full_clean()
        with self.assertRaises(ValidationError):
            ResourceReservation(
                space=self.stall, starts_at=starts, ends_at=starts + timedelta(hours=1), title="Bad"
            ).full_clean()
        with self.assertRaises(ValidationError):
            ResourceReservation(
                space=self.ring, starts_at=starts, ends_at=starts, title="Bad"
            ).full_clean()
