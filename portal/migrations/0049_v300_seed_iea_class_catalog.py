from django.db import migrations


CATALOG_ROWS = [
    ("hunt_seat", "H1", "Varsity Open Equitation Over Fences 2'6\"", "upper", "open", "over_fences", True, 1, "H3301"),
    ("hunt_seat", "H2", "Varsity Open Equitation on the Flat", "upper", "open", "flat", True, 2, "H3301"),
    ("hunt_seat", "H3", "Varsity Intermediate Equitation Over Fences 2'", "upper", "intermediate", "over_fences", True, 3, "H3301"),
    ("hunt_seat", "H4", "Varsity Intermediate Equitation on the Flat", "upper", "intermediate", "flat", True, 4, "H3301"),
    ("hunt_seat", "H5", "Junior Varsity Novice Equitation Over Fences X-rails", "upper", "novice", "over_fences", True, 5, "H3301"),
    ("hunt_seat", "H6", "Junior Varsity Novice Equitation on the Flat", "upper", "novice", "flat", True, 6, "H3301"),
    ("hunt_seat", "H7", "Junior Varsity Beginner Equitation on the Flat - Walk/Trot/Canter", "upper", "beginner", "flat", True, 7, "H3301"),
    ("hunt_seat", "H8", "Junior Varsity Beginner Equitation on the Flat - Walk/Trot", "upper", "beginner", "flat", False, 8, "H3301"),
    ("hunt_seat", "H9", "Future Intermediate Equitation Over Fences 2'", "futures", "intermediate", "over_fences", True, 9, "H3302"),
    ("hunt_seat", "H10", "Future Intermediate Equitation on the Flat", "futures", "intermediate", "flat", True, 10, "H3302"),
    ("hunt_seat", "H11", "Future Novice Equitation Over Fences X-rails", "futures", "novice", "over_fences", True, 11, "H3302"),
    ("hunt_seat", "H12", "Future Novice Equitation on the Flat", "futures", "novice", "flat", True, 12, "H3302"),
    ("hunt_seat", "H13", "Future Beginner Equitation on the Flat - Walk/Trot/Canter", "futures", "beginner", "flat", True, 13, "H3302"),
    ("hunt_seat", "H14", "Future Beginner Equitation on the Flat - Walk/Trot", "futures", "beginner", "flat", False, 14, "H3302"),
    ("western", "W1", "Varsity Open Horsemanship", "upper", "open", "horsemanship", True, 1, "W3301"),
    ("western", "W2", "Varsity Open Reining", "upper", "open", "reining", True, 2, "W3302"),
    ("western", "W3", "Varsity Intermediate Horsemanship", "upper", "intermediate", "horsemanship", True, 3, "W3301"),
    ("western", "W4", "Varsity Intermediate Reining", "upper", "intermediate", "reining", True, 4, "W3302"),
    ("western", "W5", "Junior Varsity Novice Horsemanship", "upper", "novice", "horsemanship", True, 5, "W3301"),
    ("western", "W6", "Junior Varsity Novice Ranch Riding", "upper", "novice", "ranch_riding", True, 6, "W3302"),
    ("western", "W7", "Junior Varsity Beginner Horsemanship Walk/Jog/Lope", "upper", "beginner", "horsemanship", True, 7, "W3301"),
    ("western", "W8", "Junior Varsity Beginner Horsemanship Walk/Jog", "upper", "beginner", "horsemanship", False, 8, "W3301"),
    ("western", "W9", "Future Intermediate Horsemanship", "futures", "intermediate", "horsemanship", True, 9, "W3301"),
    ("western", "W10", "Future Intermediate Reining", "futures", "intermediate", "reining", True, 10, "W3302"),
    ("western", "W11", "Future Novice Horsemanship", "futures", "novice", "horsemanship", True, 11, "W3301"),
    ("western", "W12", "Future Novice Ranch Riding", "futures", "novice", "ranch_riding", True, 12, "W3302"),
    ("western", "W13", "Future Beginner Horsemanship Walk/Jog/Lope", "futures", "beginner", "horsemanship", True, 13, "W3301"),
    ("western", "W14", "Future Beginner Horsemanship Walk/Jog", "futures", "beginner", "horsemanship", False, 14, "W3301"),
    ("dressage", "D1", "Varsity Open Dressage Test", "upper", "open", "dressage_test", True, 1, "D3301"),
    ("dressage", "D2", "Varsity Open Dressage Seat Equitation (DSE)", "upper", "open", "dse", True, 2, "D3301"),
    ("dressage", "D3", "Varsity Intermediate Dressage Test", "upper", "intermediate", "dressage_test", True, 3, "D3301"),
    ("dressage", "D4", "Varsity Intermediate Dressage Seat Equitation", "upper", "intermediate", "dse", True, 4, "D3301"),
    ("dressage", "D5", "Junior Varsity Novice Dressage Test", "upper", "novice", "dressage_test", True, 5, "D3301"),
    ("dressage", "D6", "Junior Varsity Novice Dressage Seat Equitation", "upper", "novice", "dse", True, 6, "D3301"),
    ("dressage", "D7", "Junior Varsity Beginner Dressage Seat Equitation - Walk/Trot/Canter", "upper", "beginner", "dse", True, 7, "D3301"),
    ("dressage", "D8", "Junior Varsity Beginner Dressage Seat Equitation - Walk/Trot", "upper", "beginner", "dse", False, 8, "D3301"),
    ("dressage", "D9", "Future Intermediate Dressage Test", "futures", "intermediate", "dressage_test", True, 9, "D3302"),
    ("dressage", "D10", "Future Intermediate Dressage Seat Equitation", "futures", "intermediate", "dse", True, 10, "D3302"),
    ("dressage", "D11", "Future Novice Dressage Test", "futures", "novice", "dressage_test", True, 11, "D3302"),
    ("dressage", "D12", "Future Novice Dressage Seat Equitation", "futures", "novice", "dse", True, 12, "D3302"),
    ("dressage", "D13", "Future Beginner Dressage Seat Equitation - Walk/Trot/Canter", "futures", "beginner", "dse", True, 13, "D3302"),
    ("dressage", "D14", "Future Beginner Equitation on the Flat - Walk/Trot", "futures", "beginner", "dse", False, 14, "D3302"),
]


def seed_2026_2027_catalog(apps, schema_editor):
    Entry = apps.get_model("portal", "IEAClassCatalogEntry")
    for discipline, class_code, official_name, team_level, ability_level, class_family, team_points_enabled, sort_order, source_rule in CATALOG_ROWS:
        Entry.objects.update_or_create(
            rulebook_season="2026-2027",
            discipline=discipline,
            class_code=class_code,
            defaults={
                "official_name": official_name,
                "team_level": team_level,
                "ability_level": ability_level,
                "class_family": class_family,
                "individual_points_enabled": True,
                "team_points_enabled": team_points_enabled,
                "season_assignable": True,
                "active": True,
                "sort_order": sort_order,
                "source_rule": source_rule,
            },
        )


def remove_2026_2027_catalog(apps, schema_editor):
    Entry = apps.get_model("portal", "IEAClassCatalogEntry")
    Entry.objects.filter(rulebook_season="2026-2027").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0048_v300_iea_class_catalog"),
    ]

    operations = [
        migrations.RunPython(seed_2026_2027_catalog, remove_2026_2027_catalog),
    ]
