from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from portal.model_modules.people import LegacyPersonLink, Person, PersonRelationship
from portal.models import Announcement, Rider, Season, SeasonMembership, Team, UserProfile
from portal.view_modules.communications_helpers import _announcement_recipients


class V323PeopleCommunicationsTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Blue Skies Riding Academy")
        self.season = Season.objects.create(
            team=self.team,
            name="2026-27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
        )

        self.parent_user = self._user("canonical-parent", UserProfile.Role.PARENT)
        self.parent_person = Person.objects.create(
            team=self.team, user=self.parent_user, first_name="Morgan", last_name="Smith"
        )
        self.rider_user = self._user("canonical-rider", UserProfile.Role.RIDER)
        self.rider_person = Person.objects.create(
            team=self.team, user=self.rider_user, first_name="Jamie", last_name="Smith"
        )
        self.rider = Rider.objects.create(team=self.team, first_name="Jamie", last_name="Smith", grade=7)
        LegacyPersonLink.objects.create(person=self.rider_person, rider=self.rider)
        SeasonMembership.objects.create(
            season=self.season,
            rider=self.rider,
            team_level=SeasonMembership.TeamLevel.FUTURES,
        )
        PersonRelationship.objects.create(
            from_person=self.parent_person,
            to_person=self.rider_person,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
            active=True,
        )

    def _user(self, username, role):
        user = User.objects.create_user(username=username, password="pass12345")
        profile = user.profile
        profile.team = self.team
        profile.role = role
        profile.save(update_fields=["team", "role"])
        return user

    def _announcement(self, audience):
        return Announcement.objects.create(
            team=self.team,
            season=self.season,
            title="Team update",
            body="Update body",
            audience=audience,
        )

    def test_parent_audience_includes_canonical_parent_login(self):
        recipients = _announcement_recipients(self._announcement(Announcement.Audience.PARENTS))
        self.assertTrue(recipients.filter(pk=self.parent_user.pk).exists())

    def test_futures_audience_includes_canonical_rider_and_parent(self):
        recipients = _announcement_recipients(self._announcement(Announcement.Audience.FUTURES))
        self.assertTrue(recipients.filter(pk=self.rider_user.pk).exists())
        self.assertTrue(recipients.filter(pk=self.parent_user.pk).exists())

    def test_upper_audience_excludes_futures_family(self):
        recipients = _announcement_recipients(self._announcement(Announcement.Audience.UPPER))
        self.assertFalse(recipients.filter(pk=self.rider_user.pk).exists())
        self.assertFalse(recipients.filter(pk=self.parent_user.pk).exists())

    def test_ended_parent_relationship_excludes_parent_from_futures_family(self):
        relationship = PersonRelationship.objects.get(from_person=self.parent_person, to_person=self.rider_person)
        relationship.end_date = date.today()
        relationship.save(update_fields=["end_date"])
        recipients = _announcement_recipients(self._announcement(Announcement.Audience.FUTURES))
        self.assertTrue(recipients.filter(pk=self.rider_user.pk).exists())
        self.assertFalse(recipients.filter(pk=self.parent_user.pk).exists())

    def test_unrelated_parent_role_is_not_added_to_futures_audience(self):
        unrelated = self._user("unrelated-parent", UserProfile.Role.PARENT)
        Person.objects.create(team=self.team, user=unrelated, first_name="Taylor", last_name="Jones")
        recipients = _announcement_recipients(self._announcement(Announcement.Audience.FUTURES))
        self.assertFalse(recipients.filter(pk=unrelated.pk).exists())
