from django.db import migrations, models
import django.db.models.deletion


def backfill_primary_people(apps, schema_editor):
    Account = apps.get_model("portal", "ReceivableAccount")
    Relationship = apps.get_model("portal", "ReceivableAccountPerson")
    for account in Account.objects.exclude(primary_person_id=None).iterator():
        Relationship.objects.get_or_create(
            account_id=account.pk,
            person_id=account.primary_person_id,
            defaults={"role": "responsible_party", "statement_recipient": True, "active": True},
        )


class Migration(migrations.Migration):
    dependencies = [("portal", "0094_v350_finance_capabilities")]
    operations = [
        migrations.CreateModel(
            name="ReceivableAccountPerson",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("responsible_party", "Responsible party"), ("billing_contact", "Billing contact"), ("participant", "Rider / participant"), ("statement_recipient", "Statement recipient")], default="participant", max_length=24)),
                ("statement_recipient", models.BooleanField(default=False)),
                ("active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="people_links", to="portal.receivableaccount")),
                ("person", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="receivable_account_links", to="portal.person")),
            ],
            options={"ordering": ["account_id", "role", "person_id"]},
        ),
        migrations.AddConstraint(model_name="receivableaccountperson", constraint=models.UniqueConstraint(fields=("account", "person", "role"), name="unique_receivable_account_person_role")),
        migrations.RunPython(backfill_primary_people, migrations.RunPython.noop),
    ]
