"""Privacy-safe public profile helpers for ArenaLine People.

Public-facing surfaces must opt in to this payload instead of reading Person or
legacy Rider fields directly. Contact details, birth dates, school, graduation
year, family relationships, and operational records are intentionally excluded.
"""

from portal.model_modules.people import IEAParticipant, LegacyPersonLink, Person


def public_profile_for_person(person):
    """Return the approved public profile payload for an active opted-in Person."""
    if not person or not person.active or not person.public_profile_enabled:
        return None
    return {
        "person_id": person.pk,
        "display_name": person.display_name,
        "photo": person.photo,
        "bio": person.bio,
        "website_url": person.website_url,
        "instagram_url": person.instagram_url,
        "youtube_url": person.youtube_url,
    }


def public_profile_for_rider(rider):
    """Resolve a legacy Rider to its canonical, explicitly opted-in Person profile."""
    bridge = (
        LegacyPersonLink.objects.filter(rider=rider)
        .select_related("person")
        .first()
    )
    return public_profile_for_person(bridge.person if bridge else None)


def public_profiles_for_riders(riders):
    """Resolve public payloads for a rider collection without exposing private Person data."""
    rider_ids = [rider.pk for rider in riders]
    bridges = (
        LegacyPersonLink.objects.filter(rider_id__in=rider_ids)
        .select_related("person")
    )
    profiles = {
        bridge.rider_id: public_profile_for_person(bridge.person)
        for bridge in bridges
    }
    return {rider_id: profile for rider_id, profile in profiles.items() if profile}


def _public_rider_people_for_team(team):
    """Return opted-in People who have an active IEA participant identity.

    v3.9 treats IEAParticipant as the primary rider-domain qualification. A
    legacy Rider bridge remains an additive compatibility path until closeout.
    """
    participant_person_ids = IEAParticipant.objects.filter(
        team=team,
        active=True,
        person__active=True,
        person__public_profile_enabled=True,
    ).values_list("person_id", flat=True)
    legacy_person_ids = LegacyPersonLink.objects.filter(
        person__team=team,
        person__active=True,
        person__public_profile_enabled=True,
        rider__isnull=False,
        rider__active=True,
    ).values_list("person_id", flat=True)
    return Person.objects.filter(
        team=team,
        active=True,
        public_profile_enabled=True,
        pk__in=set(participant_person_ids) | set(legacy_person_ids),
    ).order_by("last_name", "first_name", "id")


def public_profiles_for_team(team):
    """Return privacy-safe public Rider Cards from canonical People."""
    return [
        public_profile_for_person(person)
        for person in _public_rider_people_for_team(team)
    ]


def public_profile_for_team_person(team, person_id):
    """Resolve one public Rider Card by canonical Person identity."""
    person = (
        _public_rider_people_for_team(team)
        .filter(pk=person_id)
        .first()
    )
    return public_profile_for_person(person)
