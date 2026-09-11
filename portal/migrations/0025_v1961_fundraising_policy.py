from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0024_v196_fundraising"),
    ]

    operations = [
        migrations.CreateModel(
            name="FundraisingPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("model", models.CharField(
                    choices=[
                        ("team_wide", "Team-wide"),
                        ("family_credit", "Family credit"),
                        ("hybrid", "Hybrid"),
                    ],
                    default="team_wide",
                    max_length=24,
                )),
                ("default_family_credit_percent", models.DecimalField(
                    decimal_places=2,
                    default=0,
                    help_text="Default percentage of an attributed contribution applied to the family account.",
                    max_digits=5,
                )),
                ("participation_optional", models.BooleanField(default=True)),
                ("allowed_charge_types", models.JSONField(
                    blank=True,
                    default=list,
                    help_text="Family charge types that fundraising credits may reduce. Empty means any charge type.",
                )),
                ("family_message", models.TextField(
                    blank=True,
                    help_text="Plain-language fundraising policy shown to linked Parent/Guardian accounts.",
                )),
                ("notes", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("season", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="fundraising_policy",
                    to="portal.season",
                )),
                ("updated_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="fundraising_policies_updated",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
