from django.db import migrations


class Migration(migrations.Migration):
    """Join the legacy branding migration branch back into the main portal graph."""

    dependencies = [
        ("portal", "0069_teambranding_barn_hero"),
        ("portal", "0100_v370_accounts_payable_foundation"),
    ]

    operations = []
