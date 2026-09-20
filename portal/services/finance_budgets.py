"""Budget-versus-actual reporting for ArenaLine v3.7.2."""
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum

from portal.model_modules.finance import Budget
from portal.models import FinancialTransaction

ZERO=Decimal("0.00")


@dataclass(frozen=True)
class BudgetActualReport:
    budget:object
    planned_income:Decimal
    actual_income:Decimal
    planned_expenses:Decimal
    actual_expenses:Decimal
    planned_net:Decimal
    actual_net:Decimal
    line_rows:tuple


def budget_actuals(budget):
    """Compare a budget with posted ledger transactions in its domain and period."""
    if not isinstance(budget,Budget):
        raise TypeError("budget must be a Budget instance.")

    qs=FinancialTransaction.objects.filter(
        team=budget.team,
        account__finance_domain=budget.finance_domain,
        status=FinancialTransaction.Status.POSTED,
        transaction_date__gte=budget.start_date,
        transaction_date__lte=budget.end_date,
    )
    if budget.season_id:
        qs=qs.filter(season=budget.season)

    actual_by_key={
        (row["category_id"],row["kind"]):(row["total"] or ZERO)
        for row in qs.values("category_id","kind").annotate(total=Sum("amount"))
    }

    rows=[]
    planned_income=ZERO
    planned_expenses=ZERO
    actual_income=ZERO
    actual_expenses=ZERO
    for line in budget.lines.select_related("category").all():
        actual=actual_by_key.get((line.category_id,line.kind),ZERO)
        remaining=line.amount-actual
        percent_used=(actual/line.amount*Decimal("100")) if line.amount else None
        rows.append({
            "line":line,
            "planned":line.amount,
            "actual":actual,
            "remaining":remaining,
            "percent_used":percent_used,
        })
        if line.kind==FinancialTransaction.Kind.INCOME:
            planned_income+=line.amount
            actual_income+=actual
        else:
            planned_expenses+=line.amount
            actual_expenses+=actual

    return BudgetActualReport(
        budget=budget,
        planned_income=planned_income,
        actual_income=actual_income,
        planned_expenses=planned_expenses,
        actual_expenses=actual_expenses,
        planned_net=planned_income-planned_expenses,
        actual_net=actual_income-actual_expenses,
        line_rows=tuple(rows),
    )
