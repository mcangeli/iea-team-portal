"""ArenaLine v3.5 finance workspace views."""
from datetime import date
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render
from portal.forms_v350_finance import FinanceAccountForm, FinanceAccountPersonForm, FinanceAllocationForm, FinanceChargeForm, FinanceCreditForm, FinancePaymentForm, FinanceUnallocateForm, BankImportMappingForm, BankImportUploadForm, FinanceVoidPaymentForm
from portal.model_modules.finance import BankImportBatch, BankImportProfile, FinanceDomain, ImportedBankTransaction, ReceivableCharge, ReconciliationMatch
from portal.models import FinancialAccount
from portal.platform import organization_for_view_user
from portal.services.finance_access import allowed_finance_domains, finance_account_for_user, finance_accounts_for_user
from portal.services.finance_imports import stage_bank_import
from portal.services.finance_reconciliation import confirm_reconciliation, generate_match_candidates\nfrom portal.services.finance_operations import add_account_person_for_user, allocate_credit_for_user, allocate_payment_for_user, create_account_for_user, create_charge_for_user, post_credit_for_user, post_payment_for_user, remove_account_person_for_user, unallocate_payment_for_user, void_payment_for_user
from portal.services.finance_statements import account_activity, statement_for_user
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
def finance_receivable_account_add(request):
    team=_team_for_finance_user(request.user);domains=allowed_finance_domains(request.user,team);form=FinanceAccountForm(request.POST or None,team=team,allowed_domains=domains)
    if request.method=="POST" and form.is_valid():
        try:account=create_account_for_user(request.user,team=team,**form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:messages.success(request,"Receivable account created.");return redirect("finance_receivable_account_detail",pk=account.pk)
    return render(request,"portal/finance_account_form_v350.html",{"team":team,"form":form})
@login_required
def finance_receivable_account_detail(request,pk):
    team,account=_account_for_request(request,pk);open_charges=[c for c in account.charges.filter(status=ReceivableCharge.Status.POSTED) if c.balance>ZERO]
    return render(request,"portal/finance_receivable_account_v350.html",{"team":team,"account":account,"activity":account_activity(account),"people_links":account.people_links.filter(active=True).select_related("person"),"open_charges":open_charges,"posted_payments":account.payments.filter(status="posted").select_related("financial_transaction").prefetch_related("allocations__charge"),"unapplied_payments":[p for p in account.payments.filter(status="posted") if p.unapplied_amount>ZERO],"unapplied_credits":[c for c in account.credits.filter(status="posted") if c.unapplied_amount>ZERO]})
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
    return render(request,"portal/finance_bank_import_batch_v350.html",{"team":team,"batch":batch,"rows":rows})

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
