"""Finance reporting and business insights for ArenaLine v3.5 Preview 5."""
from dataclasses import dataclass
from decimal import Decimal
from django.db.models import Q, Sum
from portal.model_modules.finance import FinanceDomain, PayableObligation, ReceivableCharge
from portal.services.finance_access import allowed_finance_domains, finance_accounts_for_user, financial_transactions_for_user, payable_obligations_for_user

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
    payables:Decimal
    overdue_payables:Decimal
    payable_aging_buckets:dict
    payable_aging_rows:tuple
    category_rows:tuple
    aging_buckets:dict
    account_rows:tuple
    aging_rows:tuple
    period_rows:tuple

def finance_report_for_user(user,team,finance_domain,*,start_date=None,end_date=None,as_of=None,season=None):
    if finance_domain not in allowed_finance_domains(user,team):
        return None
    if season is not None and season.team_id != team.id:
        return None
    if start_date and end_date and end_date < start_date:
        raise ValueError("Report end date cannot be before start date.")
    qs=financial_transactions_for_user(user,team,finance_domain).filter(status="posted")
    if season is not None:qs=qs.filter(season=season)
    if start_date:qs=qs.filter(transaction_date__gte=start_date)
    if end_date:qs=qs.filter(transaction_date__lte=end_date)
    income=qs.filter(kind="income").aggregate(total=Sum("amount"))["total"] or ZERO
    expenses=qs.filter(kind="expense").aggregate(total=Sum("amount"))["total"] or ZERO
    grouped=qs.values("category__name","kind").annotate(total=Sum("amount")).order_by("kind","category__name")
    category_rows=tuple({"category":row["category__name"],"kind":row["kind"],"total":row["total"]} for row in grouped)
    accounts=finance_accounts_for_user(user,team).filter(finance_domain=finance_domain)
    charges=ReceivableCharge.objects.filter(account__in=accounts,status=ReceivableCharge.Status.POSTED).select_related("account")
    if season is not None:charges=charges.filter(season=season)
    if as_of:charges=charges.filter(charge_date__lte=as_of)
    receivables=sum((charge.balance for charge in charges),ZERO)
    overdue=ZERO
    aging_rows=[]
    aging={"current":ZERO,"days_1_30":ZERO,"days_31_60":ZERO,"days_61_90":ZERO,"days_90_plus":ZERO}
    if as_of:
        for charge in charges:
            balance=charge.balance
            if balance<=ZERO:continue
            if not charge.due_date or charge.due_date>=as_of:
                bucket="current"
                aging[bucket]+=balance
                aging_rows.append({"account_id":charge.account_id,"account":charge.account.name,"description":charge.description,"due_date":charge.due_date,"balance":balance,"bucket":bucket,"bucket_label":"Current"})
                continue
            days=(as_of-charge.due_date).days
            overdue+=balance
            if days<=30:bucket="days_1_30"
            elif days<=60:bucket="days_31_60"
            elif days<=90:bucket="days_61_90"
            else:bucket="days_90_plus"
            aging[bucket]+=balance
            bucket_label={"days_1_30":"1–30 days","days_31_60":"31–60 days","days_61_90":"61–90 days","days_90_plus":"90+ days"}[bucket]
            aging_rows.append({"account_id":charge.account_id,"account":charge.account.name,"description":charge.description,"due_date":charge.due_date,"balance":balance,"bucket":bucket,"bucket_label":bucket_label})
    obligations=payable_obligations_for_user(user,team).filter(party__finance_domain=finance_domain,status=PayableObligation.Status.OPEN).select_related("party","expense_category").prefetch_related("payments")
    if season is not None:obligations=obligations.filter(season=season)
    if as_of:obligations=obligations.filter(obligation_date__lte=as_of)
    payables=ZERO;overdue_payables=ZERO;payable_aging_rows=[]
    payable_aging={"current":ZERO,"days_1_30":ZERO,"days_31_60":ZERO,"days_61_90":ZERO,"days_90_plus":ZERO}
    for obligation in obligations:
        balance=obligation.balance
        if balance<=ZERO:continue
        payables+=balance
        if not as_of or not obligation.due_date or obligation.due_date>=as_of:
            bucket="current"
        else:
            days=(as_of-obligation.due_date).days
            overdue_payables+=balance
            if days<=30:bucket="days_1_30"
            elif days<=60:bucket="days_31_60"
            elif days<=90:bucket="days_61_90"
            else:bucket="days_90_plus"
        payable_aging[bucket]+=balance
        bucket_label={"current":"Current","days_1_30":"1–30 days","days_31_60":"31–60 days","days_61_90":"61–90 days","days_90_plus":"90+ days"}[bucket]
        payable_aging_rows.append({"obligation_id":obligation.pk,"party":obligation.party.name,"description":obligation.description,"due_date":obligation.due_date,"balance":balance,"bucket":bucket,"bucket_label":bucket_label})
    period_rows=[]
    grouped_periods=qs.values("transaction_date__year","transaction_date__month").annotate(
        income=Sum("amount",filter=Q(kind="income")),
        expenses=Sum("amount",filter=Q(kind="expense")),
    ).order_by("transaction_date__year","transaction_date__month")
    for period in grouped_periods:
        inc=period["income"] or ZERO;exp=period["expenses"] or ZERO
        period_rows.append({"year":period["transaction_date__year"],"month":period["transaction_date__month"],"income":inc,"expenses":exp,"net":inc-exp})
    account_rows=[]
    for account in qs.values("account__name").annotate(
        income=Sum("amount",filter=Q(kind="income")),
        expenses=Sum("amount",filter=Q(kind="expense")),
    ).order_by("account__name"):
        inc=account["income"] or ZERO;exp=account["expenses"] or ZERO
        account_rows.append({"account":account["account__name"],"income":inc,"expenses":exp,"net":inc-exp})
    return FinanceReport(finance_domain,start_date,end_date,income,expenses,income-expenses,receivables,overdue,payables,overdue_payables,payable_aging,tuple(payable_aging_rows),category_rows,aging,tuple(account_rows),tuple(aging_rows),tuple(period_rows))
