from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0052_v300_seasonclass_multidiscipline_uniqueness"),
    ]

    operations = [
        migrations.AddField(
            model_name="showclass",
            name="catalog_entry",
            field=models.ForeignKey(
                blank=True,
                help_text="Official show-only IEA class definition when no SeasonClass should be created.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="direct_show_classes",
                to="portal.ieaclasscatalogentry",
            ),
        ),
    ]
