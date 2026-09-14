from django.db import migrations
from django.db.models import Q


def reconcile_non_team_entries(apps, schema_editor):
    ShowEntry = apps.get_model("portal", "ShowEntry")

    non_team = ShowEntry.objects.filter(
        Q(show_class__season_class__catalog_entry__team_points_enabled=False)
        | Q(show_class__catalog_entry__team_points_enabled=False)
    )

    regular = non_team.filter(show_class__show__competition_level="regular")
    regular.update(is_point_rider=False, entry_type="individual")

    finals = non_team.exclude(show_class__show__competition_level="regular")
    finals.update(
        is_point_rider=False,
        entry_type="individual",
        competition_track="individual",
    )


def noop_reverse(apps, schema_editor):
    # The prior point-rider/team-entry state cannot be reconstructed safely.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0055_v300_seed_iea_voc"),
    ]

    operations = [
        migrations.RunPython(reconcile_non_team_entries, noop_reverse),
    ]
