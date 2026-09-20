"""ArenaLine v3.5 finance workspace views."""
from datetime import date
from decimal import Decimal
import csv
from io import StringIO
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.http import HttpResponse
from django.utils.text import slugify
from portal.forms_v350_finance import BudgetForm, BudgetLineForm, PayableObligationForm, PayablePartyForm, PayablePaymentForm, PayableVoidPaymentForm, ReceivableBillingRuleForm, ReceivableCreditRuleForm, MonthlyBillingRunForm, FinanceAccountForm, FinanceAccountPersonForm, FinanceAllocationForm, FinanceChargeForm, FinanceCreditForm, FinancePaymentForm, FinanceUnallocateForm, BankImportMappingForm, BankImportUploadForm, FinanceVoidPaymentForm, AccountingExportProfileForm, AccountingExportRunForm, FinanceReportFilterForm
from portal.model_modules.finance import AccountingExportProfile, BankImportBatch, BankImportProfile, Budget, FinanceDomain, ImportedBankTransaction, ReceivableCharge, ReceivableCreditRule, ReconciliationMatch
from portal.models import FinancialAccount
from portal.platform import organization_for_view_user
from portal.services.finance_access import allowed_finance_domains, finance_account_for_user, finance_accounts_for_user, receivable_billing_rules_for_user
from portal.services.finance_imports import stage_bank_import
from portal.services.finance_exports import QUICKBOOKS_MAPPING, normalized_export_rows, render_accounting_export
from portal.services.finance_reconciliation import confirm_reconciliation, generate_match_candidates
from portal.services.finance_operations import add_account_person_for_user, allocate_credit_for_user, allocate_payment_for_user, allocate_credit_oldest_for_user, allocate_payment_oldest_for_user, create_account_for_user, create_charge_for_user, post_credit_for_user, post_payment_for_user, remove_account_person_for_user, unallocate_credit_for_user, unallocate_payment_for_user, void_payment_for_user
from portal.services.finance_statements import account_activity, statement_for_user
from portal.services.finance_reports import finance_report_for_user
from portal.services.finance_payable_reports import payable_workspace_summary
from portal.services.finance_receivable_reports import receivable_workspace_summary
from portal.services.finance_budgets import budget_actuals
from portal.services.finance_billing_operations import create_billing_rule_for_user, generate_monthly_domain_for_user
from portal.services.finance_payable_operations import create_payable_obligation_for_user, create_payable_party_for_user, post_payable_payment_for_user, void_payable_payment_for_user
ZERO=Decimal("0.00")

def _team_for_finance_user(user):
    team=organization_for_view_user(user)
    if not team or not allowed_finance_domains(user,team):raise PermissionDenied
    return team

def _account_for_request(request,pk):
    team=_team_for_finance_user(request.user);account=finance_account_for_user(request.user,pk,team)
    if account is None:raise PermissionDenied
    return team,account

def _domain_summary(user,team,domain):
    rows=list(finance_accounts_for_user(user,team).filter(finance_domain=domain).select_related("primary_person"));return {"domain":domain,"label":"General Barn" if domain==FinanceDomain.GENERAL else "IEA","accounts":rows,"account_count":len(rows),"balance":sum((a.balance for a in rows),ZERO),"amount_due":sum((a.amount_due for a in rows),ZERO),"unapplied_payments":sum((a.unapplied_payment_total for a in rows),ZERO),"unapplied_credits":sum((a.unapplied_credit_total for a in rows),ZERO)}
@login_required
def finance_workspace(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team);summaries=[_domain_summary(request.user,team,d) for d in (FinanceDomain.GENERAL,FinanceDomain.IEA) if d in domains];accounts=finance_accounts_for_user(request.user,team).select_related("primary_person").order_by("finance_domain","name");return render(request,"portal/finance_workspace_v350.html",{"team":team,"domain_summaries":summaries,"accounts":accounts,"can_see_general":FinanceDomain.GENERAL in domains,"can_see_iea":FinanceDomain.IEA in domains})

@login_required
def finance_budgets(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    requested=request.GET.get("domain")
    domain=requested if requested in domains else (FinanceDomain.GENERAL if FinanceDomain.GENERAL in domains else FinanceDomain.IEA)
    budgets=Budget.objects.filter(team=team,finance_domain=domain).select_related("season").order_by("-start_date","name")
    return render(request,"portal/finance_budgets_v372.html",{"team":team,"domains":domains,"selected_domain":domain,"budgets":budgets})

@login_required
def finance_budget_add(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    requested=request.GET.get("domain") or request.POST.get("finance_domain")
    domain=requested if requested in domains else (FinanceDomain.GENERAL if FinanceDomain.GENERAL in domains else FinanceDomain.IEA)
    form=BudgetForm(request.POST or None,team=team,finance_domain=domain)
    if request.method=="POST" and form.is_valid():
        budget=form.save(commit=False);budget.team=team;budget.finance_domain=domain
        try:budget.full_clean();budget.save()
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Budget created.");return redirect("finance_budget_detail",pk=budget.pk)
    return render(request,"portal/finance_budget_form_v372.html",{"team":team,"form":form,"selected_domain":domain,"title":"New budget"})

@login_required
def finance_budget_detail(request,pk):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    budget=Budget.objects.filter(pk=pk,team=team,finance_domain__in=domains).select_related("season").first()
    if budget is None:raise PermissionDenied
    report=budget_actuals(budget)
    return render(request,"portal/finance_budget_detail_v372.html",{"team":team,"budget":budget,"report":report})

@login_required
def finance_budget_edit(request,pk):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    budget=Budget.objects.filter(pk=pk,team=team,finance_domain__in=domains).first()
    if budget is None:raise PermissionDenied
    form=BudgetForm(request.POST or None,instance=budget,team=team,finance_domain=budget.finance_domain)
    if request.method=="POST" and form.is_valid():
        budget=form.save(commit=False);budget.team=team
        try:budget.full_clean();budget.save()
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Budget updated.");return redirect("finance_budget_detail",pk=budget.pk)
    return render(request,"portal/finance_budget_form_v372.html",{"team":team,"form":form,"selected_domain":budget.finance_domain,"budget":budget,"title":f"Edit {budget.name}"})

@login_required
def finance_budget_line_add(request,pk):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    budget=Budget.objects.filter(pk=pk,team=team,finance_domain__in=domains).first()
    if budget is None:raise PermissionDenied
    form=BudgetLineForm(request.POST or None,team=team)
    if request.method=="POST" and form.is_valid():
        line=form.save(commit=False);line.budget=budget
        try:line.full_clean();line.save()
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Budget line added.");return redirect("finance_budget_detail",pk=budget.pk)
    return render(request,"portal/finance_budget_line_form_v372.html",{"team":team,"budget":budget,"form":form,"title":"Add budget line"})

@login_required
def finance_budget_line_edit(request,pk,line_id):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    budget=Budget.objects.filter(pk=pk,team=team,finance_domain__in=domains).first()
    if budget is None:raise PermissionDenied
    line=budget.lines.filter(pk=line_id).first()
    if line is None:raise PermissionDenied
    form=BudgetLineForm(request.POST or None,instance=line,team=team)
    if request.method=="POST" and form.is_valid():
        line=form.save(commit=False);line.budget=budget
        try:line.full_clean();line.save()
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Budget line updated.");return redirect("finance_budget_detail",pk=budget.pk)
    return render(request,"portal/finance_budget_line_form_v372.html",{"team":team,"budget":budget,"line":line,"form":form,"title":f"Edit {line.description}"})

@login_required
def finance_receivables(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    requested=request.GET.get("domain")
    domain=requested if requested in domains else (FinanceDomain.GENERAL if FinanceDomain.GENERAL in domains else FinanceDomain.IEA)
    summary=receivable_workspace_summary(request.user,team,finance_domain=domain)
    rules=receivable_billing_rules_for_user(request.user,team).filter(account__finance_domain=domain).select_related("account").order_by("account__name","description")
    credit_rules=ReceivableCreditRule.objects.filter(team=team,finance_domain=domain).order_by("name","id")
    return render(request,"portal/finance_receivables_v371.html",{"team":team,"domains":domains,"selected_domain":domain,"summary":summary,"billing_rules":rules,"credit_rules":credit_rules})


@login_required
def finance_billing_rule_add(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    requested=request.GET.get("domain");domain=requested if requested in domains else (FinanceDomain.GENERAL if FinanceDomain.GENERAL in domains else FinanceDomain.IEA)
    accounts=finance_accounts_for_user(request.user,team).filter(finance_domain=domain,status="active").order_by("name")
    form=ReceivableBillingRuleForm(request.POST or None,accounts=accounts)
    if request.method=="POST" and form.is_valid():
        account=form.cleaned_data.pop("account")
        try:create_billing_rule_for_user(request.user,account.pk,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Billing rule created.");return redirect(f"{reverse('finance_receivables')}?domain={account.finance_domain}")
    return render(request,"portal/finance_billing_rule_form_v371.html",{"team":team,"form":form,"selected_domain":domain})

@login_required
def finance_credit_rule_add(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    requested=request.GET.get("domain") or request.POST.get("finance_domain")
    domain=requested if requested in domains else (FinanceDomain.GENERAL if FinanceDomain.GENERAL in domains else FinanceDomain.IEA)
    form=ReceivableCreditRuleForm(request.POST or None,team=team,finance_domain=domain)
    if request.method=="POST" and form.is_valid():
        rule=form.save(commit=False);rule.team=team;rule.finance_domain=domain;rule.full_clean();rule.save()
        messages.success(request,"Credit rule created.");return redirect(f"{reverse('finance_receivables')}?domain={domain}")
    return render(request,"portal/finance_credit_rule_form_v371.html",{"team":team,"form":form,"selected_domain":domain,"title":"New credit rule"})

@login_required
def finance_credit_rule_edit(request,pk):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    rule=ReceivableCreditRule.objects.filter(pk=pk,team=team,finance_domain__in=domains).first()
    if rule is None:raise PermissionDenied
    form=ReceivableCreditRuleForm(request.POST or None,instance=rule,team=team,finance_domain=rule.finance_domain)
    if request.method=="POST" and form.is_valid():
        rule=form.save(commit=False);rule.team=team;rule.finance_domain=rule.finance_domain;rule.full_clean();rule.save()
        messages.success(request,"Credit rule updated.");return redirect(f"{reverse('finance_receivables')}?domain={rule.finance_domain}")
    return render(request,"portal/finance_credit_rule_form_v371.html",{"team":team,"form":form,"selected_domain":rule.finance_domain,"title":f"Edit {rule.name}","rule":rule})

@login_required
def finance_monthly_billing_run(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    requested=request.GET.get("domain") or request.POST.get("finance_domain");domain=requested if requested in domains else (FinanceDomain.GENERAL if FinanceDomain.GENERAL in domains else FinanceDomain.IEA)
    form=MonthlyBillingRunForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        result=generate_monthly_domain_for_user(request.user,billing_month=form.cleaned_data["billing_month"],finance_domain=domain,team=team)
        messages.success(request,f'Monthly billing complete: {len(result["generated"])} charge(s) created, {len(result["existing"])} already existed.')
        return redirect(f"{reverse('finance_receivables')}?domain={domain}")
    return render(request,"portal/finance_monthly_billing_run_v371.html",{"team":team,"form":form,"selected_domain":domain})


@login_required
def finance_payables(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    requested=request.GET.get("domain")
    domain=requested if requested in domains else (FinanceDomain.GENERAL if FinanceDomain.GENERAL in domains else FinanceDomain.IEA)
    summary=payable_workspace_summary(request.user,team,finance_domain=domain)
    from portal.services.finance_access import payable_parties_for_user
    parties=payable_parties_for_user(request.user,team).filter(finance_domain=domain,active=True).order_by("name")
    return render(request,"portal/finance_payables_v370.html",{"team":team,"domains":domains,"selected_domain":domain,"summary":summary,"parties":parties,"FinanceDomain":FinanceDomain})

@login_required
def finance_payable_party_add(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    initial={"finance_domain":request.GET.get("domain")} if request.GET.get("domain") in domains else {}
    form=PayablePartyForm(request.POST or None,initial=initial,team=team,allowed_domains=domains)
    if request.method=="POST" and form.is_valid():
        try:party=create_payable_party_for_user(request.user,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Payee created.");return redirect(f"{reverse('finance_payables')}?domain={party.finance_domain}")
    return render(request,"portal/finance_payable_party_form_v370.html",{"team":team,"form":form})

@login_required
def finance_payable_party_detail(request,pk):
    team=_team_for_finance_user(request.user)
    from portal.services.finance_access import payable_party_for_user
    party=payable_party_for_user(request.user,pk,team)
    if party is None:raise PermissionDenied
    obligations=party.obligations.select_related("expense_category").prefetch_related("payments").order_by("-obligation_date","-id")
    return render(request,"portal/finance_payable_party_detail_v370.html",{"team":team,"party":party,"obligations":obligations})

@login_required
def finance_payable_obligation_add(request,party_id):
    team=_team_for_finance_user(request.user)
    from portal.services.finance_access import payable_party_for_user
    party=payable_party_for_user(request.user,party_id,team)
    if party is None:raise PermissionDenied
    form=PayableObligationForm(request.POST or None,initial={"obligation_date":date.today()},team=team)
    if request.method=="POST" and form.is_valid():
        try:create_payable_obligation_for_user(request.user,party.pk,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Payable obligation created.");return redirect(f"{reverse('finance_payables')}?domain={party.finance_domain}")
    return render(request,"portal/finance_payable_obligation_form_v370.html",{"team":team,"party":party,"form":form})

@login_required
def finance_payable_obligation_detail(request,pk):
    team=_team_for_finance_user(request.user)
    from portal.services.finance_access import payable_obligation_for_user
    obligation=payable_obligation_for_user(request.user,pk,team)
    if obligation is None:raise PermissionDenied
    payments=obligation.payments.select_related("payment_account","financial_transaction").order_by("-paid_date","-id")
    return render(request,"portal/finance_payable_obligation_detail_v370.html",{"team":team,"obligation":obligation,"payments":payments})

@login_required
def finance_payable_payment_add(request,pk):
    team=_team_for_finance_user(request.user)
    from portal.services.finance_access import payable_obligation_for_user
    obligation=payable_obligation_for_user(request.user,pk,team)
    if obligation is None:raise PermissionDenied
    form=PayablePaymentForm(request.POST or None,initial={"paid_date":date.today(),"amount":obligation.balance},team=team,finance_domain=obligation.party.finance_domain,max_amount=obligation.balance)
    if request.method=="POST" and form.is_valid():
        try:post_payable_payment_for_user(request.user,obligation.pk,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Payable payment recorded.");return redirect("finance_payable_obligation_detail",pk=obligation.pk)
    return render(request,"portal/finance_payable_payment_form_v370.html",{"team":team,"obligation":obligation,"form":form})

@login_required
def finance_payable_payment_void(request,pk,payment_id):
    team=_team_for_finance_user(request.user)
    from portal.services.finance_access import payable_obligation_for_user
    obligation=payable_obligation_for_user(request.user,pk,team)
    if obligation is None:raise PermissionDenied
    payment=obligation.payments.filter(pk=payment_id).first()
    if payment is None:raise PermissionDenied
    form=PayableVoidPaymentForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        try:void_payable_payment_for_user(request.user,obligation.pk,payment_id=payment.pk,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Payable payment voided.");return redirect("finance_payable_obligation_detail",pk=obligation.pk)
    return render(request,"portal/finance_payable_payment_void_v370.html",{"team":team,"obligation":obligation,"payment":payment,"form":form})

@login_required
def finance_reporting(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    default_domain=FinanceDomain.GENERAL if FinanceDomain.GENERAL in domains else FinanceDomain.IEA
    data=request.GET or {"finance_domain":default_domain,"as_of":date.today().isoformat()}
    form=FinanceReportFilterForm(data,team=team,allowed_domains=domains);report=None
    if form.is_valid():
        report=finance_report_for_user(request.user,team,form.cleaned_data["finance_domain"],start_date=form.cleaned_data.get("start_date"),end_date=form.cleaned_data.get("end_date"),as_of=form.cleaned_data.get("as_of"),season=form.cleaned_data.get("season"))
        if report is None:raise PermissionDenied
    return render(request,"portal/finance_reporting_v350.html",{"team":team,"form":form,"report":report})

@login_required
def finance_reporting_export(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    form=FinanceReportFilterForm(request.GET,team=team,allowed_domains=domains)
    if not form.is_valid():raise PermissionDenied
    report=finance_report_for_user(request.user,team,form.cleaned_data["finance_domain"],start_date=form.cleaned_data.get("start_date"),end_date=form.cleaned_data.get("end_date"),as_of=form.cleaned_data.get("as_of"),season=form.cleaned_data.get("season"))
    if report is None:raise PermissionDenied
    out=StringIO(newline="");writer=csv.writer(out)
    writer.writerow(["ArenaLine Finance Report",report.finance_domain])
    writer.writerow(["Income",f"{report.income:.2f}"]);writer.writerow(["Expenses",f"{report.expenses:.2f}"]);writer.writerow(["Net",f"{report.net:.2f}"]);writer.writerow(["Receivables",f"{report.receivables:.2f}"]);writer.writerow(["Overdue receivables",f"{report.overdue_receivables:.2f}"]);writer.writerow(["Payables",f"{report.payables:.2f}"]);writer.writerow(["Overdue payables",f"{report.overdue_payables:.2f}"])
    writer.writerow([]);writer.writerow(["Period","Income","Expenses","Net movement"])
    for row in report.period_rows:writer.writerow([f'{row["month"]:02d}/{row["year"]}',f'{row["income"]:.2f}',f'{row["expenses"]:.2f}',f'{row["net"]:.2f}'])
    writer.writerow([]);writer.writerow(["Category","Type","Total"])
    for row in report.category_rows:writer.writerow([row["category"],row["kind"],f'{row["total"]:.2f}'])
    writer.writerow([]);writer.writerow(["Financial account","Income","Expenses","Net"])
    for row in report.account_rows:writer.writerow([row["account"],f'{row["income"]:.2f}',f'{row["expenses"]:.2f}',f'{row["net"]:.2f}'])
    writer.writerow([]);writer.writerow(["Receivable account","Description","Due date","Aging bucket","Balance"])
    for row in report.aging_rows:writer.writerow([row["account"],row["description"],row["due_date"].isoformat() if row["due_date"] else "",row["bucket"],f'{row["balance"]:.2f}'])
    writer.writerow([]);writer.writerow(["Budget","Start","End","Planned income","Actual income","Income variance","Planned expenses","Actual expenses","Expense variance","Planned net","Actual net","Net variance"])
    for row in report.budget_rows:writer.writerow([row["name"],row["start_date"].isoformat(),row["end_date"].isoformat(),f'{row["planned_income"]:.2f}',f'{row["actual_income"]:.2f}',f'{row["income_variance"]:.2f}',f'{row["planned_expenses"]:.2f}',f'{row["actual_expenses"]:.2f}',f'{row["expense_variance"]:.2f}',f'{row["planned_net"]:.2f}',f'{row["actual_net"]:.2f}',f'{row["net_variance"]:.2f}'])
    writer.writerow([]);writer.writerow(["Payee","Description","Due date","Aging bucket","Balance"])
    for row in report.payable_aging_rows:writer.writerow([row["party"],row["description"],row["due_date"].isoformat() if row["due_date"] else "",row["bucket"],f'{row["balance"]:.2f}'])
    response=HttpResponse(out.getvalue(),content_type="text/csv")
    response["Content-Disposition"]=f'attachment; filename="arenaline-finance-report-{report.finance_domain}.csv"'
    return response

@login_required
def finance_receivable_account_add(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team);form=FinanceAccountForm(request.POST or None,team=team,allowed_domains=domains)
    if request.method=="POST" and form.is_valid():
        try:account=create_account_for_user(request.user,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Receivable account created.");return redirect("finance_receivable_account_detail",pk=account.pk)
    return render(request,"portal/finance_account_form_v350.html",{"team":team,"form":form})
@login_required
def finance_receivable_account_detail(request,pk):
    team,account=_account_for_request(request,pk);today=date.today();open_charges=[c for c in account.charges.filter(status=ReceivableCharge.Status.POSTED) if c.balance>ZERO]
    charge_rows=[{"charge":c,"state":c.lifecycle_status(today)} for c in open_charges]
    overdue_total=sum((c.balance for c in open_charges if c.lifecycle_status(today)=="overdue"),ZERO)
    return render(request,"portal/finance_receivable_account_v350.html",{"team":team,"account":account,"activity":account_activity(account),"people_links":account.people_links.filter(active=True).select_related("person"),"open_charges":open_charges,"charge_rows":charge_rows,"overdue_total":overdue_total,"posted_payments":account.payments.filter(status="posted").select_related("financial_transaction").prefetch_related("allocations__charge"),"unapplied_payments":[p for p in account.payments.filter(status="posted") if p.unapplied_amount>ZERO],"unapplied_credits":[c for c in account.credits.filter(status="posted").select_related("credit_rule") if c.unapplied_amount>ZERO],"posted_credits":account.credits.filter(status="posted").select_related("credit_rule").order_by("-credit_date","-id")})
@login_required
def finance_account_person_add(request,pk):
    team,account=_account_for_request(request,pk);form=FinanceAccountPersonForm(request.POST or None,team=team)
    if request.method=="POST" and form.is_valid():
        try:add_account_person_for_user(request.user,account.pk,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Account person added.");return redirect("finance_receivable_account_detail",pk=account.pk)
    return render(request,"portal/finance_account_person_form_v350.html",{"team":team,"account":account,"form":form})
@login_required
def finance_account_person_remove(request,pk,link_id):
    team,account=_account_for_request(request,pk)
    if request.method!="POST":raise PermissionDenied
    try:remove_account_person_for_user(request.user,account.pk,link_id=link_id,team=team)
    except ValidationError as exc:messages.error(request,str(exc))
    else:messages.success(request,"Account person removed.")
    return redirect("finance_receivable_account_detail",pk=account.pk)

def _operation_form(request,pk,form_class,title,submit_label,operation):
    team,account=_account_for_request(request,pk);initial={"charge_date":date.today(),"received_date":date.today(),"credit_date":date.today()};charge_id=request.GET.get("charge")
    if charge_id:
        try:selected=account.charges.get(pk=charge_id,status=ReceivableCharge.Status.POSTED)
        except (ReceivableCharge.DoesNotExist,ValueError):selected=None
        if selected and selected.balance>ZERO:initial["charge_id"]=selected.pk
    form=form_class(request.POST or None,initial=initial,**({"team":team,"finance_domain":account.finance_domain} if form_class is FinancePaymentForm else {}))
    if request.method=="POST" and form.is_valid():
        try:operation(request.user,account.pk,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,f"{submit_label} saved.");return redirect("finance_receivable_account_detail",pk=account.pk)
    return render(request,"portal/finance_operation_form_v350.html",{"team":team,"account":account,"form":form,"title":title,"submit_label":submit_label})
@login_required
def finance_charge_add(request,pk):return _operation_form(request,pk,FinanceChargeForm,"Add charge","Charge",create_charge_for_user)
@login_required
def finance_payment_add(request,pk):return _operation_form(request,pk,FinancePaymentForm,"Record payment","Payment",post_payment_for_user)
@login_required
def finance_credit_add(request,pk):return _operation_form(request,pk,FinanceCreditForm,"Add credit","Credit",post_credit_for_user)
@login_required
def finance_payment_allocate(request,pk,payment_id):
    team,account=_account_for_request(request,pk);form=FinanceAllocationForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        try:allocate_payment_for_user(request.user,account.pk,payment_id=payment_id,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Payment allocation saved.");return redirect("finance_receivable_account_detail",pk=account.pk)
    return render(request,"portal/finance_allocation_form_v350.html",{"account":account,"form":form,"source_kind":"Payment","charges":[c for c in account.charges.filter(status="posted") if c.balance>ZERO]})
@login_required
def finance_credit_allocate(request,pk,credit_id):
    team,account=_account_for_request(request,pk);form=FinanceAllocationForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        try:allocate_credit_for_user(request.user,account.pk,credit_id=credit_id,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Credit allocation saved.");return redirect("finance_receivable_account_detail",pk=account.pk)
    return render(request,"portal/finance_allocation_form_v350.html",{"account":account,"form":form,"source_kind":"Credit","charges":[c for c in account.charges.filter(status="posted") if c.balance>ZERO]})

@login_required
def finance_payment_allocate_oldest(request,pk,payment_id):
    team,account=_account_for_request(request,pk)
    if request.method!="POST":raise PermissionDenied
    try:allocations=allocate_payment_oldest_for_user(request.user,account.pk,payment_id=payment_id,team=team)
    except ValidationError as exc:messages.error(request,str(exc))
    else:messages.success(request,f"Payment applied to {len(allocations)} outstanding charge(s)." if allocations else "No outstanding charges were available for this payment.")
    return redirect("finance_receivable_account_detail",pk=account.pk)

@login_required
def finance_credit_allocate_oldest(request,pk,credit_id):
    team,account=_account_for_request(request,pk)
    if request.method!="POST":raise PermissionDenied
    try:allocations=allocate_credit_oldest_for_user(request.user,account.pk,credit_id=credit_id,team=team)
    except ValidationError as exc:messages.error(request,str(exc))
    else:messages.success(request,f"Credit applied to {len(allocations)} outstanding charge(s)." if allocations else "No outstanding charges were available for this credit.")
    return redirect("finance_receivable_account_detail",pk=account.pk)

@login_required
def finance_receivable_statement(request,pk):
    team,account=_account_for_request(request,pk);today=date.today()
    try:start_date=date.fromisoformat(request.GET.get("start")) if request.GET.get("start") else date(today.year,1,1);end_date=date.fromisoformat(request.GET.get("end")) if request.GET.get("end") else today
    except ValueError:start_date,end_date=date(today.year,1,1),today
    if end_date<start_date:start_date,end_date=end_date,start_date
    statement=statement_for_user(request.user,account.pk,start_date=start_date,end_date=end_date,team=team)
    if statement is None:raise PermissionDenied
    return render(request,"portal/finance_statement_v350.html",{"team":team,"account":account,"statement":statement,"start_date":start_date,"end_date":end_date})

@login_required
def finance_payment_void(request,pk,payment_id):
    team,account=_account_for_request(request,pk)
    try:payment=account.payments.select_related("financial_transaction").get(pk=payment_id,status="posted")
    except account.payments.model.DoesNotExist:raise PermissionDenied
    form=FinanceVoidPaymentForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        try:void_payment_for_user(request.user,account.pk,payment_id=payment.pk,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Payment voided.");return redirect("finance_receivable_account_detail",pk=account.pk)
    return render(request,"portal/finance_payment_void_v350.html",{"team":team,"account":account,"payment":payment,"form":form})

@login_required
def finance_payment_unallocate(request,pk,allocation_id):
    team,account=_account_for_request(request,pk)
    try:allocation=account.payments.model.objects.filter(account=account,allocations__pk=allocation_id).values_list("allocations__pk",flat=True).first()
    except (ValueError,TypeError):allocation=None
    if allocation is None:raise PermissionDenied
    form=FinanceUnallocateForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        try:unallocate_payment_for_user(request.user,account.pk,allocation_id=allocation_id,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Payment allocation removed. The funds are now available to reallocate.");return redirect("finance_receivable_account_detail",pk=account.pk)
    return render(request,"portal/finance_unallocate_v350.html",{"team":team,"account":account,"form":form})


@login_required
def finance_credit_unallocate(request,pk,allocation_id):
    team,account=_account_for_request(request,pk)
    try:allocation=account.credits.model.objects.filter(account=account,allocations__pk=allocation_id).values_list("allocations__pk",flat=True).first()
    except (ValueError,TypeError):allocation=None
    if allocation is None:raise PermissionDenied
    form=FinanceUnallocateForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        try:unallocate_credit_for_user(request.user,account.pk,allocation_id=allocation_id,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Credit allocation removed. The credit is now available to reallocate.");return redirect("finance_receivable_account_detail",pk=account.pk)
    return render(request,"portal/finance_unallocate_v350.html",{"team":team,"account":account,"form":form,"source_kind":"Credit"})


@login_required
def finance_bank_reconciliation(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    form=BankImportUploadForm(request.POST or None,request.FILES or None,team=team,allowed_domains=domains)
    if request.method=="POST" and form.is_valid():
        uploaded=form.cleaned_data["statement"];account=form.cleaned_data["financial_account"];profile=form.cleaned_data.get("profile")
        if profile and profile.financial_account_id!=account.pk:form.add_error("profile","Choose a profile saved for this bank account.")
        else:
            data=uploaded.read();file_type="xlsx" if uploaded.name.lower().endswith(".xlsx") else "csv"
            if profile:
                try:batch=stage_bank_import(team=team,financial_account=account,source_name=uploaded.name,data=data,file_type=file_type,column_mapping=profile.column_mapping,profile=profile)
                except ValidationError as exc:form.add_error(None,exc)
                else:messages.success(request,f"Statement staged with {batch.transactions.count()} transaction(s).");return redirect("finance_bank_import_batch",batch_id=batch.pk)
            else:
                request.session["finance_bank_import"]={"account_id":account.pk,"source_name":uploaded.name,"file_type":file_type,"data":data.hex()}
                return redirect("finance_bank_import_mapping")
    batches=BankImportBatch.objects.filter(team=team,finance_domain__in=domains).select_related("financial_account","profile").order_by("-imported_at")[:20]
    return render(request,"portal/finance_bank_reconciliation_v350.html",{"team":team,"form":form,"batches":batches})

@login_required
def finance_bank_import_mapping(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team);pending=request.session.get("finance_bank_import")
    if not pending: return redirect("finance_bank_reconciliation")
    try:account=FinancialAccount.objects.get(pk=pending["account_id"],team=team,finance_domain__in=domains)
    except FinancialAccount.DoesNotExist:raise PermissionDenied
    form=BankImportMappingForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        mapping={key:value for key,value in form.cleaned_data.items() if key!="profile_name" and value};data=bytes.fromhex(pending["data"])
        try:batch=stage_bank_import(team=team,financial_account=account,source_name=pending["source_name"],data=data,file_type=pending["file_type"],column_mapping=mapping)
        except ValidationError as exc:form.add_error(None,exc)
        else:
            profile_name=form.cleaned_data.get("profile_name")
            if profile_name:BankImportProfile.objects.update_or_create(team=team,financial_account=account,name=profile_name,defaults={"file_type":pending["file_type"],"column_mapping":mapping,"active":True})
            request.session.pop("finance_bank_import",None);messages.success(request,f"Statement staged with {batch.transactions.count()} transaction(s).");return redirect("finance_bank_import_batch",batch_id=batch.pk)
    return render(request,"portal/finance_bank_import_mapping_v350.html",{"team":team,"account":account,"form":form,"source_name":pending["source_name"]})

@login_required
def finance_bank_import_batch(request,batch_id):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    try:batch=BankImportBatch.objects.select_related("financial_account","profile").get(pk=batch_id,team=team,finance_domain__in=domains)
    except BankImportBatch.DoesNotExist:raise PermissionDenied
    rows=batch.transactions.prefetch_related("matches__financial_transaction").order_by("transaction_date","id")
    counts={status:batch.transactions.filter(status=status).count() for status in ("staged","matched","reconciled","ignored")}
    return render(request,"portal/finance_bank_import_batch_v350.html",{"team":team,"batch":batch,"rows":rows,"counts":counts})

@login_required
def finance_bank_generate_candidates(request,batch_id,row_id):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    if request.method!="POST":raise PermissionDenied
    try:row=ImportedBankTransaction.objects.select_related("batch").get(pk=row_id,batch_id=batch_id,batch__team=team,batch__finance_domain__in=domains)
    except ImportedBankTransaction.DoesNotExist:raise PermissionDenied
    try:matches=generate_match_candidates(row)
    except ValidationError as exc:messages.error(request,str(exc))
    else:
        if matches:messages.success(request,f"Found {len(matches)} possible ledger match(es). Review them before confirming.")
        else:messages.info(request,"No matching posted ledger transactions were found.")
    return redirect("finance_bank_import_batch",batch_id=batch_id)

@login_required
def finance_bank_confirm_match(request,batch_id,row_id,match_id):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    if request.method!="POST":raise PermissionDenied
    try:match=ReconciliationMatch.objects.select_related("imported_transaction__batch").get(pk=match_id,imported_transaction_id=row_id,imported_transaction__batch_id=batch_id,imported_transaction__batch__team=team,imported_transaction__batch__finance_domain__in=domains)
    except ReconciliationMatch.DoesNotExist:raise PermissionDenied
    try:confirm_reconciliation(match)
    except ValidationError as exc:messages.error(request,str(exc))
    else:messages.success(request,"Bank transaction reconciled to the selected ledger transaction.")
    return redirect("finance_bank_import_batch",batch_id=batch_id)


def _refresh_bank_batch_status(batch):
    """Mark a batch reviewed after row decisions; completion remains explicit."""
    if batch.status not in (BankImportBatch.Status.COMPLETED,BankImportBatch.Status.VOID) and batch.status!=BankImportBatch.Status.REVIEWED:
        batch.status=BankImportBatch.Status.REVIEWED
        batch.save(update_fields=["status"])
    return batch

@login_required
def finance_bank_ignore_row(request,batch_id,row_id):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    if request.method!="POST":raise PermissionDenied
    try:row=ImportedBankTransaction.objects.select_related("batch").get(pk=row_id,batch_id=batch_id,batch__team=team,batch__finance_domain__in=domains)
    except ImportedBankTransaction.DoesNotExist:raise PermissionDenied
    if row.status==ImportedBankTransaction.Status.RECONCILED:
        messages.error(request,"A reconciled bank transaction cannot be ignored.")
    else:
        row.matches.filter(status=ReconciliationMatch.Status.SUGGESTED).update(status=ReconciliationMatch.Status.REJECTED)
        row.status=ImportedBankTransaction.Status.IGNORED;row.save(update_fields=["status"])
        _refresh_bank_batch_status(row.batch);messages.success(request,"Bank transaction marked ignored. No ledger entry was changed.")
    return redirect("finance_bank_import_batch",batch_id=batch_id)

@login_required
def finance_bank_complete_review(request,batch_id):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    if request.method!="POST":raise PermissionDenied
    try:batch=BankImportBatch.objects.get(pk=batch_id,team=team,finance_domain__in=domains)
    except BankImportBatch.DoesNotExist:raise PermissionDenied
    unresolved=batch.transactions.filter(status__in=[ImportedBankTransaction.Status.STAGED,ImportedBankTransaction.Status.MATCHED]).count()
    if unresolved:
        batch.status=BankImportBatch.Status.REVIEWED;batch.save(update_fields=["status"])
        messages.error(request,f"{unresolved} transaction(s) still need reconciliation or an explicit ignore decision.")
    else:
        batch.status=BankImportBatch.Status.COMPLETED;batch.save(update_fields=["status"])
        messages.success(request,"Bank statement review completed.")
    return redirect("finance_bank_import_batch",batch_id=batch_id)


@login_required
def finance_accounting_exports(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team)
    profiles=AccountingExportProfile.objects.filter(team=team,finance_domain__in=domains).order_by("finance_domain","name")
    form=AccountingExportProfileForm(request.POST or None,allowed_domains=domains)
    if request.method=="POST" and form.is_valid():
        profile=form.save(commit=False);profile.team=team
        profile.column_mapping=form.cleaned_data["column_mapping"]
        profile.full_clean();profile.save()
        messages.success(request,"Accounting export profile created.")
        return redirect("finance_accounting_export_detail",profile_id=profile.pk)
    return render(request,"portal/finance_accounting_exports_v350.html",{"team":team,"profiles":profiles,"form":form})

def _export_profile_for_user(user,profile_id):
    team=_team_for_finance_user(user);domains=allowed_finance_domains(user,team)
    try:return AccountingExportProfile.objects.get(pk=profile_id,team=team,finance_domain__in=domains)
    except AccountingExportProfile.DoesNotExist:raise PermissionDenied

@login_required
def finance_accounting_export_edit(request,profile_id):
    profile=_export_profile_for_user(request.user,profile_id);domains=allowed_finance_domains(request.user,profile.team)
    form=AccountingExportProfileForm(request.POST or None,instance=profile,allowed_domains=domains)
    if request.method=="POST" and form.is_valid():
        updated=form.save(commit=False);updated.team=profile.team;updated.column_mapping=form.cleaned_data["column_mapping"];updated.full_clean();updated.save()
        messages.success(request,"Accounting export profile updated.")
        return redirect("finance_accounting_export_detail",profile_id=profile.pk)
    return render(request,"portal/finance_accounting_export_edit_v350.html",{"profile":profile,"form":form})

@login_required
def finance_accounting_export_detail(request,profile_id):
    profile=_export_profile_for_user(request.user,profile_id);form=AccountingExportRunForm(request.GET)
    rows=[]
    if form.is_valid():rows=normalized_export_rows(request.user,profile,start_date=form.cleaned_data.get("start_date"),end_date=form.cleaned_data.get("end_date"))[:25]
    return render(request,"portal/finance_accounting_export_detail_v350.html",{"profile":profile,"form":form,"rows":rows,"headers":list(profile.column_mapping)})

@login_required
def finance_accounting_export_download(request,profile_id):
    profile=_export_profile_for_user(request.user,profile_id);form=AccountingExportRunForm(request.GET)
    if not form.is_valid():raise PermissionDenied
    data,mime=render_accounting_export(request.user,profile,start_date=form.cleaned_data.get("start_date"),end_date=form.cleaned_data.get("end_date"))
    extension="xlsx" if profile.file_type==AccountingExportProfile.FileType.XLSX else "csv"
    response=HttpResponse(data,content_type=mime)
    parts=["arenaline",profile.finance_domain,slugify(profile.name) or "export"]
    if form.cleaned_data.get("start_date"):parts.append(form.cleaned_data["start_date"].isoformat())
    if form.cleaned_data.get("end_date"):parts.append(form.cleaned_data["end_date"].isoformat())
    filename="-".join(parts)
    response["Content-Disposition"]=f'attachment; filename="{filename}.{extension}"'
    return response
