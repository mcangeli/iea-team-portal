"""Finance reporting and business insights for ArenaLine v3.5 Preview 5."""
from dataclasses import dataclass
from decimal import Decimal
from django.db.models import Q, Sum
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
    aging_buckets:dict
    account_rows:tuple

def finance_report_for_user(user,team,finance_domain,*,start_date=None,end_date=None,as_of=None):
    if finance_domain not in allowed_finance_domains(user,team):
        return None
    if start_date and end_date and end_date < start_date:
        raise ValueError("Report end date cannot be before start date.")
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
    aging={"current":ZERO,"1_30":ZERO,"31_60":ZERO,"61_90":ZERO,"90_plus":ZERO}
    if as_of:
        for charge in charges:
            balance=charge.balance
            if balance<=ZERO:continue
            if not charge.due_date or charge.due_date>=as_of:
                aging["current"]+=balance;continue
            days=(as_of-charge.due_date).days
            overdue+=balance
            if days<=30:aging["1_30"]+=balance
            elif days<=60:aging["31_60"]+=balance
            elif days<=90:aging["61_90"]+=balance
            else:aging["90_plus"]+=balance
    account_rows=[]
    for account in financial_transactions_for_user(user,team,finance_domain).filter(status="posted").values("account__name").annotate(
        income=Sum("amount",filter=Q(kind="income")),
        expenses=Sum("amount",filter=__import__("django").db.models.Q(kind="expense")),
    ).order_by("account__name"):
        inc=account["income"] or ZERO;exp=account["expenses"] or ZERO
        account_rows.append({"account":account["account__name"],"income":inc,"expenses":exp,"net":inc-exp})
    return FinanceReport(finance_domain,start_date,end_date,income,expenses,income-expenses,receivables,overdue,category_rows,aging,tuple(account_rows))
