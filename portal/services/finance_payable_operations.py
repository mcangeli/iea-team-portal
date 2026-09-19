"""Authorized write-side operations for ArenaLine v3.7 accounts payable."""
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from portal.model_modules.finance import PayableParty, PayablePayment
from portal.services.finance_access import (
    can_manage_finance_domain,
    payable_obligation_for_user,
    payable_party_for_user,
)
from portal.services.finance_payables import create_obligation, post_payable_payment, void_payable_payment


@transaction.atomic
def create_payable_party_for_user(user, *, team, name, finance_domain, party_type=PayableParty.PartyType.VENDOR,
                                  contact_person=None, email="", phone="", notes=""):
    if not can_manage_finance_domain(user, finance_domain, team):
        raise PermissionDenied
    party = PayableParty(
        team=team, name=name.strip(), finance_domain=finance_domain, party_type=party_type,
        contact_person=contact_person, email=email.strip(), phone=phone.strip(), notes=notes.strip(),
    )
    party.full_clean()
    party.save()
    return party


@transaction.atomic
def create_payable_obligation_for_user(user, party_id, *, expense_category, description, amount,
                                       obligation_date, due_date=None, season=None, reference="", notes="", team=None):
    party = payable_party_for_user(user, party_id, team)
    if party is None:
        raise PermissionDenied
    return create_obligation(
        party=party, expense_category=expense_category, description=description, amount=Decimal(amount),
        obligation_date=obligation_date, due_date=due_date, season=season, reference=reference, notes=notes,
    )


@transaction.atomic
def post_payable_payment_for_user(user, obligation_id, *, amount, paid_date, payment_account,
                                  method="", reference="", notes="", team=None):
    obligation = payable_obligation_for_user(user, obligation_id, team)
    if obligation is None:
        raise PermissionDenied
    return post_payable_payment(
        obligation=obligation, amount=Decimal(amount), paid_date=paid_date, payment_account=payment_account,
        method=method, reference=reference, notes=notes,
    )


@transaction.atomic
def void_payable_payment_for_user(user, obligation_id, *, payment_id, reason="", team=None):
    obligation = payable_obligation_for_user(user, obligation_id, team)
    if obligation is None:
        raise PermissionDenied
    try:
        payment = obligation.payments.get(pk=payment_id)
    except PayablePayment.DoesNotExist as exc:
        raise ValidationError("Payment is not available on this payable obligation.") from exc
    return void_payable_payment(payment=payment, user=user, reason=reason)
