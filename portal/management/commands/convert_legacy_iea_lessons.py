from django.core.management.base import BaseCommand, CommandError

from portal.models import Season, Team
from portal.services.legacy_iea_lessons import convert_legacy_iea_lessons


class Command(BaseCommand):
    help = "Report or convert legacy IEA Lesson/LessonAttendance records into the v3.4 lesson engine."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write the conversion. Without this flag the command is dry-run only.")
        parser.add_argument("--team-id", type=int, help="Limit conversion to one Team primary key.")
        parser.add_argument("--season-id", type=int, help="Limit conversion to one Season primary key.")

    def handle(self, *args, **options):
        team = None
        season = None
        if options.get("team_id"):
            try:
                team = Team.objects.get(pk=options["team_id"])
            except Team.DoesNotExist as exc:
                raise CommandError(f"Team {options['team_id']} does not exist.") from exc
        if options.get("season_id"):
            try:
                season = Season.objects.select_related("team").get(pk=options["season_id"])
            except Season.DoesNotExist as exc:
                raise CommandError(f"Season {options['season_id']} does not exist.") from exc
        if team and season and season.team_id != team.id:
            raise CommandError("The selected season does not belong to the selected team.")

        dry_run = not options["apply"]
        report = convert_legacy_iea_lessons(team=team, season=season, dry_run=dry_run)

        mode = "DRY RUN" if dry_run else "APPLIED"
        self.stdout.write(self.style.MIGRATE_HEADING(f"Legacy IEA lesson conversion — {mode}"))
        self.stdout.write(f"Lessons scanned: {report.lessons_scanned}")
        self.stdout.write(f"Convertible: {report.lessons_convertible}")
        self.stdout.write(f"Programs created: {report.programs_created}")
        self.stdout.write(f"Series created: {report.series_created}")
        self.stdout.write(f"Occurrences created/existing: {report.occurrences_created}/{report.occurrences_existing}")
        self.stdout.write(f"Attendance created/existing: {report.attendance_created}/{report.attendance_existing}")
        self.stdout.write(f"Assignments created/existing: {report.assignments_created}/{report.assignments_existing}")
        self.stdout.write(f"Issues: {report.issue_count}")
        for issue in report.issues:
            self.stdout.write(self.style.WARNING(f"  Lesson {issue.lesson_id}: {issue.message}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("No changes written. Re-run with --apply after reviewing the report."))
        elif report.issue_count:
            self.stdout.write(self.style.WARNING("Conversion completed with unresolved lessons; legacy records remain unchanged."))
        else:
            self.stdout.write(self.style.SUCCESS("Conversion completed; legacy records remain unchanged for compatibility."))
