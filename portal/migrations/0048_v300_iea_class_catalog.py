from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0047_v250_host_family_publication"),
    ]

    operations = [
        migrations.CreateModel(
            name="IEAClassCatalogEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rulebook_season", models.CharField(help_text="Canonical IEA rulebook season, for example 2026-2027.", max_length=20)),
                ("discipline", models.CharField(choices=[("hunt_seat", "Hunt Seat"), ("western", "Western"), ("dressage", "Dressage")], max_length=30)),
                ("class_code", models.CharField(max_length=30)),
                ("official_name", models.CharField(max_length=200)),
                ("team_level", models.CharField(choices=[("futures", "Futures Team"), ("upper", "Upper School Team"), ("both", "Both teams")], max_length=20)),
                ("ability_level", models.CharField(blank=True, max_length=40)),
                ("class_family", models.CharField(blank=True, max_length=60)),
                ("individual_points_enabled", models.BooleanField(default=True)),
                ("team_points_enabled", models.BooleanField(default=True)),
                ("season_assignable", models.BooleanField(default=True, help_text="Whether this class is a normal rider/season placement class.")),
                ("active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("source_rule", models.CharField(blank=True, max_length=80)),
                ("source_revision_date", models.DateField(blank=True, null=True)),
            ],
            options={
                "ordering": ["rulebook_season", "discipline", "sort_order", "class_code"],
            },
        ),
        migrations.AddConstraint(
            model_name="ieaclasscatalogentry",
            constraint=models.UniqueConstraint(fields=("rulebook_season", "discipline", "class_code"), name="unique_iea_catalog_class_version"),
        ),
        migrations.AddIndex(
            model_name="ieaclasscatalogentry",
            index=models.Index(fields=["rulebook_season", "discipline", "active"], name="iea_catalog_version_idx"),
        ),
    ]
