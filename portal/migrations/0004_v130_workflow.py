from datetime import datetime, time

from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def sync_existing_shows(apps, schema_editor):
    Show = apps.get_model("portal", "Show")
    CalendarEvent = apps.get_model("portal", "CalendarEvent")
    tz = timezone.get_current_timezone()
    for show in Show.objects.all().iterator():
        starts_at = timezone.make_aware(datetime.combine(show.show_date, show.start_time or time(0, 0)), tz)
        location = " · ".join(part for part in [show.venue, show.address] if part)
        CalendarEvent.objects.update_or_create(
            show_id=show.id,
            defaults={
                "team_id": show.team_id,
                "season_id": show.season_id,
                "title": show.name,
                "kind": "show",
                "starts_at": starts_at,
                "ends_at": None,
                "all_day": not bool(show.start_time),
                "location": location,
                "description": show.notes,
                "visible_to_all": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("portal", "0003_team_levels_season_classes_guardians")]

    operations = [
        # Division was a redundant class-setup concept. Remove it from Django's
        # active model state but intentionally retain the old physical DB column
        # as harmless legacy data for safer upgrades from drifted v1.2 schemas.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[migrations.RemoveField(model_name="seasonclass", name="division")],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=r"""
                    ALTER TABLE portal_calendarevent
                        ADD COLUMN IF NOT EXISTS all_day boolean NOT NULL DEFAULT false;
                    ALTER TABLE portal_calendarevent ALTER COLUMN all_day DROP DEFAULT;
                    ALTER TABLE portal_calendarevent
                        ADD COLUMN IF NOT EXISTS show_id bigint NULL;

                    DO $$ BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint
                            WHERE conname='portal_calendarevent_show_id_fk'
                              AND conrelid='portal_calendarevent'::regclass
                        ) THEN
                            ALTER TABLE portal_calendarevent
                                ADD CONSTRAINT portal_calendarevent_show_id_fk
                                FOREIGN KEY (show_id) REFERENCES portal_show(id)
                                DEFERRABLE INITIALLY DEFERRED;
                        END IF;
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint
                            WHERE conname='portal_calendarevent_show_id_uniq'
                              AND conrelid='portal_calendarevent'::regclass
                        ) THEN
                            ALTER TABLE portal_calendarevent
                                ADD CONSTRAINT portal_calendarevent_show_id_uniq UNIQUE (show_id);
                        END IF;
                    END $$;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="calendarevent",
                    name="all_day",
                    field=models.BooleanField(default=False),
                ),
                migrations.AddField(
                    model_name="calendarevent",
                    name="show",
                    field=models.OneToOneField(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                        related_name="calendar_event", to="portal.show"
                    ),
                ),
            ],
        ),
        migrations.RunPython(sync_existing_shows, migrations.RunPython.noop),
    ]
