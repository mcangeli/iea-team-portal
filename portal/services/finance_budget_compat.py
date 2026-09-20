"""Compatibility helpers between legacy IEA SeasonBudget and v3.7.2 generic budgets."""
from django.core.exceptions import ValidationError

from portal.model_modules.finance import Budget, BudgetLine, FinanceDomain
from portal.models import SeasonBudget, ShowBudgetLine


def sync_season_budget_to_generic(*,season,name=None):
    """Create/update an IEA generic budget from the existing SeasonBudget rows."""
    if not season.start_date or not season.end_date:
        raise ValidationError("Season dates are required before syncing its budget.")
    budget,_=Budget.objects.get_or_create(
        team=season.team,
        finance_domain=FinanceDomain.IEA,
        season=season,
        name=name or f"{season.name} Budget",
        start_date=season.start_date,
        end_date=season.end_date,
        defaults={"status":Budget.Status.ACTIVE},
    )
    legacy=SeasonBudget.objects.filter(season=season).select_related("category")
    seen=set()
    for item in legacy:
        line,_=BudgetLine.objects.update_or_create(
            budget=budget,
            category=item.category,
            kind=item.kind,
            defaults={"description":item.category.name,"amount":item.amount,"notes":item.notes},
        )
        seen.add(line.pk)
    return budget


def sync_show_budget_to_generic(*,show):
    """Mirror legacy show budget lines into a generic IEA budget without deleting generic-only planning."""
    season=show.season
    if not season.start_date or not season.end_date:
        raise ValidationError("Season dates are required before syncing a show budget.")
    budget,_=Budget.objects.get_or_create(
        team=show.team,
        finance_domain=FinanceDomain.IEA,
        season=season,
        name=f"{show.name} Show Budget",
        start_date=show.start_date if getattr(show,"start_date",None) else season.start_date,
        end_date=show.end_date if getattr(show,"end_date",None) else (show.start_date if getattr(show,"start_date",None) else season.end_date),
        defaults={"status":Budget.Status.ACTIVE,"notes":f"Compatibility budget for show #{show.pk}."},
    )
    legacy=ShowBudgetLine.objects.filter(show=show).select_related("category")
    for item in legacy:
        description=item.description
        if item.scope:
            description=f"{item.get_scope_display()}: {description}"
        BudgetLine.objects.update_or_create(
            budget=budget,
            category=item.category,
            kind=item.kind,
            defaults={"description":description,"amount":item.amount,"notes":item.notes},
        )
    return budget
