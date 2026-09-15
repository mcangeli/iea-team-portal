"""Privacy-safe public profile helpers for ArenaLine People.

Public-facing surfaces must opt in to this payload instead of reading Person or
legacy Rider fields directly. Contact details, birth dates, school, graduation
year, family relationships, and operational records are intentionally excluded.
"""

from portal.model_modules.people import LegacyPersonLink, Person


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


def public_profiles_for_team(team):
    """Return only opted-in rider People for an organization's anonymous public site."""
    bridges = (
        LegacyPersonLink.objects.filter(
            person__team=team,
            person__active=True,
            person__public_profile_enabled=True,
            rider__isnull=False,
            rider__active=True,
        )
        .select_related("person", "rider")
        .order_by("person__last_name", "person__first_name", "person__id")
    )
    return [public_profile_for_person(bridge.person) for bridge in bridges]


def public_profile_for_team_person(team, person_id):
    """Resolve one public rider profile while enforcing organization and opt-in boundaries."""
    try:
        bridge = LegacyPersonLink.objects.select_related("person", "rider").get(
            person_id=person_id,
            person__team=team,
            person__active=True,
            person__public_profile_enabled=True,
            rider__isnull=False,
            rider__active=True,
        )
    except LegacyPersonLink.DoesNotExist:
        return None
    return public_profile_for_person(bridge.person)
