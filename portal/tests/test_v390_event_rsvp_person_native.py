from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from portal.model_modules.people import IEAParticipant, Person, PersonRelationship
from portal.models import CalendarEvent, EventRSVP, Team, UserProfile


class V390EventRSVPPersonNativeTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Person Native RSVP")
        self.parent_user = User.objects.create_user(username="rsvp-parent", password="test-pass")
        self.parent_user.profile.team = self.team
        self.parent_user.profile.role = UserProfile.Role.PARENT
        self.parent_user.profile.save(update_fields=["team", "role"])
        self.parent = Person.objects.create(
            team=self.team, user=self.parent_user, first_name="Pat", last_name="Parent"
        )
        self.child = Person.objects.create(
            team=self.team, first_name="Casey", last_name="Participant"
        )
        PersonRelationship.objects.create(
            from_person=self.parent,
            to_person=self.child,
            relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        )
        self.participant = IEAParticipant.objects.create(team=self.team, person=self.child)
        self.event = CalendarEvent.objects.create(
            team=self.team,
            title="Team Meeting",
            starts_at=timezone.now() + timedelta(days=2),
            rsvp_requested=True,
        )

    def test_event_rsvp_can_exist_without_legacy_rider(self):
        rsvp = EventRSVP(event=self.event, person=self.child, status=EventRSVP.Status.GOING)
        rsvp.full_clean()
        rsvp.save()

        self.assertEqual(rsvp.participant_identity, self.child)
        self.assertIsNone(rsvp.rider_id)

    def test_parent_can_update_person_native_rsvp_without_legacy_rider(self):
        self.client.force_login(self.parent_user)

        response = self.client.post(
            reverse("event_rsvp", args=[self.event.pk, self.participant.pk]),
            {"status": EventRSVP.Status.GOING, "notes": "We will be there."},
        )

        self.assertEqual(response.status_code, 302)
        rsvp = EventRSVP.objects.get(event=self.event, person=self.child)
        self.assertIsNone(rsvp.rider_id)
        self.assertEqual(rsvp.status, EventRSVP.Status.GOING)
        self.assertEqual(rsvp.responded_by, self.parent_user)

    def test_my_team_renders_person_native_rsvp_row_without_legacy_rider(self):
        EventRSVP.objects.create(
            event=self.event,
            person=self.child,
            status=EventRSVP.Status.GOING,
            responded_by=self.parent_user,
        )
        self.client.force_login(self.parent_user)

        response = self.client.get(reverse("my_team"))

        self.assertEqual(response.status_code, 200)
        event_row = next(row for row in response.context["event_rows"] if row["event"] == self.event)
        self.assertEqual(len(event_row["responses"]), 1)
        self.assertEqual(event_row["responses"][0]["rider"], self.child)
        self.assertEqual(event_row["responses"][0]["participant"], self.participant)
        self.assertEqual(event_row["responses"][0]["rsvp"].person, self.child)
        self.assertIsNone(event_row["responses"][0]["rsvp"].rider_id)
