from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from portal.community_services import visible_community_posts
from portal.model_modules.people import Person, OrganizationGroup, OrganizationGroupMembership
from portal.models import Team, CommunityPost, CommunityPostAudience


class CommunityAudienceFoundationTests(TestCase):
    def setUp(self):
        self.org = Team.objects.create(name="First Barn")
        self.other_org = Team.objects.create(name="Other Barn")
        self.user = User.objects.create_user(username="community-reader", password="testpass123")
        self.person = Person.objects.create(team=self.org, user=self.user, first_name="First", last_name="Reader")
        self.other_person = Person.objects.create(team=self.other_org, first_name="Other", last_name="Reader")
        self.post = CommunityPost.objects.create(
            team=self.org, author=self.person, created_by=self.user,
            title="News", body="Barn update",
            status=CommunityPost.Status.PUBLISHED, published_at=timezone.now(),
        )

    def test_no_audience_is_private(self):
        self.assertFalse(visible_community_posts(organization=self.org, person=self.person).exists())

    def test_organization_audience_is_tenant_scoped(self):
        CommunityPostAudience.objects.create(post=self.post, scope=CommunityPostAudience.Scope.ORGANIZATION)
        self.assertTrue(visible_community_posts(organization=self.org, person=self.person).exists())
        self.assertFalse(visible_community_posts(organization=self.other_org, person=self.other_person).exists())

    def test_selected_person_is_not_other_person(self):
        CommunityPostAudience.objects.create(post=self.post, scope=CommunityPostAudience.Scope.PERSON, person=self.person)
        second = Person.objects.create(team=self.org, first_name="Second", last_name="Reader")
        self.assertTrue(visible_community_posts(organization=self.org, person=self.person).exists())
        self.assertFalse(visible_community_posts(organization=self.org, person=second).exists())

    def test_cross_tenant_author_and_audience_rejected(self):
        self.post.author = self.other_person
        with self.assertRaises(ValidationError):
            self.post.full_clean()
        self.post.author = self.person
        audience = CommunityPostAudience(post=self.post, scope=CommunityPostAudience.Scope.PERSON, person=self.other_person)
        with self.assertRaises(ValidationError):
            audience.full_clean()

    def test_group_membership_revocation_takes_effect(self):
        group = OrganizationGroup.objects.create(team=self.org, name="Barn group")
        membership = OrganizationGroupMembership.objects.create(
            team=self.org, group=group, person=self.person, status=OrganizationGroupMembership.Status.ACTIVE,
        )
        CommunityPostAudience.objects.create(post=self.post, scope=CommunityPostAudience.Scope.GROUP, group=group)
        self.assertTrue(visible_community_posts(organization=self.org, person=self.person).exists())
        membership.active = False
        membership.save(update_fields=["active"])
        self.assertFalse(visible_community_posts(organization=self.org, person=self.person).exists())

    def test_draft_and_expired_post_not_visible(self):
        CommunityPostAudience.objects.create(post=self.post, scope=CommunityPostAudience.Scope.ORGANIZATION)
        self.post.status = CommunityPost.Status.DRAFT
        self.post.save(update_fields=["status"])
        self.assertFalse(visible_community_posts(organization=self.org, person=self.person).exists())
        self.post.status = CommunityPost.Status.PUBLISHED
        self.post.expires_at = timezone.now() - timedelta(seconds=1)
        self.post.save(update_fields=["status", "expires_at"])
        self.assertFalse(visible_community_posts(organization=self.org, person=self.person).exists())

    def test_staff_can_oversee_targeted_post_in_own_organization(self):
        group = OrganizationGroup.objects.create(team=self.org, name="IEA Program")
        CommunityPostAudience.objects.create(post=self.post, scope=CommunityPostAudience.Scope.GROUP, group=group)
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.assertTrue(visible_community_posts(organization=self.org, person=self.person, user=self.user).filter(pk=self.post.pk).exists())
        self.assertFalse(visible_community_posts(organization=self.org, person=self.person).filter(pk=self.post.pk).exists())
        self.assertFalse(visible_community_posts(organization=self.other_org, person=self.other_person, user=self.user).filter(pk=self.post.pk).exists())

    def test_staff_cannot_see_drafts_or_expired_posts(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.post.status = CommunityPost.Status.DRAFT
        self.post.save(update_fields=["status"])
        self.assertFalse(visible_community_posts(organization=self.org, person=self.person, user=self.user).exists())
        self.post.status = CommunityPost.Status.PUBLISHED
        self.post.expires_at = timezone.now() - timedelta(minutes=1)
        self.post.save(update_fields=["status", "expires_at"])
        self.assertFalse(visible_community_posts(organization=self.org, person=self.person, user=self.user).exists())

    def test_scheduled_post_stays_hidden_until_publication(self):
        CommunityPostAudience.objects.create(post=self.post, scope="organization")
        now = timezone.now()
        self.post.published_at = now + timedelta(hours=2)
        self.post.save(update_fields=["published_at"])
        self.assertFalse(visible_community_posts(organization=self.org, person=self.person, at=now).exists())
        self.assertTrue(visible_community_posts(organization=self.org, person=self.person, at=now + timedelta(hours=3)).exists())

    def test_notice_priority_expires_without_hiding_post(self):
        CommunityPostAudience.objects.create(post=self.post, scope="organization")
        now = timezone.now()
        self.post.is_notice = True
        self.post.notice_until = now + timedelta(hours=1)
        self.post.save(update_fields=["is_notice", "notice_until"])
        active = visible_community_posts(organization=self.org, person=self.person, at=now).get()
        self.assertEqual(active.notice_rank, 1)
        later = visible_community_posts(organization=self.org, person=self.person, at=now + timedelta(hours=2)).get()
        self.assertEqual(later.notice_rank, 0)
