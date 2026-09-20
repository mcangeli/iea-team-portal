from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0105_v371_receivable_credit_rules"),
    ]

    operations = [
        migrations.AddField(
            model_name="horsepersonrelationship",
            name="credit_recipient",
            field=models.BooleanField(
                default=False,
                help_text="Use this person for earned credits generated from the horse's use.",
            ),
        ),
        migrations.AddConstraint(
            model_name="horsepersonrelationship",
            constraint=models.UniqueConstraint(
                fields=("horse",),
                condition=models.Q(active=True, credit_recipient=True),
                name="unique_active_horse_credit_recipient",
            ),
        ),
    ]
