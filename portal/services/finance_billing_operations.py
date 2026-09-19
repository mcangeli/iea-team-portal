"""Authorized billing-rule operations for ArenaLine v3.7.1."""
from django.core.exceptions import PermissionDenied
from django.db import transaction
from portal.model_modules.finance import ReceivableBillingRule
from portal.services.finance_access import finance_account_for_user, receivable_billing_rule_for_user, receivable_billing_rules_for_user
from portal.services.finance_billing import generate_monthly_charge, generate_monthly_charges

@transaction.atomic
def create_billing_rule_for_user(user,account_id,*,description,amount,cadence,charge_type="",due_days=0,notes="",team=None):
    account=finance_account_for_user(user,account_id,team)
    if account is None: raise PermissionDenied
    rule=ReceivableBillingRule(account=account,description=description.strip(),amount=amount,cadence=cadence,charge_type=charge_type.strip(),due_days=due_days,notes=notes.strip())
    rule.full_clean();rule.save();return rule

@transaction.atomic
def generate_monthly_rule_for_user(user,rule_id,*,billing_month,season=None,team=None):
    rule=receivable_billing_rule_for_user(user,rule_id,team)
    if rule is None: raise PermissionDenied
    return generate_monthly_charge(rule=rule,billing_month=billing_month,season=season)

@transaction.atomic
def generate_monthly_domain_for_user(user,*,billing_month,finance_domain,season=None,team=None):
    rules=receivable_billing_rules_for_user(user,team).filter(account__finance_domain=finance_domain,active=True,cadence=ReceivableBillingRule.Cadence.MONTHLY).select_related("account")
    return generate_monthly_charges(rules=rules,billing_month=billing_month,season=season)
