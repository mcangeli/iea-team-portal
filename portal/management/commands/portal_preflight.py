from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


INITIAL_SCHEMAS = {
    ("contenttypes", "0001_initial"): {"django_content_type"},
    ("auth", "0001_initial"): {
        "auth_permission", "auth_group", "auth_group_permissions", "auth_user",
        "auth_user_groups", "auth_user_user_permissions",
    },
    ("admin", "0001_initial"): {"django_admin_log"},
    ("sessions", "0001_initial"): {"django_session"},
    ("portal", "0001_initial"): {
        "portal_team", "portal_season", "portal_userprofile", "portal_rider",
        "portal_rider_guardians", "portal_seasonmembership", "portal_announcement",
        "portal_calendarevent",
    },
}


class Command(BaseCommand):
    help = "Check for partial initial schemas before Django migrations run."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))
            applied = set()
            if "django_migrations" in tables:
                cursor.execute("SELECT app, name FROM django_migrations")
                applied = set(cursor.fetchall())

        problems = []
        for migration, expected in INITIAL_SCHEMAS.items():
            if migration in applied:
                continue
            present = expected & tables
            if present and present != expected:
                problems.append((migration, sorted(present), sorted(expected - present)))

        if problems:
            for (app, name), present, missing in problems:
                self.stderr.write(self.style.ERROR(f"Partial schema detected for {app}.{name}."))
                self.stderr.write(f"  Present: {', '.join(present)}")
                self.stderr.write(f"  Missing: {', '.join(missing)}")
            raise CommandError(
                "Migration preflight stopped startup because an initial Django schema is only partially present. "
                "Restore/reconcile that schema before running migrations; do not use --fake blindly."
            )

        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            pending = [f"{migration.app_label}.{migration.name}" for migration, _backwards in plan]
            self.stdout.write(
                self.style.WARNING(
                    f"Portal migration preflight passed with {len(pending)} pending migration(s)."
                )
            )
            for migration_name in pending[:25]:
                self.stdout.write(f"  pending: {migration_name}")
            if len(pending) > 25:
                self.stdout.write(f"  ... and {len(pending) - 25} more")
        else:
            self.stdout.write(self.style.SUCCESS("Portal migration preflight passed. No pending migrations."))
