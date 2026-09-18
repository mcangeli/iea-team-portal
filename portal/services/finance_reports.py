"""Finance reporting and business insights for ArenaLine v3.5 Preview 5."""
from dataclasses import dataclass
from decimal import Decimal
from django.db.models import Sum
from portal.model_modules.finance import FinanceDomain, ReceivableCharge
from portal.services.finance_access import allowed_finance_domains, finance_accounts_for_user, financial_transactions_for_user

ZERO=Decimal("0.00")

@dataclass(frozen=True)
class FinanceReport:
    finance_domain:str
    start_date:object
    end_date:object
    income:Decimal
    expenses:Decimal
    net:Decimal
    receivables:Decimal
    overdue_receivables:Decimal
    category_rows:tuple

def finance_report_for_user(user,team,finance_domain,*,start_date=None,end_date=None,as_of=None):
    if finance_domain not in allowed_finance_domains(user,team):
        return None
    qs=financial_transactions_for_user(user,team,finance_domain).filter(status="posted")
    if start_date:qs=qs.filter(transaction_date__gte=start_date)
    if end_date:qs=qs.filter(transaction_date__lte=end_date)
    income=qs.filter(kind="income").aggregate(total=Sum("amount"))["total"] or ZERO
    expenses=qs.filter(kind="expense").aggregate(total=Sum("amount"))["total"] or ZERO
    grouped=qs.values("category__name","kind").annotate(total=Sum("amount")).order_by("kind","category__name")
    category_rows=tuple({"category":row["category__name"],"kind":row["kind"],"total":row["total"]} for row in grouped)
    accounts=finance_accounts_for_user(user,team).filter(finance_domain=finance_domain)
    charges=ReceivableCharge.objects.filter(account__in=accounts,status=ReceivableCharge.Status.POSTED)
    receivables=sum((charge.balance for charge in charges),ZERO)
    overdue=ZERO
    if as_of:
        overdue=sum((charge.balance for charge in charges.filter(due_date__lt=as_of) if charge.balance>ZERO),ZERO)
    return FinanceReport(finance_domain,start_date,end_date,income,expenses,income-expenses,receivables,overdue,category_rows)
