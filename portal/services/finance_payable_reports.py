"""Accounts-payable operational summaries for ArenaLine v3.7."""
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from portal.model_modules.finance import PayableObligation
from portal.services.finance_access import payable_obligations_for_user

ZERO = Decimal("0.00")


def payable_workspace_summary(user, team=None, *, finance_domain=None, as_of=None):
    as_of = as_of or timezone.localdate()
    qs = payable_obligations_for_user(user, team).select_related("party", "expense_category")
    if finance_domain is not None:
        qs = qs.filter(party__finance_domain=finance_domain)

    open_qs = qs.filter(status=PayableObligation.Status.OPEN).annotate(
        posted_paid=Sum("payments__amount", filter=Q(payments__status="posted"))
    )

    rows = []
    totals = {"open": ZERO, "due": ZERO, "overdue": ZERO, "paid": ZERO}
    for obligation in open_qs:
        paid = obligation.posted_paid or ZERO
        balance = max(obligation.amount - paid, ZERO)
        state = obligation.lifecycle_status(as_of)
        if state == "paid":
            totals["paid"] += obligation.amount
            continue
        totals["open"] += balance
        if state == "due":
            totals["due"] += balance
        elif state == "overdue":
            totals["overdue"] += balance
        rows.append({
            "obligation": obligation,
            "party": obligation.party,
            "balance": balance,
            "state": state,
            "due_date": obligation.due_date,
        })

    rows.sort(key=lambda row: (row["due_date"] is None, row["due_date"] or as_of, row["obligation"].id))
    return {
        "as_of": as_of,
        "rows": rows,
        "open_total": totals["open"],
        "due_total": totals["due"],
        "overdue_total": totals["overdue"],
        "paid_total": totals["paid"],
    }
