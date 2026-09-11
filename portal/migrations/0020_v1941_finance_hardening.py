from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("portal", "0019_v194_show_finance"),
    ]

    operations = [
        migrations.AddField(
            model_name="financialtransaction",
            name="show_finance_scope",
            field=models.CharField(
                blank=True,
                choices=[("participation", "Our team participation"), ("hosting", "Hosting operations")],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="financialtransaction",
            name="status",
            field=models.CharField(
                choices=[("posted", "Posted"), ("void", "Void")],
                default="posted",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="financialtransaction",
            name="voided_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="financialtransaction",
            name="void_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="financialtransaction",
            name="voided_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="financial_transactions_voided",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="financialtransaction",
            name="reversal_of",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reversals",
                to="portal.financialtransaction",
            ),
        ),
    ]
