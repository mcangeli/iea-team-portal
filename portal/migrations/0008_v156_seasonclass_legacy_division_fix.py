from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("portal", "0007_v155_user_onboarding")]

    operations = [
        # v1.3.0 removed SeasonClass.division from Django's model state but
        # intentionally retained the physical PostgreSQL column for historical
        # upgrade safety. Migration 0003 had removed that column's DB default,
        # leaving it NOT NULL with no value supplied by new ORM INSERTs.
        #
        # Preserve the legacy data/column, but restore a harmless empty-string
        # database default so new SeasonClass rows can be created normally.
        # This is database-only because `division` intentionally remains absent
        # from Django's active SeasonClass model state.
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=r"""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_schema = current_schema()
                              AND table_name = 'portal_seasonclass'
                              AND column_name = 'division'
                        ) THEN
                            ALTER TABLE portal_seasonclass
                                ALTER COLUMN division SET DEFAULT '';
                            UPDATE portal_seasonclass
                                SET division = ''
                                WHERE division IS NULL;
                            ALTER TABLE portal_seasonclass
                                ALTER COLUMN division SET NOT NULL;
                        END IF;
                    END $$;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=[],
        ),
    ]
