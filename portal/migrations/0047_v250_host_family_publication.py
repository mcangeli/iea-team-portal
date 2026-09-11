from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0046_v250_host_show_duties"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HostShowFamilyPublication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("published", models.BooleanField(default=False, help_text="Make the selected host-show information visible to authenticated team riders and families.")),
                ("publish_arrival", models.BooleanField(default=False)),
                ("publish_parking", models.BooleanField(default=False)),
                ("publish_warmup", models.BooleanField(default=False)),
                ("publish_ring_operations", models.BooleanField(default=False)),
                ("publish_hospitality", models.BooleanField(default=False)),
                ("publish_emergency", models.BooleanField(default=False)),
                ("publish_documents", models.BooleanField(default=False)),
                ("publish_family_notes", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("operations", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="family_publication", to="portal.hostshowoperations")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_host_family_publications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "host show family publication"},
        ),
    ]
