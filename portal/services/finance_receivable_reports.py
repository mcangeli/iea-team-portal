"""Receivables operational summaries for ArenaLine v3.7.1."""
from decimal import Decimal
from django.utils import timezone
from portal.model_modules.finance import ReceivableCharge
from portal.services.finance_access import finance_accounts_for_user

ZERO=Decimal("0.00")

def receivable_workspace_summary(user,team=None,*,finance_domain=None,as_of=None):
    as_of=as_of or timezone.localdate()
    accounts=finance_accounts_for_user(user,team).select_related("primary_person")
    if finance_domain is not None:accounts=accounts.filter(finance_domain=finance_domain)
    rows=[];open_total=ZERO;overdue_total=ZERO
    for account in accounts:
        due=account.amount_due
        overdue=sum((c.balance for c in account.charges.filter(status=ReceivableCharge.Status.POSTED,due_date__lt=as_of) if c.balance>ZERO),ZERO)
        open_total+=due;overdue_total+=overdue
        rows.append({"account":account,"amount_due":due,"balance":account.balance,"overdue":overdue,"unapplied":account.unapplied_payment_total+account.unapplied_credit_total})
    rows.sort(key=lambda r:(r["overdue"]<=ZERO,-r["overdue"],r["account"].name.lower()))
    return {"as_of":as_of,"rows":rows,"open_total":open_total,"overdue_total":overdue_total,"account_count":len(rows)}
