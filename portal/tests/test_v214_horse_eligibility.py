from datetime import date

from django.test import TestCase

from portal.horse_forms import HorseShowAssignmentForm
from portal.horse_models import Horse, HorseSeasonProfile, HorseShowAssignment
from portal.models import Season, SeasonClass, Show, ShowClass, Team


class HorseShowEligibilityTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Eligibility Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
            is_active=True,
        )
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Eligibility Show",
            show_date=date(2026, 10, 10),
        )
        self.eligible_season_class = SeasonClass.objects.create(
            season=self.season,
            name="Open Flat",
            team_level=SeasonClass.TeamLevel.UPPER,
        )
        self.other_season_class = SeasonClass.objects.create(
            season=self.season,
            name="Open Fences",
            team_level=SeasonClass.TeamLevel.UPPER,
        )
        self.eligible_show_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.eligible_season_class,
            name="Open Flat",
        )
        self.other_show_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.other_season_class,
            name="Open Fences",
        )
        self.horse = Horse.objects.create(team=self.team, name="Eligible Horse")
        profile = HorseSeasonProfile.objects.create(
            horse=self.horse,
            season=self.season,
            active_for_season=True,
        )
        profile.eligible_classes.add(self.eligible_season_class)

    def _data(self, classes, override=False, reason=""):
        return {
            "horse": str(self.horse.pk),
            "available": "on",
            "show_classes": [str(item.pk) for item in classes],
            "crop_preference": "",
            "spur_preference": "",
            "lead_change": "",
            "notes": "",
            "eligibility_override": "on" if override else "",
            "eligibility_override_reason": reason,
        }

    def test_eligible_class_is_allowed_without_override(self):
        form = HorseShowAssignmentForm(
            data=self._data([self.eligible_show_class]),
            show=self.show,
            allow_eligibility_override=True,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_ineligible_class_requires_coach_admin_override(self):
        form = HorseShowAssignmentForm(
            data=self._data([self.other_show_class]),
            show=self.show,
            allow_eligibility_override=True,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("show_classes", form.errors)

    def test_override_requires_reason(self):
        form = HorseShowAssignmentForm(
            data=self._data([self.other_show_class], override=True),
            show=self.show,
            allow_eligibility_override=True,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("eligibility_override_reason", form.errors)

    def test_coach_admin_override_allows_ineligible_class_with_reason(self):
        form = HorseShowAssignmentForm(
            data=self._data([self.other_show_class], override=True, reason="Coach approved emergency substitution"),
            show=self.show,
            allow_eligibility_override=True,
        )
        self.assertTrue(form.is_valid(), form.errors)
        assignment = form.save(commit=False)
        assignment.show = self.show
        assignment.save()
        form.save_m2m()
        assignment.refresh_from_db()
        self.assertTrue(assignment.eligibility_override)
        self.assertEqual(assignment.eligibility_override_reason, "Coach approved emergency substitution")

    def test_show_lead_cannot_add_new_ineligible_class(self):
        assignment = HorseShowAssignment.objects.create(show=self.show, horse=self.horse)
        assignment.show_classes.add(self.eligible_show_class)
        form = HorseShowAssignmentForm(
            data=self._data([self.eligible_show_class, self.other_show_class]),
            instance=assignment,
            show=self.show,
            allow_eligibility_override=False,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("show_classes", form.errors)
