"""Helpers for legacy regression fixtures under the v3.9 Person-native data contract.

Older regression tests intentionally construct legacy Rider rows. Production v3.9
requires those rows to have deterministic Person/IEAParticipant bridges before
Person-native IEA workflows run, so tests that exercise those workflows should
normalize their fixture rather than recreate an impossible post-migration state.
"""

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
