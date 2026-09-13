from django.db import migrations


def seed_voc(apps, schema_editor):
    Entry = apps.get_model("portal", "IEAClassCatalogEntry")
    Entry.objects.update_or_create(
        rulebook_season="2026-2027",
        discipline="hunt_seat",
        class_code="VOC",
        defaults={
            "official_name": "Hunt Seat Varsity Open Championship (VOC)",
            "team_level": "upper",
            "ability_level": "open",
            "class_family": "championship",
            "individual_points_enabled": False,
            "team_points_enabled": False,
            "season_assignable": False,
            "active": True,
            "sort_order": 90,
            "source_rule": "H3303.2",
        },
    )


def remove_voc(apps, schema_editor):
    Entry = apps.get_model("portal", "IEAClassCatalogEntry")
    Entry.objects.filter(
        rulebook_season="2026-2027",
        discipline="hunt_seat",
        class_code="VOC",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0054_v300_seed_iea_show_only_warmups"),
    ]

    operations = [
        migrations.RunPython(seed_voc, remove_voc),
    ]
