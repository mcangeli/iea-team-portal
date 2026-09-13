from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0049_v300_seed_iea_class_catalog"),
    ]

    operations = [
        migrations.AddField(
            model_name="seasonclass",
            name="catalog_entry",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional official IEA class definition for this season-specific class.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="season_classes",
                to="portal.ieaclasscatalogentry",
            ),
        ),
    ]
