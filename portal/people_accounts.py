"""Canonical People identity synchronization for Django login accounts.

Authentication remains Django User-backed, while Person is the organization human
identity. Legacy Rider/GuardianContact links are maintained as v3.2 compatibility
bridges rather than being the source of login identity.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from portal.model_modules.people import LegacyPersonLink, Person
from portal.people_compat import ensure_guardian_person, ensure_rider_person


def _person_from_legacy(*, rider=None, guardian=None):
    if rider is not None:
        return ensure_rider_person(rider)
    if guardian is not None:
        return ensure_guardian_person(guardian)
    return None


def person_for_user(user):
    try:
        return user.arena_person
    except Person.DoesNotExist:
        return None


def _sync_person_fields(person, user):
    changed = []
    values = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
    }
    for field, value in values.items():
        if value and getattr(person, field) != value:
            setattr(person, field, value)
            changed.append(field)
    if not person.active:
        person.active = True
        changed.append("active")
    if changed:
        person.save(update_fields=changed + ["updated_at"])


@transaction.atomic
def sync_user_person_identity(user, team, *, rider=None, guardian=None):
    """Ensure a login resolves to exactly one canonical Person in its organization."""
    current = person_for_user(user)
    legacy_person = _person_from_legacy(rider=rider, guardian=guardian)

    if current and current.team_id != team.id:
        raise ValidationError("This login is linked to a Person in another organization.")
    if legacy_person and legacy_person.team_id != team.id:
        raise ValidationError("The selected person belongs to another organization.")
    if current and legacy_person and current.pk != legacy_person.pk:
        raise ValidationError(
            "This login is already linked to a different Person. Manage the existing People record instead."
        )

    person = current or legacy_person
    if person is None:
        person = Person.objects.create(
            team=team,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            active=True,
        )

    if person.user_id and person.user_id != user.id:
        raise ValidationError("This Person already has a different login account.")
    if person.user_id != user.id:
        person.user = user
        person.save(update_fields=["user", "updated_at"])

    _sync_person_fields(person, user)
    return person


@transaction.atomic
def sync_user_person_after_account_edit(user, team, *, rider=None, guardian=None):
    """Keep the canonical Person attached while legacy account links are edited."""
    person = sync_user_person_identity(user, team, rider=rider, guardian=guardian)

    # Staff and other People without legacy Rider/Guardian identities should not
    # accumulate empty compatibility bridges merely because their login is edited.
    if rider is None and guardian is None:
        return person

    # A Person may legitimately retain both compatibility identities. We do not
    # delete bridges when a login role changes; domain history belongs to Person.
    bridge, _ = LegacyPersonLink.objects.get_or_create(person=person)
    if rider is not None and bridge.rider_id != rider.id:
        if LegacyPersonLink.objects.filter(rider=rider).exclude(pk=bridge.pk).exists():
            raise ValidationError("That rider is already linked to another Person.")
        bridge.rider = rider
    if guardian is not None and bridge.guardian_id != guardian.id:
        if LegacyPersonLink.objects.filter(guardian=guardian).exclude(pk=bridge.pk).exists():
            raise ValidationError("That parent/guardian is already linked to another Person.")
        bridge.guardian = guardian
    bridge.save()
    return person
