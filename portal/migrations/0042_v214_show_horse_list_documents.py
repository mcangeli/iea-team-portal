from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0041_v214_horse_eligibility_override"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ShowHorseListDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("revision", models.PositiveIntegerField()),
                ("document", models.FileField(upload_to="show_horse_lists/%Y/%m/")),
                ("source_name", models.CharField(blank=True, help_text="Optional source, host team, or label for this horse list.", max_length=160)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("family_notes", models.TextField(blank=True, help_text="Coach notes intentionally shared with riders and parents for this show horse list.")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("show", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="horse_list_documents", to="portal.show")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="uploaded_show_horse_lists", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-revision", "-uploaded_at"]},
        ),
        migrations.AddConstraint(
            model_name="showhorselistdocument",
            constraint=models.UniqueConstraint(fields=("show", "revision"), name="unique_horse_list_revision_per_show"),
        ),
    ]
