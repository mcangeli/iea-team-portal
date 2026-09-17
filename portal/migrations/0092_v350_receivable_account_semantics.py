from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0091_v350_finance_domains_and_legacy_backfill")]

    operations = [
        migrations.RemoveConstraint(
            model_name="receivableaccount",
            name="unique_receivable_account_team_name",
        ),
        migrations.AddConstraint(
            model_name="receivableaccount",
            constraint=models.UniqueConstraint(
                fields=("team", "finance_domain", "name"),
                name="unique_receivable_account_team_domain_name",
            ),
        ),
    ]
