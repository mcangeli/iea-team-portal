from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.models import (
    CommitteeAssignment,
    Lesson,
    LessonGroup,
    Rider,
    Season,
    SeasonClass,
    SeasonMembership,
    Show,
    ShowClass,
    ShowEntry,
    Team,
    UserProfile,
    VolunteerLog,
)


class V199ArchivedSeasonPermissionTests(TestCase):
    """Regression coverage for legacy mutation paths that must respect archive state."""

    def setUp(self):
        self.team = Team.objects.create(name="Archive Test Team")
        self.season = Season.objects.create(
            team=self.team,
            name="2025-26",
            start_date=date(2025, 8, 1),
            end_date=date(2026, 7, 31),
            is_active=False,
            is_closed=True,
        )
        self.coach = User.objects.create_user(username="coach199", password="testpass")
        self.coach.profile.team = self.team
        self.coach.profile.role = UserProfile.Role.COACH
        self.coach.profile.save(update_fields=["team", "role"])

        self.admin = User.objects.create_user(username="admin199", password="testpass")
        self.admin.profile.team = self.team
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save(update_fields=["team", "role"])

        self.rider = Rider.objects.create(
            team=self.team, first_name="Emma", last_name="Brown"
        )
        self.season_class = SeasonClass.objects.create(
            season=self.season,
            name="Varsity Open Flat",
            team_level=SeasonClass.TeamLevel.UPPER,
        )
        self.membership = SeasonMembership.objects.create(
            rider=self.rider,
            season=self.season,
            team_level=SeasonMembership.TeamLevel.UPPER,
        )
        self.membership.classes.add(self.season_class)
        self.show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Archived Show",
            show_date=date(2025, 10, 1),
            status=Show.Status.COMPLETE,
        )
        self.show_class = ShowClass.objects.create(
            show=self.show,
            season_class=self.season_class,
            name=self.season_class.name,
        )
        self.entry = ShowEntry.objects.create(
            show_class=self.show_class,
            rider=self.rider,
            status=ShowEntry.Status.ENTERED,
        )

    def _assert_archived_forbidden(self, url, data=None):
        self.client.force_login(self.coach)
        response = self.client.post(url, data or {})
        self.assertEqual(response.status_code, 403)

    def test_show_edit_delete_and_structure_are_protected(self):
        self._assert_archived_forbidden(reverse("show_edit", args=[self.show.pk]))
        self._assert_archived_forbidden(reverse("show_delete", args=[self.show.pk]))
        self._assert_archived_forbidden(reverse("show_class_create", args=[self.show.pk]))
        self._assert_archived_forbidden(reverse("show_class_edit", args=[self.show_class.pk]))
        self._assert_archived_forbidden(reverse("show_class_delete", args=[self.show_class.pk]))
        self._assert_archived_forbidden(reverse("show_entry_edit", args=[self.entry.pk]))
        self._assert_archived_forbidden(reverse("show_entry_delete", args=[self.entry.pk]))
        self._assert_archived_forbidden(reverse("point_rider_set", args=[self.entry.pk]))

    def test_season_class_edit_is_protected(self):
        self._assert_archived_forbidden(
            reverse("season_class_edit", args=[self.season_class.pk])
        )

    def test_lesson_and_attendance_mutations_are_protected(self):
        group = LessonGroup.objects.create(
            season=self.season,
            name="Archived Group",
        )
        lesson = Lesson.objects.create(
            team=self.team,
            season=self.season,
            group=group,
            title="Archived Lesson",
            starts_at="2025-10-02T16:00:00Z",
        )
        self._assert_archived_forbidden(reverse("lesson_group_edit", args=[group.pk]))
        self._assert_archived_forbidden(reverse("lesson_edit", args=[lesson.pk]))
        self._assert_archived_forbidden(reverse("lesson_delete", args=[lesson.pk]))

    def test_committee_assignment_edit_is_protected(self):
        assignment = CommitteeAssignment.objects.create(
            team=self.team,
            season=self.season,
            user=self.coach,
            role=CommitteeAssignment.Role.POINTS_SECRETARY,
            active=True,
        )
        self._assert_archived_forbidden(
            reverse("committee_assignment_edit", args=[assignment.pk])
        )

    def test_admin_can_reopen_but_coach_cannot(self):
        self.client.force_login(self.coach)
        response = self.client.post(reverse("season_reopen", args=[self.season.pk]))
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.admin)
        response = self.client.post(reverse("season_reopen", args=[self.season.pk]))
        self.assertRedirects(response, reverse("season_review", args=[self.season.pk]))
        self.season.refresh_from_db()
        self.assertFalse(self.season.is_closed)
        self.assertFalse(self.season.is_active)
