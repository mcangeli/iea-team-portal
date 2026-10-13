from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.people import Person
from portal.models import Team, CommunityPost, CommunityPostAudience


class CommunityManagementTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Management Test Barn")
        self.other = Team.objects.create(name="Other Management Barn")
        self.staff = User.objects.create_user(username="community-editor", password="test123", is_staff=True)
        self.reader = User.objects.create_user(username="community-nonstaff", password="test123")
        self.person = Person.objects.create(team=self.team, user=self.staff, first_name="Editor", last_name="One")
        self.reader_person = Person.objects.create(team=self.team, user=self.reader, first_name="Reader", last_name="One")
        self.post = CommunityPost.objects.create(team=self.team, author=self.person, created_by=self.staff, title="Original", body="[b]Original[/b]", status=CommunityPost.Status.PUBLISHED, published_at=timezone.now())
        CommunityPostAudience.objects.create(post=self.post, scope="organization")

    def test_management_requires_staff(self):
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(reverse("community_manage")).status_code, 403)
        self.assertEqual(self.client.get(reverse("community_edit", args=[self.post.pk])).status_code, 403)

    def test_edit_to_draft_removes_from_feed(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("community_edit", args=[self.post.pk]), {
            "title": "Updated", "body": "[i]Updated[/i]", "audience_scope": "person",
            "audience_people": [str(self.reader_person.pk)],
        })
        self.assertEqual(response.status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, CommunityPost.Status.DRAFT)
        self.assertIsNone(self.post.published_at)
        self.assertEqual(self.post.audiences.get().person_id, self.reader_person.pk)

    def test_archive_requires_post_and_hides_post(self):
        self.client.force_login(self.staff)
        url = reverse("community_archive", args=[self.post.pk])
        self.assertNotEqual(self.client.get(url).status_code, 302)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, CommunityPost.Status.ARCHIVED)

    def test_other_organization_post_not_editable(self):
        other_person = Person.objects.create(team=self.other, first_name="Other", last_name="Author")
        other_post = CommunityPost.objects.create(team=self.other, author=other_person, created_by=self.staff, title="Other", body="Secret")
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("community_edit", args=[other_post.pk])).status_code, 404)
