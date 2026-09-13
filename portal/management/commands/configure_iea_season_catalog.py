from django.core.management.base import BaseCommand, CommandError

from portal.iea_catalog_season_setup import configure_iea_season_catalog
from portal.models import Season
from portal.model_modules.competition_iea import IEAClassCatalogEntry


class Command(BaseCommand):
    help = "Configure one ArenaLine season from a versioned official IEA class catalog."

    def add_arguments(self, parser):
        parser.add_argument("--season-id", type=int, required=True)
        parser.add_argument("--rulebook-season", required=True)
        parser.add_argument(
            "--discipline",
            action="append",
            dest="disciplines",
            choices=[value for value, _label in IEAClassCatalogEntry.Discipline.choices],
            required=True,
            help="Repeat for each participating discipline.",
        )

    def handle(self, *args, **options):
        try:
            season = Season.objects.get(pk=options["season_id"])
        except Season.DoesNotExist as exc:
            raise CommandError(f"Season {options['season_id']} does not exist.") from exc

        try:
            result = configure_iea_season_catalog(
                season=season,
                rulebook_season=options["rulebook_season"],
                disciplines=options["disciplines"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(f"IEA catalog configured for {season}.")
        self.stdout.write(f"Created: {result.created}")
        self.stdout.write(f"Reused: {result.reused}")
        self.stdout.write(f"Linked legacy: {result.linked_legacy}")
        self.stdout.write(f"Conflicts: {len(result.conflicts)}")
        for conflict in result.conflicts:
            self.stdout.write(self.style.WARNING(f"- {conflict}"))
