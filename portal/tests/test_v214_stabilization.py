import tempfile
from datetime import date

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from portal.course_forms import ShowCourseMediaForm
from portal.course_models import ShowCourse
from portal.hoofprint_models import ShowHorseListDocument
from portal.horse_models import Horse, HorseShowAssignment, HorseShowAward
from portal.models import Season, Show, ShowLeadAssignment, ShowPlanningItem, Team, UserProfile


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class V214StabilizationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Stabilization Team")
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
            name="Fall Invitational",
            show_date=date(2026, 10, 10),
        )
        self.other_show = Show.objects.create(
            team=self.team,
            season=self.season,
            name="Winter Invitational",
            show_date=date(2026, 12, 5),
        )

        self.coach = self.make_user("coach214", UserProfile.Role.COACH)
        self.show_lead = self.make_user("lead214", UserProfile.Role.PARENT)
        self.other_lead = self.make_user("otherlead214", UserProfile.Role.PARENT)
        self.parent = self.make_user("parent214", UserProfile.Role.PARENT)
        self.rider_user = self.make_user("rider214", UserProfile.Role.RIDER)

        ShowLeadAssignment.objects.create(show=self.show, user=self.show_lead, active=True)
        ShowLeadAssignment.objects.create(show=self.other_show, user=self.other_lead, active=True)

        self.course = ShowCourse.objects.create(
            show=self.show,
            title="Open Over Fences",
            course_type=ShowCourse.CourseType.OVER_FENCES,
            ring="Ring 1",
            coach_notes="Private strategy",
            created_by=self.coach,
            updated_by=self.coach,
        )

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def test_course_workspace_permissions_are_role_scoped(self):
        self.client.force_login(self.coach)
        self.assertEqual(
            self.client.get(reverse("show_courses", args=[self.show.pk])).status_code,
            200,
        )

        self.client.force_login(self.show_lead)
        response = self.client.get(reverse("show_courses", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Private strategy")

        self.client.force_login(self.parent)
        self.assertEqual(
            self.client.get(reverse("show_courses", args=[self.show.pk])).status_code,
            403,
        )

        self.client.force_login(self.other_lead)
        self.assertEqual(
            self.client.get(reverse("show_courses", args=[self.show.pk])).status_code,
            403,
        )

    def test_show_lead_can_update_course_media_but_not_private_details(self):
        self.client.force_login(self.show_lead)
        self.assertEqual(
            self.client.get(reverse("show_course_edit", args=[self.show.pk, self.course.pk])).status_code,
            403,
        )
        response = self.client.post(
            reverse("show_course_media", args=[self.show.pk, self.course.pk]),
            {"external_link": "https://example.com/course.pdf"},
        )
        self.assertEqual(response.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.external_link, "https://example.com/course.pdf")
        self.assertEqual(self.course.coach_notes, "Private strategy")

    def test_course_media_rejects_unsupported_file_types(self):
        upload = SimpleUploadedFile(
            "course.exe",
            b"not a course image",
            content_type="application/octet-stream",
        )
        form = ShowCourseMediaForm(
            data={"external_link": ""},
            files={"course_file": upload},
            instance=self.course,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("course_file", form.errors)

    def test_course_document_is_protected_by_course_permissions(self):
        self.course.course_file = SimpleUploadedFile(
            "ring-1-course.jpg",
            b"fake course image",
            content_type="image/jpeg",
        )
        self.course.save(update_fields=["course_file"])

        self.client.force_login(self.show_lead)
        response = self.client.get(
            reverse("show_course_document", args=[self.show.pk, self.course.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")

        self.client.force_login(self.parent)
        self.assertEqual(
            self.client.get(
                reverse("show_course_document", args=[self.show.pk, self.course.pk])
            ).status_code,
            403,
        )

    def test_horse_list_document_is_team_authenticated_and_upload_is_restricted(self):
        document = ShowHorseListDocument.objects.create(
            show=self.show,
            revision=1,
            document=SimpleUploadedFile(
                "horse-list.jpg",
                b"fake image data",
                content_type="image/jpeg",
            ),
            uploaded_by=self.coach,
            family_notes="Please review horse descriptions before the first draw.",
            notes="Internal coach note",
        )

        self.client.force_login(self.parent)
        response = self.client.get(
            reverse("show_horse_list_document", args=[self.show.pk, document.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(
            self.client.get(reverse("show_horse_list_upload", args=[self.show.pk])).status_code,
            403,
        )

        hoofprint = self.client.get(reverse("show_hoofprint", args=[self.show.pk]))
        self.assertEqual(hoofprint.status_code, 200)
        self.assertContains(hoofprint, "Please review horse descriptions before the first draw.")
        self.assertNotContains(hoofprint, "Internal coach note")

        self.client.force_login(self.show_lead)
        self.assertEqual(
            self.client.get(reverse("show_horse_list_upload", args=[self.show.pk])).status_code,
            200,
        )

    def test_show_day_renders_with_assigned_planning_item(self):
        item = ShowPlanningItem.objects.create(
            show=self.show,
            item_type=ShowPlanningItem.ItemType.CHECKLIST,
            team_level=ShowPlanningItem.TeamLevel.ALL,
            title="Bring show binder",
            assigned_to=self.show_lead,
            family_visible=True,
        )
        self.client.force_login(self.show_lead)
        response = self.client.get(reverse("show_day_dashboard", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, item.title)

    def test_horse_of_day_award_blocks_assignment_deletion(self):
        horse = Horse.objects.create(team=self.team, name="History Horse")
        assignment = HorseShowAssignment.objects.create(
            show=self.show,
            horse=horse,
            available=True,
        )
        award = HorseShowAward.objects.create(
            show=self.show,
            assignment=assignment,
            session=HorseShowAward.Session.FULL_DAY,
        )

        self.client.force_login(self.coach)
        response = self.client.post(
            reverse("show_horse_remove", args=[self.show.pk, assignment.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(HorseShowAssignment.objects.filter(pk=assignment.pk).exists())
        self.assertTrue(HorseShowAward.objects.filter(pk=award.pk).exists())
