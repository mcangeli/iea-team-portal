from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.model_modules.facilities import Facility, FacilitySpace, HorseStallAssignment
from portal.model_modules.horses import Horse
from portal.models import AuditEvent, Team, UserProfile


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
        response = self.client.get(reverse("facility_space_detail", args=[self.stall.pk]))
        self.assertContains(response, "Atlas")
        self.assertContains(response, reverse("stall_assignment_edit", args=[assignment.pk]))

    def test_ended_assignment_leaves_stall_available(self):
        HorseStallAssignment.objects.create(
            horse=self.horse, space=self.stall, start_date=date(2026, 1, 1), end_date=date(2026, 2, 1)
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_space_detail", args=[self.stall.pk]))
        self.assertContains(response, "Available")


    def test_stall_rejects_overlapping_horse_occupancy(self):
        HorseStallAssignment.objects.create(
            horse=self.horse, space=self.stall, start_date=date(2026, 9, 1)
        )
        other_horse = Horse.objects.create(team=self.team, name="Bella")
        assignment = HorseStallAssignment(
            horse=other_horse, space=self.stall, start_date=date(2026, 9, 10)
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_manager_can_vacate_current_stall(self):
        assignment = HorseStallAssignment.objects.create(
            horse=self.horse, space=self.stall, start_date=date.today()
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("stall_assignment_vacate", args=[assignment.pk]))
        assignment.refresh_from_db()
        self.assertEqual(assignment.end_date, date.today())
        self.assertIsNotNone(assignment.updated_at)
        self.assertFalse(HorseStallAssignment.objects.filter(pk=assignment.pk, end_date__isnull=True).exists())
        self.assertRedirects(response, reverse("facility_detail", args=[self.facility.pk]))

    def test_manager_can_move_horse_and_preserve_history(self):
        assignment = HorseStallAssignment.objects.create(
            horse=self.horse, space=self.stall, start_date=date(2026, 9, 1)
        )
        new_stall = FacilitySpace.objects.create(
            facility=self.facility, name="Stall 2", space_type=FacilitySpace.SpaceType.STALL,
            housing_capable=True,
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("stall_assignment_move", args=[assignment.pk]), {
            "horse": self.horse.pk, "space": new_stall.pk, "start_date": date.today(),
            "end_date": "", "notes": "",
        })
        assignment.refresh_from_db()
        self.assertEqual(assignment.end_date, date.today())
        current = HorseStallAssignment.objects.get(horse=self.horse, end_date__isnull=True)
        self.assertEqual(current.space, new_stall)
        self.assertRedirects(response, reverse("facility_detail", args=[self.facility.pk]))


    def test_vacated_today_is_hidden_from_current_housing_and_visible_in_history(self):
        assignment = HorseStallAssignment.objects.create(
            horse=self.horse, space=self.stall, start_date=date.today()
        )
        assignment.end_date = date.today()
        assignment.save()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("facility_space_detail", args=[self.stall.pk]))
        self.assertContains(response, "Available")
        self.assertContains(response, "Assignment history")


    def test_adjacent_stall_assignments_can_share_transition_date(self):
        HorseStallAssignment.objects.create(
            horse=self.horse, space=self.stall, start_date=date(2026, 9, 1), end_date=date(2026, 9, 21)
        )
        other_stall = FacilitySpace.objects.create(
            facility=self.facility, name="Stall 2", space_type=FacilitySpace.SpaceType.STALL,
            housing_capable=True,
        )
        next_assignment = HorseStallAssignment(
            horse=self.horse, space=other_stall, start_date=date(2026, 9, 21)
        )
        next_assignment.full_clean()


    def test_vacate_then_reassign_same_day_does_not_overlap(self):
        old_assignment = HorseStallAssignment.objects.create(
            horse=self.horse, space=self.stall, start_date=date.today()
        )
        new_stall = FacilitySpace.objects.create(
            facility=self.facility, name="Same Day Stall",
            space_type=FacilitySpace.SpaceType.STALL, housing_capable=True,
        )
        self.client.force_login(self.admin)
        vacate_response = self.client.post(
            reverse("stall_assignment_vacate", args=[old_assignment.pk])
        )
        self.assertEqual(vacate_response.status_code, 302)
        old_assignment.refresh_from_db()
        self.assertEqual(old_assignment.end_date, date.today())

        assign_response = self.client.post(
            reverse("stall_assignment_create", args=[self.facility.pk]),
            {
                "horse": self.horse.pk,
                "space": new_stall.pk,
                "start_date": date.today(),
                "end_date": "",
                "notes": "",
            },
        )
        self.assertEqual(assign_response.status_code, 302)
        self.assertTrue(
            HorseStallAssignment.objects.filter(
                horse=self.horse, space=new_stall,
                start_date=date.today(), end_date__isnull=True,
            ).exists()
        )


    def test_horse_profile_shows_current_housing_and_history(self):
        current = HorseStallAssignment.objects.create(
            horse=self.horse, space=self.stall, start_date=date.today()
        )
        old_stall = FacilitySpace.objects.create(
            facility=self.facility, name="Old Stall",
            space_type=FacilitySpace.SpaceType.STALL, housing_capable=True,
        )
        HorseStallAssignment.objects.create(
            horse=self.horse, space=old_stall,
            start_date=date(2026, 1, 1), end_date=date(2026, 2, 1),
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("horse_detail", args=[self.horse.pk]))
        self.assertContains(response, "Housing &amp; turnout")
        self.assertContains(response, current.space.name)
        self.assertContains(response, old_stall.name)


    def test_housing_mutations_are_audited(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("stall_assignment_create", args=[self.facility.pk]), {
            "horse": self.horse.pk, "space": self.stall.pk,
            "start_date": date.today(), "end_date": "", "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        assignment = HorseStallAssignment.objects.get(horse=self.horse)
        self.assertTrue(AuditEvent.objects.filter(
            team=self.team, entity_id=assignment.pk, action=AuditEvent.Action.CREATED
        ).exists())
        response = self.client.post(reverse("stall_assignment_vacate", args=[assignment.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditEvent.objects.filter(
            team=self.team, entity_id=assignment.pk, action=AuditEvent.Action.UPDATED,
            summary__icontains="Vacated",
        ).exists())
