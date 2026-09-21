from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.facilities import Facility, FacilitySpace, HorseStallAssignment
from portal.model_modules.horses import Horse
from portal.models import Team, UserProfile


class StallHousingWorkflowTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Housing Barn")
        self.other_team = Team.objects.create(name="Other Barn")
        self.admin = User.objects.create_user(username="housing-admin", password="pass12345")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])
        self.parent = User.objects.create_user(username="housing-parent", password="pass12345")
        self.parent.profile.team = self.team
        self.parent.profile.role = UserProfile.Role.PARENT
        self.parent.profile.save(update_fields=["team", "role"])
        self.facility = Facility.objects.create(team=self.team, name="Main Farm")
        self.stall = FacilitySpace.objects.create(
            facility=self.facility, name="Stall 1", space_type=FacilitySpace.SpaceType.STALL,
            housing_capable=True,
        )
        self.horse = Horse.objects.create(team=self.team, name="Atlas")

    def test_manager_can_assign_horse_to_stall(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("stall_assignment_create", args=[self.facility.pk]), {
            "horse": self.horse.pk, "space": self.stall.pk, "start_date": date.today(), "end_date": "", "notes": "",
        })
        assignment = HorseStallAssignment.objects.get(horse=self.horse)
        self.assertEqual(assignment.space, self.stall)
        self.assertRedirects(response, reverse("facility_detail", args=[self.facility.pk]))

    def test_non_manager_cannot_assign_housing(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("stall_assignment_create", args=[self.facility.pk]))
        self.assertEqual(response.status_code, 403)

    def test_form_rejects_cross_organization_horse(self):
        other_horse = Horse.objects.create(team=self.other_team, name="Outsider")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("stall_assignment_create", args=[self.facility.pk]), {
            "horse": other_horse.pk, "space": self.stall.pk, "start_date": date.today(), "end_date": "", "notes": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HorseStallAssignment.objects.filter(horse=other_horse).exists())

    def test_facility_detail_shows_current_stall_occupancy(self):
        assignment = HorseStallAssignment.objects.create(
            horse=self.horse, space=self.stall, start_date=date.today()
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_detail", args=[self.facility.pk]))
        self.assertContains(response, "Atlas")
        self.assertContains(response, "Occupied")
        self.assertContains(response, reverse("stall_assignment_edit", args=[assignment.pk]))

    def test_ended_assignment_leaves_stall_available(self):
        HorseStallAssignment.objects.create(
            horse=self.horse, space=self.stall, start_date=date(2026, 1, 1), end_date=date(2026, 2, 1)
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_detail", args=[self.facility.pk]))
        self.assertContains(response, "Available")
