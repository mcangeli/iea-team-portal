from django.db import migrations


SHOW_ONLY_ROWS = [
    (
        "hunt_seat",
        "H7x/H8x",
        "Junior Varsity Beginner Equitation on the Flat - Walk/Trot Warm-Up",
        "upper",
        "beginner",
        "warm_up",
        8,
        "H3301",
    ),
    (
        "hunt_seat",
        "H13x/H14x",
        "Future Beginner Equitation on the Flat - Walk/Trot Warm-Up",
        "futures",
        "beginner",
        "warm_up",
        14,
        "H3302",
    ),
    (
        "western",
        "W7x/W8x",
        "Junior Varsity Beginner Horsemanship - Walk/Jog Warm-Up",
        "upper",
        "beginner",
        "warm_up",
        8,
        "W3301",
    ),
    (
        "western",
        "W13x/W14x",
        "Future Beginner Horsemanship - Walk/Jog Warm-Up",
        "futures",
        "beginner",
        "warm_up",
        14,
        "W3301",
    ),
    (
        "dressage",
        "D7x/D8x",
        "Junior Varsity Beginner Dressage Seat Equitation - Walk/Trot Warm-Up",
        "upper",
        "beginner",
        "warm_up",
        8,
        "D3301",
    ),
    (
        "dressage",
        "D13x/D14x",
        "Future Beginner Equitation on the Flat - Walk/Trot Warm-Up",
        "futures",
        "beginner",
        "warm_up",
        14,
        "D3302",
    ),
]


def seed_show_only_warmups(apps, schema_editor):
    Entry = apps.get_model("portal", "IEAClassCatalogEntry")
    for discipline, class_code, official_name, team_level, ability_level, class_family, sort_order, source_rule in SHOW_ONLY_ROWS:
        Entry.objects.update_or_create(
            rulebook_season="2026-2027",
            discipline=discipline,
            class_code=class_code,
            defaults={
                "official_name": official_name,
                "team_level": team_level,
                "ability_level": ability_level,
                "class_family": class_family,
                "individual_points_enabled": False,
                "team_points_enabled": False,
                "season_assignable": False,
                "active": True,
                "sort_order": sort_order,
                "source_rule": source_rule,
            },
        )


def remove_show_only_warmups(apps, schema_editor):
    Entry = apps.get_model("portal", "IEAClassCatalogEntry")
    keys = [(discipline, code) for discipline, code, *_rest in SHOW_ONLY_ROWS]
    for discipline, code in keys:
        Entry.objects.filter(
            rulebook_season="2026-2027",
            discipline=discipline,
            class_code=code,
            season_assignable=False,
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0053_v300_showclass_catalog_link"),
    ]

    operations = [
        migrations.RunPython(seed_show_only_warmups, remove_show_only_warmups),
    ]
