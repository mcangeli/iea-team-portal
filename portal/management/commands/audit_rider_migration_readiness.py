from django.core.management.base import BaseCommand, CommandError

from portal.models import Team
from portal.services.rider_migration_readiness import audit_rider_migration_readiness


class Command(BaseCommand):
    help = "Read-only v3.9 audit of Rider/Person/IEA/SeasonMembership migration readiness."

    def add_arguments(self, parser):
        parser.add_argument("--team-id", type=int, help="Limit the audit to one Team primary key.")

    def handle(self, *args, **options):
        team = None
        if options.get("team_id"):
            try:
                team = Team.objects.get(pk=options["team_id"])
            except Team.DoesNotExist as exc:
                raise CommandError(f"Team {options['team_id']} does not exist.") from exc

        report = audit_rider_migration_readiness(team=team)
        self.stdout.write(self.style.MIGRATE_HEADING("v3.9 Rider migration readiness — READ ONLY"))
        self.stdout.write(f"Riders scanned: {report.riders_scanned}")
        self.stdout.write(f"Riders with Person bridge: {report.riders_with_person_bridge}")
        self.stdout.write(f"Riders without Person bridge: {report.riders_without_person_bridge}")
        self.stdout.write(f"Riders with IEAParticipant: {report.riders_with_iea_participant}")
        self.stdout.write(f"Riders without IEAParticipant: {report.riders_without_iea_participant}")
        self.stdout.write(f"Season memberships scanned: {report.season_memberships_scanned}")
        self.stdout.write(f"Season memberships ready: {report.season_memberships_ready}")
        self.stdout.write(f"Season memberships blocked: {report.season_memberships_blocked}")
        self.stdout.write(f"Duplicate Person-native member numbers: {len(report.duplicate_member_numbers)}")
        for item in report.duplicate_member_numbers:
            self.stdout.write(self.style.WARNING(f"  {item}"))
        self.stdout.write(f"Issues: {report.issue_count}")
        for issue in report.issues:
            self.stdout.write(self.style.WARNING(
                f"  Rider {issue.rider_id} [{issue.code}]: {issue.message}"
            ))
        if report.ready:
            self.stdout.write(self.style.SUCCESS(
                "All audited SeasonMembership rows are ready for a Person-native additive link."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "Readiness blockers remain. No data was changed."
            ))
