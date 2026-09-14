"""Compatibility bridge between legacy IEA committee assignments and v3.2 committees."""

from portal.model_modules.people import Committee, CommitteeMembership, OrganizationGroup, Person
from portal.models import CommitteeAssignment


# Legacy CommitteeAssignment roles are IEA-scoped compatibility roles. They must
# never imply organization-wide authority simply because the generalized
# committee model can also represent barn-level committees.
ROLE_MAP = {
    CommitteeAssignment.Role.UPPER_PARENT: ("IEA Program", "Upper Team Parent Committee", CommitteeMembership.Position.CHAIR),
    CommitteeAssignment.Role.FUTURES_PARENT: ("IEA Program", "Futures Team Parent Committee", CommitteeMembership.Position.CHAIR),
    CommitteeAssignment.Role.TREASURER: ("IEA Program", "IEA Finance Committee", CommitteeMembership.Position.TREASURER),
    CommitteeAssignment.Role.POINTS_SECRETARY: ("IEA Program", "IEA Points & Records", CommitteeMembership.Position.SECRETARY),
}


def _person_for_assignment(assignment):
    existing = Person.objects.filter(user=assignment.user).first()
    if existing:
        return existing if existing.team_id == assignment.team_id else None
    user = assignment.user
    return Person.objects.create(
        team=assignment.team,
        user=user,
        first_name=user.first_name or user.username,
        last_name=user.last_name or "",
        email=user.email or "",
    )


def sync_legacy_committee_assignment(assignment):
    mapping = ROLE_MAP.get(assignment.role)
    if not mapping:
        return None

    person = _person_for_assignment(assignment)
    if person is None:
        return None

    group_name, committee_name, position = mapping
    group = None
    if group_name:
        group, _ = OrganizationGroup.objects.get_or_create(
            team=assignment.team,
            name=group_name,
            defaults={
                "group_type": OrganizationGroup.GroupType.PROGRAM,
                "description": "IEA program structure mirrored from legacy committee assignments.",
                "active": True,
            },
        )

    committee, _ = Committee.objects.get_or_create(
        team=assignment.team,
        group=group,
        name=committee_name,
        defaults={"active": True},
    )

    notes = "Mirrored from legacy IEA committee assignment."
    if assignment.notes:
        notes = f"{notes} {assignment.notes}"[:255]

    membership, _ = CommitteeMembership.objects.update_or_create(
        legacy_committee_assignment=assignment,
        defaults={
            "committee": committee,
            "person": person,
            "position": position,
            "start_date": assignment.season.start_date,
            "end_date": assignment.season.end_date,
            "active": assignment.active,
            "notes": notes,
        },
    )
    return membership


def remove_legacy_committee_membership(assignment):
    CommitteeMembership.objects.filter(legacy_committee_assignment=assignment).delete()
