from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from portal.host_show_models import HostShowFamilyPublication, HostShowOperations, HostShowStaffAssignment, ShowManagerAssignment
from portal.models import Season, Show, Team, UserProfile


class V250HostFamilyPublicationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Family Publication Team")
        self.season = Season.objects.create(team=self.team, name="2026-2027", start_date=date(2026, 8, 1), end_date=date(2027, 6, 30), is_active=True)
        self.show = Show.objects.create(team=self.team, season=self.season, name="Hosted Family Show", show_date=date(2026, 11, 21), financial_role=Show.FinancialRole.HOSTING_ATTENDING)
        self.manager = self.make_user("familymanager", UserProfile.Role.PARENT)
        self.parent = self.make_user("familyspectator", UserProfile.Role.PARENT)
        ShowManagerAssignment.objects.create(show=self.show, user=self.manager, active=True)
        self.operations = HostShowOperations.objects.create(
            show=self.show,
            arrival_instructions="Use the north entrance.",
            check_in_location="Secretary booth",
            trailer_parking="Trailer lot B",
            warmup_schooling="Schooling opens at 6:30 AM.",
            emergency_information="EMS is stationed at the main office.",
            family_notes="Bring water and team polos.",
            internal_notes="PRIVATE HOST STRATEGY",
            created_by=self.manager,
            updated_by=self.manager,
        )
        HostShowStaffAssignment.objects.create(operations=self.operations, role=HostShowStaffAssignment.Role.JUDGE, name="PRIVATE JUDGE CONTACT")

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password="testpass")
        user.profile.team = self.team
        user.profile.role = role
        user.profile.save(update_fields=["team", "role"])
        return user

    def test_family_cannot_view_until_explicitly_published(self):
        self.client.force_login(self.parent)
        response = self.client.get(reverse("host_family_information", args=[self.show.pk]))
        self.assertEqual(response.status_code, 403)

    def test_publication_settings_use_clear_family_publish_language(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("host_family_publication_edit", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Publish Family Show Info")
        self.assertContains(response, "Host Show Operations stays private by default")

    def test_show_manager_can_publish_selected_sections(self):
        self.client.force_login(self.manager)
        response = self.client.post(reverse("host_family_publication_edit", args=[self.show.pk]), {
            "published": "on",
            "publish_arrival": "on",
            "publish_warmup": "on",
            "publish_family_notes": "on",
        })
        self.assertEqual(response.status_code, 302)
        publication = HostShowFamilyPublication.objects.get(operations=self.operations)
        self.assertTrue(publication.published)
        self.assertTrue(publication.publish_arrival)
        self.assertFalse(publication.publish_emergency)

    def test_family_page_shows_only_selected_host_sections(self):
        HostShowFamilyPublication.objects.create(operations=self.operations, published=True, publish_arrival=True, publish_family_notes=True, updated_by=self.manager)
        self.client.force_login(self.parent)
        response = self.client.get(reverse("host_family_information", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Use the north entrance.")
        self.assertContains(response, "Secretary booth")
        self.assertContains(response, "Bring water and team polos.")
        self.assertNotContains(response, "Trailer lot B")
        self.assertNotContains(response, "Schooling opens at 6:30 AM.")
        self.assertNotContains(response, "EMS is stationed at the main office.")
        self.assertNotContains(response, "PRIVATE HOST STRATEGY")
        self.assertNotContains(response, "PRIVATE JUDGE CONTACT")

    def test_unpublishing_immediately_removes_family_access_without_deleting_plan(self):
        publication = HostShowFamilyPublication.objects.create(operations=self.operations, published=True, publish_arrival=True, updated_by=self.manager)
        publication.published = False
        publication.save(update_fields=["published"])
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse("host_family_information", args=[self.show.pk])).status_code, 403)
        self.operations.refresh_from_db()
        self.assertEqual(self.operations.arrival_instructions, "Use the north entrance.")
