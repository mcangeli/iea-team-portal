"""Resolve operational participants to explicit receivable accounts."""
from django.core.exceptions import ValidationError
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableAccountPerson

def resolve_participant_account(person, *, finance_domain=FinanceDomain.GENERAL):
    """Return the one active account explicitly linking person as a participant.

    No fallback to primary_person, responsible party, or billing contact is used:
    operational billing must be explicit and unambiguous.
    """
    links=(ReceivableAccountPerson.objects
        .filter(person=person,role=ReceivableAccountPerson.Role.PARTICIPANT,active=True,
                account__team=person.team,account__finance_domain=finance_domain,
                account__status=ReceivableAccount.Status.ACTIVE)
        .select_related("account").order_by("account_id"))
    accounts=[]
    seen=set()
    for link in links:
        if link.account_id not in seen:
            seen.add(link.account_id);accounts.append(link.account)
    if not accounts:
        return None
    if len(accounts)>1:
        raise ValidationError(f"{person} is linked to multiple active receivable accounts in the {finance_domain} finance domain.")
    return accounts[0]
