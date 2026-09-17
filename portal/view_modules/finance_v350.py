"""ArenaLine v3.5 finance workspace views.

These views deliberately use the v3.5 finance access/query services so finance
domain authorization is enforced before any receivable account data is loaded.
Legacy finance views remain available during the compatibility-first transition.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from portal.model_modules.finance import FinanceDomain
from portal.platform import organization_for_view_user
from portal.services.finance_access import allowed_finance_domains, finance_account_for_user, finance_accounts_for_user
from portal.services.finance_statements import account_activity, statement_for_user


ZERO = Decimal("0.00")


def _team_for_finance_user(user):
    team = organization_for_view_user(user)
    if not team or not allowed_finance_domains(user, team):
        raise PermissionDenied
    return team


def _domain_summary(user, team, domain):
    accounts = finance_accounts_for_user(user, team).filter(finance_domain=domain).select_related("primary_person")
    rows = list(accounts)
    return {
        "domain": domain,
        "label": "General Barn" if domain == FinanceDomain.GENERAL else "IEA",
        "accounts": rows,
        "account_count": len(rows),
        "balance": sum((account.balance for account in rows), ZERO),
        "amount_due": sum((account.amount_due for account in rows), ZERO),
        "unapplied_payments": sum((account.unapplied_payment_total for account in rows), ZERO),
        "unapplied_credits": sum((account.unapplied_credit_total for account in rows), ZERO),
    }


@login_required
def finance_workspace(request):
    team = _team_for_finance_user(request.user)
    domains = allowed_finance_domains(request.user, team)
    summaries = [
        _domain_summary(request.user, team, domain)
        for domain in (FinanceDomain.GENERAL, FinanceDomain.IEA)
        if domain in domains
    ]
    accounts = finance_accounts_for_user(request.user, team).select_related("primary_person").order_by("finance_domain", "name")
    return render(request, "portal/finance_workspace_v350.html", {
        "team": team,
        "domain_summaries": summaries,
        "accounts": accounts,
        "can_see_general": FinanceDomain.GENERAL in domains,
        "can_see_iea": FinanceDomain.IEA in domains,
    })


@login_required
def finance_receivable_account_detail(request, pk):
    team = _team_for_finance_user(request.user)
    account = finance_account_for_user(request.user, pk, team)
    if account is None:
        raise PermissionDenied
    activity = account_activity(account)
    return render(request, "portal/finance_receivable_account_v350.html", {
        "team": team,
        "account": account,
        "activity": activity,
    })


@login_required
def finance_receivable_statement(request, pk):
    team = _team_for_finance_user(request.user)
    account = finance_account_for_user(request.user, pk, team)
    if account is None:
        raise PermissionDenied

    today = date.today()
    start_raw = request.GET.get("start", "")
    end_raw = request.GET.get("end", "")
    try:
        start_date = date.fromisoformat(start_raw) if start_raw else date(today.year, 1, 1)
        end_date = date.fromisoformat(end_raw) if end_raw else today
    except ValueError:
        start_date, end_date = date(today.year, 1, 1), today

    if end_date < start_date:
        start_date, end_date = end_date, start_date

    statement = statement_for_user(
        request.user,
        account.pk,
        start_date=start_date,
        end_date=end_date,
        team=team,
    )
    if statement is None:
        raise PermissionDenied
    return render(request, "portal/finance_statement_v350.html", {
        "team": team,
        "account": account,
        "statement": statement,
        "start_date": start_date,
        "end_date": end_date,
    })
