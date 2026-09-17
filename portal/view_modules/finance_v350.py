"""ArenaLine v3.5 finance workspace views."""
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render

from portal.forms_v350_finance import FinanceAllocationForm, FinanceChargeForm, FinanceCreditForm, FinancePaymentForm
from portal.model_modules.finance import FinanceDomain
from portal.platform import organization_for_view_user
from portal.services.finance_access import allowed_finance_domains, finance_account_for_user, finance_accounts_for_user
from portal.services.finance_operations import (
    allocate_credit_for_user,
    allocate_payment_for_user,
    create_charge_for_user,
    post_credit_for_user,
    post_payment_for_user,
)
from portal.services.finance_statements import account_activity, statement_for_user

ZERO = Decimal("0.00")


def _team_for_finance_user(user):
    team = organization_for_view_user(user)
    if not team or not allowed_finance_domains(user, team):
        raise PermissionDenied
    return team


def _account_for_request(request, pk):
    team = _team_for_finance_user(request.user)
    account = finance_account_for_user(request.user, pk, team)
    if account is None:
        raise PermissionDenied
    return team, account


def _domain_summary(user, team, domain):
    accounts = finance_accounts_for_user(user, team).filter(finance_domain=domain).select_related("primary_person")
    rows = list(accounts)
    return {"domain": domain, "label": "General Barn" if domain == FinanceDomain.GENERAL else "IEA", "accounts": rows,
            "account_count": len(rows), "balance": sum((a.balance for a in rows), ZERO),
            "amount_due": sum((a.amount_due for a in rows), ZERO),
            "unapplied_payments": sum((a.unapplied_payment_total for a in rows), ZERO),
            "unapplied_credits": sum((a.unapplied_credit_total for a in rows), ZERO)}


@login_required
def finance_workspace(request):
    team = _team_for_finance_user(request.user)
    domains = allowed_finance_domains(request.user, team)
    summaries = [_domain_summary(request.user, team, domain) for domain in (FinanceDomain.GENERAL, FinanceDomain.IEA) if domain in domains]
    accounts = finance_accounts_for_user(request.user, team).select_related("primary_person").order_by("finance_domain", "name")
    return render(request, "portal/finance_workspace_v350.html", {"team": team, "domain_summaries": summaries, "accounts": accounts,
        "can_see_general": FinanceDomain.GENERAL in domains, "can_see_iea": FinanceDomain.IEA in domains})


@login_required
def finance_receivable_account_detail(request, pk):
    team, account = _account_for_request(request, pk)
    return render(request, "portal/finance_receivable_account_v350.html", {"team": team, "account": account, "activity": account_activity(account),
        "open_charges": account.charges.filter(status="posted"), "unapplied_payments": [p for p in account.payments.filter(status="posted") if p.unapplied_amount > ZERO],
        "unapplied_credits": [c for c in account.credits.filter(status="posted") if c.unapplied_amount > ZERO]})


def _operation_form(request, pk, form_class, title, submit_label, operation):
    team, account = _account_for_request(request, pk)
    form = form_class(request.POST or None, initial={"charge_date": date.today(), "received_date": date.today(), "credit_date": date.today()})
    if request.method == "POST" and form.is_valid():
        try:
            operation(request.user, account.pk, team=team, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"{submit_label} saved.")
            return redirect("finance_receivable_account_detail", pk=account.pk)
    return render(request, "portal/finance_operation_form_v350.html", {"team": team, "account": account, "form": form, "title": title, "submit_label": submit_label})


@login_required
def finance_charge_add(request, pk):
    return _operation_form(request, pk, FinanceChargeForm, "Add charge", "Charge", create_charge_for_user)


@login_required
def finance_payment_add(request, pk):
    return _operation_form(request, pk, FinancePaymentForm, "Record payment", "Payment", post_payment_for_user)


@login_required
def finance_credit_add(request, pk):
    return _operation_form(request, pk, FinanceCreditForm, "Add credit", "Credit", post_credit_for_user)


@login_required
def finance_payment_allocate(request, pk, payment_id):
    team, account = _account_for_request(request, pk)
    form = FinanceAllocationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            allocate_payment_for_user(request.user, account.pk, payment_id=payment_id, team=team, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Payment allocation saved.")
            return redirect("finance_receivable_account_detail", pk=account.pk)
    return render(request, "portal/finance_allocation_form_v350.html", {"account": account, "form": form, "source_kind": "Payment", "charges": account.charges.filter(status="posted")})


@login_required
def finance_credit_allocate(request, pk, credit_id):
    team, account = _account_for_request(request, pk)
    form = FinanceAllocationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            allocate_credit_for_user(request.user, account.pk, credit_id=credit_id, team=team, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Credit allocation saved.")
            return redirect("finance_receivable_account_detail", pk=account.pk)
    return render(request, "portal/finance_allocation_form_v350.html", {"account": account, "form": form, "source_kind": "Credit", "charges": account.charges.filter(status="posted")})


@login_required
def finance_receivable_statement(request, pk):
    team, account = _account_for_request(request, pk)
    today = date.today()
    try:
        start_date = date.fromisoformat(request.GET.get("start")) if request.GET.get("start") else date(today.year, 1, 1)
        end_date = date.fromisoformat(request.GET.get("end")) if request.GET.get("end") else today
    except ValueError:
        start_date, end_date = date(today.year, 1, 1), today
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    statement = statement_for_user(request.user, account.pk, start_date=start_date, end_date=end_date, team=team)
    if statement is None:
        raise PermissionDenied
    return render(request, "portal/finance_statement_v350.html", {"team": team, "account": account, "statement": statement, "start_date": start_date, "end_date": end_date})
