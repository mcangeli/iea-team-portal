"""Private conversation authorization and write boundary for v3.9.2."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Conversation, ConversationMember, ConversationMessage


def visible_conversations(*, organization, person):
    if person is None or not person.active or person.team_id != organization.pk:
        return Conversation.objects.none()
    return Conversation.objects.filter(
        team=organization, members__person=person, members__left_at__isnull=True,
    ).distinct()


def require_conversation_member(*, conversation, person):
    if (person is None or not person.active or
            person.team_id != conversation.team_id or
            not ConversationMember.objects.filter(
                conversation=conversation, person=person, left_at__isnull=True,
            ).exists()):
        raise PermissionDenied("Conversation membership required.")
    return True


@transaction.atomic
def create_conversation(*, organization, creator, participants, kind, title=""):
    if creator is None or not creator.active or creator.team_id != organization.pk:
        raise PermissionDenied("Active organization identity required.")
    if kind not in Conversation.Kind.values:
        raise ValidationError("Invalid conversation kind.")
    people = {person.pk: person for person in [creator, *participants]}
    if any(not person.active or person.team_id != organization.pk for person in people.values()):
        raise ValidationError("Participants must be active members of the organization.")
    if kind == Conversation.Kind.DIRECT and len(people) != 2:
        raise ValidationError("Direct conversations require exactly two people.")
    if kind == Conversation.Kind.GROUP and len(people) < 2:
        raise ValidationError("Group conversations require at least two people.")
    conversation = Conversation(team=organization, created_by=creator, kind=kind, title=title)
    conversation.full_clean()
    conversation.save()
    for person in people.values():
        member = ConversationMember(conversation=conversation, person=person)
        member.full_clean()
        member.save()
    return conversation


@transaction.atomic
def send_message(*, conversation, sender, body):
    require_conversation_member(conversation=conversation, person=sender)
    if conversation.archived_at is not None:
        raise PermissionDenied("Archived conversations are read-only.")
    message = ConversationMessage(conversation=conversation, sender=sender, body=body)
    message.full_clean()
    message.save()
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
    return message


def visible_messages(*, conversation, person):
    require_conversation_member(conversation=conversation, person=person)
    return ConversationMessage.objects.filter(
        conversation=conversation, removed_at__isnull=True,
    ).filter(Q(created_at__gte=ConversationMember.objects.filter(
        conversation=conversation, person=person,
    ).values("joined_at")[:1]))
