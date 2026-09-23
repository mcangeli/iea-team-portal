"""Compatibility helpers between legacy Rider/Guardian records and canonical People.

The rider/guardian UI remains available during v3.2, but new relationships should
also be represented in the canonical Person model so People is the source of
truth going forward.
"""

from django.core.exceptions import ValidationError
from django.utils import timezone

from portal.model_modules.people import (
    IEAParticipant,
    LegacyPersonLink,
    OrganizationRoleAssignment,
    Person,
    PersonRelationship,
)
from portal.models import GuardianContact


def _person_for_user_or_create(*, team, user, defaults):
    if user:
        person = Person.objects.filter(user=user).first()
        if person:
            if person.team_id != team.id:
                raise ValidationError("The linked account belongs to another organization.")
            return person
    return Person.objects.create(team=team, user=user, **defaults)


def _ensure_active_role(*, team, person, role, desired_active=True):
    assignment = OrganizationRoleAssignment.objects.filter(
        team=team,
        person=person,
        role=role,
        active=True,
    ).order_by("start_date", "id").first()
    if assignment:
        return assignment

    assignment, _ = OrganizationRoleAssignment.objects.get_or_create(
        team=team,
        person=person,
        role=role,
        start_date=None,
        defaults={"active": desired_active},
    )
    if desired_active and not assignment.active:
        assignment.active = True
        assignment.end_date = None
        assignment.save(update_fields=["active", "end_date"])
    return assignment


def ensure_rider_person(rider):
    bridge = LegacyPersonLink.objects.filter(rider=rider).select_related("person").first()
    if bridge:
        person = bridge.person
    else:
        person = _person_for_user_or_create(
            team=rider.team,
            user=rider.user,
            defaults={
                "first_name": rider.first_name,
                "last_name": rider.last_name,
                "preferred_name": rider.preferred_name,
                "email": rider.email,
                "school": rider.school,
                "bio": rider.bio,
                "photo": rider.photo,
                "active": rider.active,
            },
        )
        bridge, _ = LegacyPersonLink.objects.get_or_create(person=person)
        if bridge.rider_id and bridge.rider_id != rider.id:
            raise ValidationError("This Person is already linked to another rider record.")
        if not bridge.rider_id:
            bridge.rider = rider
            bridge.save(update_fields=["rider"])

    _ensure_active_role(
        team=rider.team,
        person=person,
        role=OrganizationRoleAssignment.Role.RIDER,
        desired_active=rider.active,
    )
    return person


def ensure_guardian_person(guardian):
    bridge = LegacyPersonLink.objects.filter(guardian=guardian).select_related("person").first()
    if bridge:
        person = bridge.person
    else:
        person = _person_for_user_or_create(
            team=guardian.team,
            user=guardian.user,
            defaults={
                "first_name": guardian.first_name,
                "last_name": guardian.last_name,
                "email": guardian.email,
                "phone": guardian.phone,
            },
        )
        bridge, _ = LegacyPersonLink.objects.get_or_create(person=person)
        if bridge.guardian_id and bridge.guardian_id != guardian.id:
            raise ValidationError("This Person is already linked to another guardian contact.")
        if not bridge.guardian_id:
            bridge.guardian = guardian
            bridge.save(update_fields=["guardian"])

    _ensure_active_role(
        team=guardian.team,
        person=person,
        role=OrganizationRoleAssignment.Role.PARENT_GUARDIAN,
    )
    return person


def ensure_guardian_contact_for_person(person):
    bridge = LegacyPersonLink.objects.filter(person=person).select_related("guardian").first()
    if bridge and bridge.guardian_id:
        return bridge.guardian

    guardian = None
    if person.user_id:
        guardian = GuardianContact.objects.filter(user_id=person.user_id, team=person.team).first()
    if guardian is None:
        guardian = GuardianContact.objects.create(
            team=person.team,
            user=person.user if person.user_id and not GuardianContact.objects.filter(user_id=person.user_id).exists() else None,
            first_name=person.first_name,
            last_name=person.last_name,
            email=person.email,
            phone=person.phone,
        )

    bridge, _ = LegacyPersonLink.objects.get_or_create(person=person)
    if bridge.guardian_id and bridge.guardian_id != guardian.id:
        raise ValidationError("This Person is already linked to another guardian contact.")
    if not bridge.guardian_id:
        bridge.guardian = guardian
        bridge.save(update_fields=["guardian"])
    return guardian


def sync_rider_guardian_link(link):
    rider_person = ensure_rider_person(link.rider)
    guardian_person = ensure_guardian_person(link.guardian)
    if rider_person.pk == guardian_person.pk:
        return None

    relationship, _ = PersonRelationship.objects.get_or_create(
        from_person=guardian_person,
        to_person=rider_person,
        relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        defaults={
            "label": link.relationship,
            "primary_contact": link.primary_contact,
            "active": True,
        },
    )
    changed = []
    if relationship.label != link.relationship:
        relationship.label = link.relationship
        changed.append("label")
    if relationship.primary_contact != link.primary_contact:
        relationship.primary_contact = link.primary_contact
        changed.append("primary_contact")
    if not relationship.active:
        relationship.active = True
        changed.append("active")
    if relationship.end_date is not None:
        relationship.end_date = None
        changed.append("end_date")
    if changed:
        relationship.save(update_fields=changed)
    return relationship


def end_rider_guardian_relationship(*, rider, guardian):
    rider_bridge = LegacyPersonLink.objects.filter(rider=rider).first()
    guardian_bridge = LegacyPersonLink.objects.filter(guardian=guardian).first()
    if not rider_bridge or not guardian_bridge or rider_bridge.person_id == guardian_bridge.person_id:
        return
    relationship = PersonRelationship.objects.filter(
        from_person_id=guardian_bridge.person_id,
        to_person_id=rider_bridge.person_id,
        relationship_type=PersonRelationship.RelationshipType.PARENT_GUARDIAN,
        active=True,
    ).first()
    if relationship:
        relationship.active = False
        relationship.end_date = timezone.localdate()
        relationship.save(update_fields=["active", "end_date"])


def ensure_iea_participant_for_person(person):
    """Create or validate Person-native IEA identity from a deterministic Rider bridge.

    This helper intentionally refuses to infer identity from names, email
    addresses, or other fuzzy attributes. Existing Person-side IEA data wins;
    conflicts are surfaced for reconciliation rather than silently overwritten.
    """
    try:
        bridge = person.legacy_identity
    except LegacyPersonLink.DoesNotExist:
        bridge = None

    if not bridge or not bridge.rider_id:
        raise ValidationError("A linked legacy rider is required to backfill IEA participation.")

    rider = bridge.rider
    if rider.team_id != person.team_id:
        raise ValidationError("Linked legacy rider must belong to the person's organization.")

    participant = IEAParticipant.objects.filter(person=person).first()
    if participant:
        if participant.team_id != person.team_id:
            raise ValidationError("Existing IEA participant belongs to another organization.")
        if participant.legacy_rider_id and participant.legacy_rider_id != rider.id:
            raise ValidationError("Existing IEA participant is linked to a different legacy rider.")
        if (
            participant.iea_member_number
            and rider.iea_member_number
            and participant.iea_member_number != rider.iea_member_number
        ):
            raise ValidationError("IEA member number conflicts with the linked legacy rider.")

        changed = []
        if not participant.legacy_rider_id:
            participant.legacy_rider = rider
            changed.append("legacy_rider")
        if not participant.iea_member_number and rider.iea_member_number:
            participant.iea_member_number = rider.iea_member_number
            changed.append("iea_member_number")
        if changed:
            participant.full_clean()
            participant.save(update_fields=changed)
        return participant, False

    participant = IEAParticipant(
        team=person.team,
        person=person,
        legacy_rider=rider,
        iea_member_number=rider.iea_member_number,
        active=rider.active,
    )
    participant.full_clean()
    participant.save()
    return participant, True


def ensure_iea_participant_for_rider(rider):
    """Ensure canonical Person and Person-native IEA identity for one legacy Rider."""
    person = ensure_rider_person(rider)
    return ensure_iea_participant_for_person(person)


def backfill_iea_participants(*, team=None):
    """Backfill deterministic legacy Rider bridges and report conflicts.

    Returns a summary rather than swallowing conflicts so callers can reconcile
    ambiguous historical data explicitly.
    """
    links = LegacyPersonLink.objects.filter(rider__isnull=False).select_related(
        "person", "rider"
    )
    if team is not None:
        links = links.filter(person__team=team)

    summary = {"created": 0, "existing": 0, "conflicts": []}
    for link in links.order_by("person_id"):
        try:
            _, created = ensure_iea_participant_for_person(link.person)
        except ValidationError as exc:
            summary["conflicts"].append(
                {
                    "person_id": link.person_id,
                    "rider_id": link.rider_id,
                    "errors": list(exc.messages),
                }
            )
            continue
        summary["created" if created else "existing"] += 1
    return summary
