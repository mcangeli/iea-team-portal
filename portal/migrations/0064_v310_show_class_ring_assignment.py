from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0063_v310_class_result_publication"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ShowClassRingAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ring", models.CharField(blank=True, help_text="Show-day ring name, such as 'Ring 1', 'Ring 2', or 'Main Arena'. Blank uses Main ring.", max_length=80)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("show_class", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="ring_assignment", to="portal.showclass")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="show_class_ring_assignments_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["ring", "show_class__sort_order", "show_class_id"],
            },
        ),
    ]
