"""Authorized write-side operations for the ArenaLine v3.5 receivables ledger."""
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from portal.model_modules.finance import ReceivableAccount, ReceivableAccountPerson, ReceivableAllocation, ReceivableCharge
from portal.services.finance_access import can_manage_finance_domain, finance_account_for_user
from portal.services.finance_receivables import allocate_source, allocate_source_oldest, post_credit, post_payment, void_payment

def _authorized_account(user,account_id,team=None):
    account=finance_account_for_user(user,account_id,team)
    if account is None: raise PermissionDenied
    return account

def _posted_charge(account,charge_id):
    try:return account.charges.get(pk=charge_id,status=ReceivableCharge.Status.POSTED)
    except ReceivableCharge.DoesNotExist as exc:raise ValidationError("Charge is not available on this receivable account.") from exc

@transaction.atomic
def create_account_for_user(user,*,team,name,finance_domain,primary_person=None,notes=""):
    if not can_manage_finance_domain(user,finance_domain,team):raise PermissionDenied
    account=ReceivableAccount(team=team,name=name.strip(),finance_domain=finance_domain,primary_person=primary_person,notes=notes.strip());account.full_clean();account.save()
    if primary_person:ReceivableAccountPerson.objects.create(account=account,person=primary_person,role=ReceivableAccountPerson.Role.RESPONSIBLE_PARTY,statement_recipient=True)
    return account

@transaction.atomic
def add_account_person_for_user(user,account_id,*,person,role,statement_recipient=False,notes="",team=None):
    account=_authorized_account(user,account_id,team)
    link=ReceivableAccountPerson(account=account,person=person,role=role,statement_recipient=statement_recipient,notes=notes.strip());link.full_clean();link.save();return link

@transaction.atomic
def remove_account_person_for_user(user,account_id,*,link_id,team=None):
    account=_authorized_account(user,account_id,team)
    try:link=account.people_links.get(pk=link_id)
    except ReceivableAccountPerson.DoesNotExist as exc:raise ValidationError("Person relationship is not available on this receivable account.") from exc
    link.active=False;link.statement_recipient=False;link.save(update_fields=["active","statement_recipient"])

@transaction.atomic
def create_charge_for_user(user,account_id,*,description,amount,charge_date,due_date=None,charge_type="",season=None,notes="",team=None):
    account=_authorized_account(user,account_id,team);charge=ReceivableCharge(account=account,description=description.strip(),amount=Decimal(amount),charge_date=charge_date,due_date=due_date,charge_type=charge_type.strip(),season=season,notes=notes.strip());charge.full_clean();charge.save();return charge
@transaction.atomic
def post_payment_for_user(user,account_id,*,amount,received_date,charge_id=None,method="",reference="",notes="",deposit_account=None,income_category=None,season=None,team=None):
    account=_authorized_account(user,account_id,team);charge=_posted_charge(account,charge_id) if charge_id else None;return post_payment(account=account,amount=Decimal(amount),received_date=received_date,charge=charge,method=method.strip(),reference=reference.strip(),notes=notes.strip(),deposit_account=deposit_account,income_category=income_category,season=season)
@transaction.atomic
def post_credit_for_user(user,account_id,*,description,amount,credit_date,charge_id=None,credit_type="",notes="",season=None,team=None):
    account=_authorized_account(user,account_id,team);charge=_posted_charge(account,charge_id) if charge_id else None;return post_credit(account=account,description=description.strip(),amount=Decimal(amount),credit_date=credit_date,charge=charge,credit_type=credit_type.strip(),notes=notes.strip(),season=season)
@transaction.atomic
def allocate_payment_for_user(user,account_id,*,payment_id,charge_id,amount=None,notes="",team=None):
    account=_authorized_account(user,account_id,team);charge=_posted_charge(account,charge_id)
    try:payment=account.payments.get(pk=payment_id,status=account.payments.model.Status.POSTED)
    except account.payments.model.DoesNotExist as exc:raise ValidationError("Payment is not available on this receivable account.") from exc
    return allocate_source(charge=charge,payment=payment,amount=amount,notes=notes.strip())
@transaction.atomic
def allocate_credit_for_user(user,account_id,*,credit_id,charge_id,amount=None,notes="",team=None):
    account=_authorized_account(user,account_id,team);charge=_posted_charge(account,charge_id)
    try:credit=account.credits.get(pk=credit_id,status=account.credits.model.Status.POSTED)
    except account.credits.model.DoesNotExist as exc:raise ValidationError("Credit is not available on this receivable account.") from exc
    return allocate_source(charge=charge,credit=credit,amount=amount,notes=notes.strip())


@transaction.atomic
def allocate_payment_oldest_for_user(user,account_id,*,payment_id,notes="",team=None):
    account=_authorized_account(user,account_id,team)
    try:payment=account.payments.get(pk=payment_id,status=account.payments.model.Status.POSTED)
    except account.payments.model.DoesNotExist as exc:raise ValidationError("Payment is not available on this receivable account.") from exc
    return allocate_source_oldest(payment=payment,notes=notes.strip())

@transaction.atomic
def allocate_credit_oldest_for_user(user,account_id,*,credit_id,notes="",team=None):
    account=_authorized_account(user,account_id,team)
    try:credit=account.credits.get(pk=credit_id,status=account.credits.model.Status.POSTED)
    except account.credits.model.DoesNotExist as exc:raise ValidationError("Credit is not available on this receivable account.") from exc
    return allocate_source_oldest(credit=credit,notes=notes.strip())


@transaction.atomic
def void_payment_for_user(user,account_id,*,payment_id,reason="",team=None):
    account=_authorized_account(user,account_id,team)
    try: payment=account.payments.get(pk=payment_id)
    except account.payments.model.DoesNotExist as exc: raise ValidationError("Payment is not available on this receivable account.") from exc
    return void_payment(payment=payment,user=user,reason=reason)

def _void_allocation_for_account(account,allocation,reason=""):
    allocation.status=ReceivableAllocation.Status.VOID
    note=reason.strip()
    if note:allocation.notes=((allocation.notes+" | ") if allocation.notes else "")+f"Unallocated: {note}"
    allocation.full_clean()
    allocation.save(update_fields=["status","notes"])
    return allocation

@transaction.atomic
def unallocate_payment_for_user(user,account_id,*,allocation_id,reason="",team=None):
    account=_authorized_account(user,account_id,team)
    try:allocation=ReceivableAllocation.objects.select_related("charge","payment").get(pk=allocation_id,payment__account=account,status=ReceivableAllocation.Status.POSTED)
    except ReceivableAllocation.DoesNotExist as exc:raise ValidationError("Payment allocation is not available on this receivable account.") from exc
    return _void_allocation_for_account(account,allocation,reason)

@transaction.atomic
def unallocate_credit_for_user(user,account_id,*,allocation_id,reason="",team=None):
    account=_authorized_account(user,account_id,team)
    try:allocation=ReceivableAllocation.objects.select_related("charge","credit").get(pk=allocation_id,credit__account=account,status=ReceivableAllocation.Status.POSTED)
    except ReceivableAllocation.DoesNotExist as exc:raise ValidationError("Credit allocation is not available on this receivable account.") from exc
    return _void_allocation_for_account(account,allocation,reason)
