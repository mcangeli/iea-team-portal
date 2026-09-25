"""Helpers for legacy regression fixtures under the v3.9 Person-native data contract.

Older regression tests intentionally construct legacy Rider rows. Production v3.9
requires those rows to have deterministic Person/IEAParticipant bridges before
Person-native IEA workflows run, so tests that exercise those workflows should
normalize their fixture rather than recreate an impossible post-migration state.
"""

from portal.model_modules.people import PersonRelationship
from portal.models import SeasonMembership, ShowEntry
from portal.people_compat import ensure_iea_participant_for_rider


def bridge_legacy_rider(rider):
    participant, _created = ensure_iea_participant_for_rider(rider)
    SeasonMembership.objects.filter(
        rider=rider,
        iea_participant__isnull=True,
    ).update(iea_participant=participant)
    ShowEntry.objects.filter(
        rider=rider,
        iea_participant__isnull=True,
    ).update(iea_participant=participant)
    return participant


def bridge_legacy_parent(parent_user, rider):
    """Mirror an old Rider.guardians fixture into the canonical family graph."""
    participant = bridge_legacy_rider(rider)
    parent_person, _created = parent_user.team.people.get_or_create(
        user=parent_user,
        defaults={
            "first_name": parent_user.first_name or parent_user.username,
            "last_name": parent_user.last_name or "",
            "active": True,
        },
    )
    PersonRelationship.objects.get_or_create(
        from_person=parent_person,
        to_person=participant.person,
        relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        defaults={"active": True},
    )
    return parent_person, participant
