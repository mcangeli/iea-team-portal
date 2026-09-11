from django.db import migrations


SEQUENCE_REPAIR_SQL = """
DO $$
DECLARE
    seq_name text;
    max_id bigint;
BEGIN
    -- auth_user
    SELECT pg_get_serial_sequence('auth_user', 'id') INTO seq_name;
    IF seq_name IS NOT NULL THEN
        SELECT MAX(id) INTO max_id FROM auth_user;
        IF max_id IS NULL THEN
            EXECUTE format('SELECT setval(%L, 1, false)', seq_name);
        ELSE
            EXECUTE format('SELECT setval(%L, %s, true)', seq_name, max_id);
        END IF;
    END IF;

    -- portal_userprofile
    SELECT pg_get_serial_sequence('portal_userprofile', 'id') INTO seq_name;
    IF seq_name IS NOT NULL THEN
        SELECT MAX(id) INTO max_id FROM portal_userprofile;
        IF max_id IS NULL THEN
            EXECUTE format('SELECT setval(%L, 1, false)', seq_name);
        ELSE
            EXECUTE format('SELECT setval(%L, %s, true)', seq_name, max_id);
        END IF;
    END IF;
END $$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0012_v180_team_hub"),
    ]

    operations = [
        migrations.RunSQL(SEQUENCE_REPAIR_SQL, migrations.RunSQL.noop),
    ]
