"""v3.9.2 conversation foundation security regressions."""
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from portal.models import Team, Conversation, ConversationMember
from portal.model_modules.people import Person
from portal.conversation_services import (
    create_conversation, send_message, visible_conversations,
    require_conversation_member,
)


class ConversationFoundationTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Barn A")
        self.other_team = Team.objects.create(name="Barn B")
        self.alice = Person.objects.create(team=self.team, first_name="Alice", last_name="One")
        self.bob = Person.objects.create(team=self.team, first_name="Bob", last_name="Two")
        self.charlie = Person.objects.create(team=self.team, first_name="Charlie", last_name="Three")
        self.outsider = Person.objects.create(team=self.other_team, first_name="Other", last_name="Person")

    def test_direct_conversation_members_and_message(self):
        thread = create_conversation(
            organization=self.team, creator=self.alice,
            participants=[self.bob], kind=Conversation.Kind.DIRECT,
        )
        self.assertEqual(thread.members.count(), 2)
        message = send_message(conversation=thread, sender=self.alice, body="Hello")
        self.assertEqual(message.body, "Hello")
        self.assertIn(thread, visible_conversations(organization=self.team, person=self.bob))

    def test_nonmember_cannot_read_or_send(self):
        thread = create_conversation(
            organization=self.team, creator=self.alice,
            participants=[self.bob], kind=Conversation.Kind.DIRECT,
        )
        self.assertNotIn(thread, visible_conversations(organization=self.team, person=self.charlie))
        with self.assertRaises(PermissionDenied):
            require_conversation_member(conversation=thread, person=self.charlie)
        with self.assertRaises(PermissionDenied):
            send_message(conversation=thread, sender=self.charlie, body="No")

    def test_cross_tenant_participant_rejected(self):
        with self.assertRaises(ValidationError):
            create_conversation(
                organization=self.team, creator=self.alice,
                participants=[self.outsider], kind=Conversation.Kind.DIRECT,
            )
        self.assertFalse(Conversation.objects.exists())

    def test_direct_conversation_requires_two_distinct_people(self):
        with self.assertRaises(ValidationError):
            create_conversation(
                organization=self.team, creator=self.alice,
                participants=[self.alice], kind=Conversation.Kind.DIRECT,
            )

    def test_departed_member_cannot_send(self):
        thread = create_conversation(
            organization=self.team, creator=self.alice,
            participants=[self.bob], kind=Conversation.Kind.DIRECT,
        )
        membership = ConversationMember.objects.get(conversation=thread, person=self.bob)
        from django.utils import timezone
        membership.left_at = timezone.now()
        membership.save()
        with self.assertRaises(PermissionDenied):
            send_message(conversation=thread, sender=self.bob, body="No longer a member")

    def test_new_member_cannot_see_earlier_messages(self):
        from django.utils import timezone
        from datetime import timedelta
        from portal.conversation_services import visible_messages
        thread = create_conversation(
            organization=self.team, creator=self.alice,
            participants=[self.bob], kind=Conversation.Kind.GROUP,
        )
        old = send_message(conversation=thread, sender=self.alice, body="Earlier")
        member = ConversationMember.objects.create(
            conversation=thread, person=self.charlie,
            joined_at=timezone.now() + timedelta(seconds=1),
        )
        self.assertNotIn(old, visible_messages(conversation=thread, person=self.charlie))

    def test_nonmember_cannot_access_message_history(self):
        from portal.conversation_services import visible_messages
        thread = create_conversation(
            organization=self.team, creator=self.alice,
            participants=[self.bob], kind=Conversation.Kind.DIRECT,
        )
        send_message(conversation=thread, sender=self.alice, body="Private")
        with self.assertRaises(PermissionDenied):
            list(visible_messages(conversation=thread, person=self.charlie))

    def test_cross_tenant_sender_cannot_post(self):
        thread = create_conversation(
            organization=self.team, creator=self.alice,
            participants=[self.bob], kind=Conversation.Kind.DIRECT,
        )
        with self.assertRaises(PermissionDenied):
            send_message(conversation=thread, sender=self.outsider, body="Blocked")
