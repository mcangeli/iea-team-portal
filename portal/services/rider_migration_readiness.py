"""Read-only v3.9 migration-readiness audit for legacy Rider/IEA data."""

from dataclasses import dataclass, field

from django.db.models import Count

from portal.model_modules.people import IEAParticipant, LegacyPersonLink
from portal.models import Rider, SeasonMembership


@dataclass(frozen=True)
class RiderMigrationIssue:
    code: str
    rider_id: int
    message: str


@dataclass
class RiderMigrationReadinessReport:
    riders_scanned: int = 0
    riders_with_person_bridge: int = 0
    riders_without_person_bridge: int = 0
    riders_with_iea_participant: int = 0
    riders_without_iea_participant: int = 0
    season_memberships_scanned: int = 0
    season_memberships_ready: int = 0
    season_memberships_blocked: int = 0
    duplicate_member_numbers: list[str] = field(default_factory=list)
    issues: list[RiderMigrationIssue] = field(default_factory=list)

    @property
    def issue_count(self):
        return len(self.issues)

    @property
    def ready(self):
        return self.issue_count == 0 and self.season_memberships_blocked == 0


def audit_rider_migration_readiness(*, team=None):
    """Measure whether legacy Rider/SeasonMembership rows can map deterministically.

    This function never creates or updates records. Identity is accepted only
    through the explicit LegacyPersonLink -> Rider bridge.
    """
    riders = Rider.objects.all().order_by("id")
    memberships = SeasonMembership.objects.all()
    participants = IEAParticipant.objects.all()
    if team is not None:
        riders = riders.filter(team=team)
        memberships = memberships.filter(season__team=team)
        participants = participants.filter(team=team)

    report = RiderMigrationReadinessReport()
    report.riders_scanned = riders.count()
    report.season_memberships_scanned = memberships.count()

    duplicate_numbers = (
        participants.exclude(iea_member_number="")
        .values("team_id", "iea_member_number")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
        .order_by("team_id", "iea_member_number")
    )
    for row in duplicate_numbers:
        report.duplicate_member_numbers.append(
            f"team={row['team_id']} member_number={row['iea_member_number']} count={row['total']}"
        )

    for rider in riders:
        link = LegacyPersonLink.objects.filter(rider=rider).select_related("person").first()
        if not link:
            report.riders_without_person_bridge += 1
            report.issues.append(RiderMigrationIssue(
                "missing_person_bridge", rider.id,
                "Rider has no deterministic LegacyPersonLink to Person.",
            ))
            continue

        report.riders_with_person_bridge += 1
        person = link.person
        if person.team_id != rider.team_id:
            report.issues.append(RiderMigrationIssue(
                "team_mismatch", rider.id,
                f"Person {person.id} and Rider belong to different organizations.",
            ))

        participant = IEAParticipant.objects.filter(person=person).first()
        if participant is None:
            report.riders_without_iea_participant += 1
            report.issues.append(RiderMigrationIssue(
                "missing_iea_participant", rider.id,
                f"Person {person.id} has no IEAParticipant.",
            ))
        else:
            report.riders_with_iea_participant += 1
            if participant.team_id != rider.team_id:
                report.issues.append(RiderMigrationIssue(
                    "iea_team_mismatch", rider.id,
                    f"IEAParticipant {participant.id} belongs to another organization.",
                ))
            if participant.legacy_rider_id != rider.id:
                report.issues.append(RiderMigrationIssue(
                    "iea_bridge_mismatch", rider.id,
                    f"IEAParticipant {participant.id} does not point back to this Rider.",
                ))
            if (
                participant.iea_member_number
                and rider.iea_member_number
                and participant.iea_member_number != rider.iea_member_number
            ):
                report.issues.append(RiderMigrationIssue(
                    "member_number_mismatch", rider.id,
                    "Person-native and legacy IEA member numbers differ.",
                ))

    for membership in memberships.select_related("rider", "season"):
        rider = membership.rider
        link = LegacyPersonLink.objects.filter(rider=rider).select_related("person").first()
        participant = (
            IEAParticipant.objects.filter(person=link.person).first()
            if link else None
        )
        valid = bool(
            link
            and link.person.team_id == rider.team_id == membership.season.team_id
            and participant
            and participant.team_id == rider.team_id
            and participant.legacy_rider_id == rider.id
        )
        if valid:
            report.season_memberships_ready += 1
        else:
            report.season_memberships_blocked += 1

    return report
