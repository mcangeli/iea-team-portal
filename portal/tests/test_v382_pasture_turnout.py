from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.facilities import Facility, FacilitySpace, HorsePastureAssignment, HorseStallAssignment
from portal.model_modules.horses import Horse
from portal.models import Team, UserProfile


class PastureTurnoutWorkflowTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Turnout Barn")
        self.other_team = Team.objects.create(name="Other Barn")
        self.admin = User.objects.create_user(username="turnout-admin", password="pass12345")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.parent = User.objects.create_user(username="turnout-parent", password="pass12345")
        self.parent.profile.team = self.team
        self.parent.profile.role = UserProfile.Role.PARENT
        self.parent.profile.save(update_fields=["team", "role"])
        self.facility = Facility.objects.create(team=self.team, name="Main Farm")
        self.pasture = FacilitySpace.objects.create(
            facility=self.facility, name="Mares Pasture", space_type=FacilitySpace.SpaceType.PASTURE,
            turnout_capable=True,
        )
        self.stall = FacilitySpace.objects.create(
            facility=self.facility, name="Stall 1", space_type=FacilitySpace.SpaceType.STALL,
            housing_capable=True,
        )
        self.horse = Horse.objects.create(team=self.team, name="Atlas")

    def test_manager_can_assign_primary_turnout(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("pasture_assignment_create", args=[self.facility.pk]), {
            "horse": self.horse.pk, "space": self.pasture.pk, "turnout_type": "primary",
            "start_date": date.today(), "end_date": "", "notes": "",
        })
        assignment = HorsePastureAssignment.objects.get(horse=self.horse)
        self.assertEqual(assignment.space, self.pasture)
        self.assertEqual(assignment.turnout_type, HorsePastureAssignment.TurnoutType.PRIMARY)
        self.assertRedirects(response, reverse("facility_detail", args=[self.facility.pk]))

    def test_turnout_is_independent_from_stall_housing(self):
        HorseStallAssignment.objects.create(horse=self.horse, space=self.stall, start_date=date.today())
        turnout = HorsePastureAssignment(horse=self.horse, space=self.pasture, start_date=date.today())
        turnout.full_clean()

    def test_primary_turnout_rejects_overlap_for_same_horse(self):
        HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, turnout_type="primary", start_date=date(2026, 9, 1)
        )
        other = FacilitySpace.objects.create(
            facility=self.facility, name="North Paddock", space_type=FacilitySpace.SpaceType.PASTURE,
            turnout_capable=True,
        )
        assignment = HorsePastureAssignment(
            horse=self.horse, space=other, turnout_type="primary", start_date=date(2026, 9, 10)
        )
        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_temporary_turnout_can_coexist_with_primary(self):
        HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, turnout_type="primary", start_date=date.today()
        )
        temporary = HorsePastureAssignment(
            horse=self.horse, space=self.pasture, turnout_type="temporary", start_date=date.today()
        )
        temporary.full_clean()

    def test_non_manager_cannot_assign_turnout(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("pasture_assignment_create", args=[self.facility.pk]))
        self.assertEqual(response.status_code, 403)

    def test_turnout_form_rejects_cross_organization_horse(self):
        other_horse = Horse.objects.create(team=self.other_team, name="Outsider")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("pasture_assignment_create", args=[self.facility.pk]), {
            "horse": other_horse.pk, "space": self.pasture.pk, "turnout_type": "primary",
            "start_date": date.today(), "end_date": "", "notes": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HorsePastureAssignment.objects.filter(horse=other_horse).exists())


    def test_facility_detail_shows_current_turnout_and_edit_link(self):
        assignment = HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, turnout_type="primary", start_date=date.today()
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_detail", args=[self.facility.pk]))
        self.assertContains(response, "Atlas")
        self.assertContains(response, "Primary")
        self.assertContains(response, reverse("pasture_assignment_edit", args=[assignment.pk]))

    def test_manager_can_edit_turnout_assignment(self):
        assignment = HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, turnout_type="primary", start_date=date.today()
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("pasture_assignment_edit", args=[assignment.pk]), {
            "horse": self.horse.pk, "space": self.pasture.pk, "turnout_type": "temporary",
            "start_date": date.today(), "end_date": "", "notes": "Short turnout",
        })
        assignment.refresh_from_db()
        self.assertEqual(assignment.turnout_type, HorsePastureAssignment.TurnoutType.TEMPORARY)
        self.assertEqual(assignment.notes, "Short turnout")
        self.assertRedirects(response, reverse("facility_detail", args=[self.facility.pk]))


    def test_manager_can_end_current_turnout(self):
        assignment = HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, turnout_type="primary", start_date=date.today()
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("pasture_assignment_end", args=[assignment.pk]))
        assignment.refresh_from_db()
        self.assertEqual(assignment.end_date, date.today())
        self.assertFalse(HorsePastureAssignment.objects.filter(pk=assignment.pk, end_date__isnull=True).exists())
        self.assertRedirects(response, reverse("facility_detail", args=[self.facility.pk]))


    def test_dated_current_turnout_is_visible_and_editable(self):
        assignment = HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, turnout_type="primary",
            start_date=date.today() - timedelta(days=7), end_date=date.today() + timedelta(days=7),
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_detail", args=[self.facility.pk]))
        self.assertContains(response, "Atlas")
        self.assertContains(response, reverse("pasture_assignment_edit", args=[assignment.pk]))


    def test_manager_can_move_primary_turnout_and_preserve_history(self):
        old = HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, turnout_type="primary",
            start_date=date.today(),
        )
        north = FacilitySpace.objects.create(
            facility=self.facility, name="North Paddock",
            space_type=FacilitySpace.SpaceType.PASTURE, turnout_capable=True,
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("pasture_assignment_move", args=[old.pk]), {
            "horse": self.horse.pk, "space": north.pk, "turnout_type": "primary",
            "start_date": date.today(), "end_date": "", "notes": "",
        })
        old.refresh_from_db()
        self.assertEqual(old.end_date, date.today())
        self.assertTrue(HorsePastureAssignment.objects.filter(
            horse=self.horse, space=north, turnout_type="primary", end_date__isnull=True
        ).exists())
        self.assertRedirects(response, reverse("facility_detail", args=[self.facility.pk]))

    def test_completed_turnout_appears_in_facility_history(self):
        assignment = HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, turnout_type="primary",
            start_date=date(2026, 8, 1), end_date=date(2026, 8, 31),
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_detail", args=[self.facility.pk]))
        self.assertContains(response, "Recent assignments")
        self.assertContains(response, reverse("pasture_assignment_edit", args=[assignment.pk]))


    def test_manager_can_end_dated_current_turnout(self):
        assignment = HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, turnout_type="primary",
            start_date=date.today() - timedelta(days=7), end_date=date.today() + timedelta(days=7),
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("pasture_assignment_end", args=[assignment.pk]))
        assignment.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(assignment.end_date, date.today())


    def test_ended_today_is_hidden_from_current_turnout_and_visible_in_history(self):
        assignment = HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, turnout_type="primary", start_date=date.today()
        )
        assignment.end_date = date.today()
        assignment.save()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_detail", args=[self.facility.pk]))
        self.assertContains(response, "No current turnout assignments.")
        self.assertContains(response, "Recent assignments")
        self.assertContains(response, reverse("pasture_assignment_edit", args=[assignment.pk]))


    def test_adjacent_primary_turnout_can_share_transition_date(self):
        HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, turnout_type="primary",
            start_date=date(2026, 9, 1), end_date=date(2026, 9, 21),
        )
        north = FacilitySpace.objects.create(
            facility=self.facility, name="North Paddock",
            space_type=FacilitySpace.SpaceType.PASTURE, turnout_capable=True,
        )
        next_assignment = HorsePastureAssignment(
            horse=self.horse, space=north, turnout_type="primary", start_date=date(2026, 9, 21)
        )
        next_assignment.full_clean()


    def test_horse_profile_shows_current_turnout_and_history(self):
        HorsePastureAssignment.objects.create(
            horse=self.horse, space=self.pasture, turnout_type="primary",
            start_date=date.today(),
        )
        old = FacilitySpace.objects.create(
            facility=self.facility, name="Old Paddock",
            space_type=FacilitySpace.SpaceType.PASTURE, turnout_capable=True,
        )
        HorsePastureAssignment.objects.create(
            horse=self.horse, space=old, turnout_type="primary",
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() - timedelta(days=7),
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertContains(response, "Housing &amp; turnout")
        self.assertContains(response, self.pasture.name)
        self.assertContains(response, old.name)
