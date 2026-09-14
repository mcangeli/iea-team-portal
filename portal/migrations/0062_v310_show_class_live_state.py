from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0061_v310_show_live_lifecycle"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ShowClassLiveState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("not_started", "Not started"), ("in_progress", "In progress"), ("paused", "Paused"), ("complete", "Complete")], default="not_started", max_length=20)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("show_class", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="live_state", to="portal.showclass")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="show_class_live_states_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["show_class__sort_order", "show_class__class_number", "show_class_id"],
            },
        ),
    ]
