from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0022_v19422_itemized_show_budget"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[
                    ("created", "Created"), ("updated", "Updated"), ("submitted", "Submitted"),
                    ("approved", "Approved"), ("rejected", "Rejected"), ("paid", "Paid"),
                    ("voided", "Voided"), ("restored", "Restored"), ("allocated", "Allocated"),
                    ("removed", "Removed"), ("generated", "Generated"),
                ], max_length=24)),
                ("entity_type", models.CharField(max_length=80)),
                ("entity_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("entity_label", models.CharField(max_length=255)),
                ("summary", models.CharField(max_length=255)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="portal_audit_events", to=settings.AUTH_USER_MODEL)),
                ("season", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_events", to="portal.season")),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="portal.team")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddField(
            model_name="familypayment",
            name="status",
            field=models.CharField(choices=[("posted", "Posted"), ("void", "Void")], default="posted", max_length=12),
        ),
        migrations.AddField(
            model_name="familypayment",
            name="void_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="familypayment",
            name="voided_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="familypayment",
            name="voided_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="family_payments_voided", to=settings.AUTH_USER_MODEL),
        ),
    ]
