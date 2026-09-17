"""Finance-domain authorization and queryset boundary for ArenaLine v3.5.

All new finance views, statements, reports, imports, exports and reconciliation
workflows should enter the finance domain through this module rather than
filtering ledger models directly.
"""
from django.db.models import Q
from django.utils import timezone

from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import FinanceDomain, ReceivableAccount
from portal.model_modules.people import Person
from portal.models import CommitteeAssignment, UserProfile
from portal.platform import organization_for_view_user


CAPABILITY_IEA_FINANCE = OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE
CAPABILITY_ALL_FINANCE = OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE


def _login_person(user):
    if not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.arena_person
    except Person.DoesNotExist:
        return None


def _active_capability_qs(user, team):
    person = _login_person(user)
    if not person or person.team_id != team.id:
        return OrganizationCapabilityAssignment.objects.none()
    today = timezone.localdate()
    return OrganizationCapabilityAssignment.objects.filter(
        team=team,
        person=person,
        active=True,
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today),
        Q(end_date__isnull=True) | Q(end_date__gte=today),
    )


def _has_capability(user, team, capability):
    return _active_capability_qs(user, team).filter(capability=capability).exists()


def _is_admin(user, team):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.team_id == team.id and profile.role == UserProfile.Role.ADMIN)


def _legacy_iea_treasurer(user, team):
    """Compatibility bridge: the historical Treasurer role is IEA-only in v3.5."""
    if not getattr(user, "is_authenticated", False):
        return False
    return CommitteeAssignment.objects.filter(
        user=user,
        active=True,
        role=CommitteeAssignment.Role.TREASURER,
        season__team=team,
    ).exists()


def allowed_finance_domains(user, team=None):
    """Return finance domains visible to the caller for one organization."""
    if not getattr(user, "is_authenticated", False):
        return frozenset()
    team = team or organization_for_view_user(user)
    if not team:
        return frozenset()
    if _is_admin(user, team) or _has_capability(user, team, CAPABILITY_ALL_FINANCE):
        return frozenset({FinanceDomain.GENERAL, FinanceDomain.IEA})
    if _has_capability(user, team, CAPABILITY_IEA_FINANCE) or _legacy_iea_treasurer(user, team):
        return frozenset({FinanceDomain.IEA})
    return frozenset()


def can_manage_finance_domain(user, finance_domain, team=None):
    return finance_domain in allowed_finance_domains(user, team)


def finance_accounts_for_user(user, team=None):
    """Queryset-safe account visibility. Unauthorized domains never enter the queryset."""
    if not getattr(user, "is_authenticated", False):
        return ReceivableAccount.objects.none()
    team = team or organization_for_view_user(user)
    if not team:
        return ReceivableAccount.objects.none()
    domains = allowed_finance_domains(user, team)
    if not domains:
        return ReceivableAccount.objects.none()
    return ReceivableAccount.objects.filter(team=team, finance_domain__in=domains)


def finance_account_for_user(user, pk, team=None):
    return finance_accounts_for_user(user, team).filter(pk=pk).first()


def finance_charges_for_user(user, team=None):
    from portal.model_modules.finance import ReceivableCharge
    accounts = finance_accounts_for_user(user, team)
    return ReceivableCharge.objects.filter(account__in=accounts)


def finance_credits_for_user(user, team=None):
    from portal.model_modules.finance import ReceivableCredit
    accounts = finance_accounts_for_user(user, team)
    return ReceivableCredit.objects.filter(account__in=accounts)


def finance_payments_for_user(user, team=None):
    from portal.model_modules.finance import ReceivablePayment
    accounts = finance_accounts_for_user(user, team)
    return ReceivablePayment.objects.filter(account__in=accounts)


def finance_allocations_for_user(user, team=None):
    from portal.model_modules.finance import ReceivableAllocation
    accounts = finance_accounts_for_user(user, team)
    return ReceivableAllocation.objects.filter(charge__account__in=accounts)
