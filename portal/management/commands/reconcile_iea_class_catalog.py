from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from portal.iea_catalog_reconciliation import reconcile_season_classes
from portal.models import Season, SeasonClass


class Command(BaseCommand):
    help = (
        "Report or apply deterministic links from legacy SeasonClass rows to "
        "the versioned IEA class catalog. Dry-run is the default."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--rulebook-season",
            required=True,
            help="Catalog rulebook season, for example 2026-2027.",
        )
        parser.add_argument(
            "--season-id",
            type=int,
            help="Limit reconciliation to one ArenaLine Season primary key.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist exact matches. Without this flag, no data is changed.",
        )

    def handle(self, *args, **options):
        rulebook_season = options["rulebook_season"].strip()
        season_id = options.get("season_id")
        apply = bool(options.get("apply"))

        queryset = SeasonClass.objects.all()
        if season_id is not None:
            if not Season.objects.filter(pk=season_id).exists():
                raise CommandError(f"Season {season_id} does not exist.")
            queryset = queryset.filter(season_id=season_id)

        results = reconcile_season_classes(
            queryset,
            rulebook_season=rulebook_season,
            apply=apply,
        )

        counts = Counter(result.status for result in results)
        action = "APPLY" if apply else "DRY RUN"
        self.stdout.write(f"IEA class reconciliation · {action}")
        self.stdout.write(f"Rulebook season: {rulebook_season}")
        if season_id is not None:
            self.stdout.write(f"ArenaLine season id: {season_id}")
        self.stdout.write("")

        for result in results:
            suffix = f" -> catalog {result.catalog_entry_id}" if result.catalog_entry_id else ""
            reason = f" ({result.reason})" if result.reason else ""
            self.stdout.write(
                f"SeasonClass {result.season_class_id}: {result.status}{suffix}{reason}"
            )

        self.stdout.write("")
        self.stdout.write(
            "Summary: " + ", ".join(
                f"{status}={count}" for status, count in sorted(counts.items())
            )
        )
        if not apply:
            self.stdout.write(self.style.WARNING(
                "Dry run only. Re-run with --apply to persist exact matches."
            ))
