"""People-aware recipient discovery for ArenaLine communications."""

from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from portal.model_modules.people import LegacyPersonLink, Person, PersonRelationship
from portal.models import Announcement, GuardianContact, Rider, UserProfile


def _effective_parent_relationships(team):
    """Return canonical parent/guardian relationships currently in effect."""
    today = timezone.localdate()
    return PersonRelationship.objects.filter(
        from_person__team=team,
        from_person__active=True,
        from_person__user__isnull=False,
        from_person__user__is_active=True,
        to_person__team=team,
        relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        active=True,
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today),
        Q(end_date__isnull=True) | Q(end_date__gt=today),
    )


def _active_parent_user_ids_for_child_people(child_person_ids, team):
    return _effective_parent_relationships(team).filter(
        to_person_id__in=child_person_ids,
    ).values_list("from_person__user_id", flat=True)


def announcement_recipients(announcement, *, active_season_resolver):
    """Return User delivery endpoints, discovering family identity through People first.

    User remains the delivery endpoint for notifications/email. Legacy Rider and
    GuardianContact links remain compatibility fallbacks during v3.2.
    """
    users = User.objects.filter(
        profile__team=announcement.team,
        is_active=True,
    ).select_related("profile")
    audience = announcement.audience

    if audience == Announcement.Audience.COACHES:
        return users.filter(profile__role__in=[UserProfile.Role.ADMIN, UserProfile.Role.COACH]).distinct()

    if audience == Announcement.Audience.PARENTS:
        canonical_parent_users = _effective_parent_relationships(announcement.team).values_list(
            "from_person__user_id", flat=True
        )
        return users.filter(
            Q(id__in=canonical_parent_users)
            | Q(profile__role=UserProfile.Role.PARENT)
            | Q(guardian_contact__isnull=False)
        ).distinct()

    if audience == Announcement.Audience.RIDERS:
        canonical_rider_users = LegacyPersonLink.objects.filter(
            person__team=announcement.team,
            person__active=True,
            person__user__isnull=False,
            rider__team=announcement.team,
            rider__isnull=False,
        ).values_list("person__user_id", flat=True)
        return users.filter(
            Q(id__in=canonical_rider_users) | Q(profile__role=UserProfile.Role.RIDER)
        ).distinct()

    if audience in {Announcement.Audience.FUTURES, Announcement.Audience.UPPER}:
        season = announcement.season or active_season_resolver(announcement.team)
        if not season:
            return users.none()

        rider_ids = Rider.objects.filter(
            team=announcement.team,
            memberships__season=season,
            memberships__team_level=audience,
        ).values_list("id", flat=True)

        child_people = LegacyPersonLink.objects.filter(
            rider_id__in=rider_ids,
            person__team=announcement.team,
            person__active=True,
        ).values_list("person_id", flat=True)

        canonical_rider_users = Person.objects.filter(
            id__in=child_people,
            user__isnull=False,
            user__is_active=True,
        ).values_list("user_id", flat=True)
        canonical_parent_users = _active_parent_user_ids_for_child_people(child_people, announcement.team)

        legacy_rider_users = Rider.objects.filter(
            id__in=rider_ids,
            user__isnull=False,
        ).values_list("user_id", flat=True)
        legacy_guardian_users = GuardianContact.objects.filter(
            team=announcement.team,
            rider_links__rider_id__in=rider_ids,
            user__isnull=False,
        ).values_list("user_id", flat=True)

        return users.filter(
            Q(id__in=canonical_rider_users)
            | Q(id__in=canonical_parent_users)
            | Q(id__in=legacy_rider_users)
            | Q(id__in=legacy_guardian_users)
            | Q(profile__role__in=[UserProfile.Role.ADMIN, UserProfile.Role.COACH])
        ).distinct()

    if audience == Announcement.Audience.SELECTED:
        return users.filter(id__in=announcement.selected_users.values("id")).distinct()

    return users.distinct()
