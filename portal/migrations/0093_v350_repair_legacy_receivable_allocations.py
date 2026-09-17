from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


ZERO = Decimal("0.00")


def repair_overallocations(apps, schema_editor):
    """Cap migrated allocations at each charge amount.

    Preview 1B preserved full payment/credit source amounts. Any legacy excess
    remains on the source and therefore becomes unapplied under the v3.5 ledger
    semantics instead of producing a negative charge balance.
    """
    Charge = apps.get_model("portal", "ReceivableCharge")

    for charge in Charge.objects.all().iterator():
        remaining = charge.amount
        allocations = charge.allocations.filter(status="posted").order_by("created_at", "id")
        for allocation in allocations:
            if remaining <= ZERO:
                allocation.delete()
                continue
            if allocation.amount > remaining:
                allocation.amount = remaining
                allocation.save(update_fields=["amount"])
            remaining -= allocation.amount


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("portal", "0092_v350_receivable_account_semantics")]

    operations = [migrations.RunPython(repair_overallocations, noop_reverse)]
