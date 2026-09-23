from django.core.management.base import BaseCommand, CommandError

from portal.models import Team
from portal.people_compat import backfill_iea_participants


class Command(BaseCommand):
    help = (
        "Create deterministic v3.9 IEAParticipant rows from existing "
        "LegacyPersonLink -> Rider bridges. Dry-run is the default."
    )

    def add_arguments(self, parser):
        parser.add_argument("--team-id", type=int, help="Limit the backfill to one Team primary key.")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist the deterministic backfill. Without this flag no data is changed.",
        )

    def handle(self, *args, **options):
        team = None
        if options.get("team_id"):
            try:
                team = Team.objects.get(pk=options["team_id"])
            except Team.DoesNotExist as exc:
                raise CommandError(f"Team {options['team_id']} does not exist.") from exc

        if not options["apply"]:
            self.stdout.write(self.style.MIGRATE_HEADING("v3.9 IEA participant backfill — DRY RUN"))
            self.stdout.write(
                "No data was changed. The existing readiness audit should be used "
                "to review deterministic bridges before applying."
            )
            return

        report = backfill_iea_participants(team=team)
        self.stdout.write(self.style.MIGRATE_HEADING("v3.9 IEA participant backfill — APPLIED"))
        self.stdout.write(f"Created: {report['created']}")
        self.stdout.write(f"Existing: {report['existing']}")
        self.stdout.write(f"Conflicts: {len(report['conflicts'])}")
        for conflict in report["conflicts"]:
            self.stdout.write(self.style.WARNING(f"  {conflict}"))

        if report["conflicts"]:
            self.stdout.write(self.style.WARNING(
                "Backfill completed with conflicts. Review them before SeasonMembership migration."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "Deterministic IEA participant backfill completed without conflicts."
            ))
