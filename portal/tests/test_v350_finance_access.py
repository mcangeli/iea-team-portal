from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableCharge, ReceivableCredit, ReceivablePayment
from portal.model_modules.people import Person
from portal.models import CommitteeAssignment, Season, Team, UserProfile
from portal.context_processors import portal_context
from portal.services.finance_access import (
    allowed_finance_domains,
    finance_account_for_user,
    finance_accounts_for_user,
    finance_charges_for_user,
    finance_credits_for_user,
    finance_payments_for_user,
)


class FinanceAccessBoundaryTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Preview 2 Barn")
        self.other_team = Team.objects.create(name="Other Barn")
        self.general = ReceivableAccount.objects.create(team=self.team, name="General Family", finance_domain=FinanceDomain.GENERAL)
        self.iea = ReceivableAccount.objects.create(team=self.team, name="IEA Family", finance_domain=FinanceDomain.IEA)
        self.other = ReceivableAccount.objects.create(team=self.other_team, name="Other Family", finance_domain=FinanceDomain.GENERAL)
        self.general_charge = ReceivableCharge.objects.create(account=self.general, description="Board", amount="100.00", charge_date=date(2026, 9, 1))
        self.iea_charge = ReceivableCharge.objects.create(account=self.iea, description="Show fee", amount="50.00", charge_date=date(2026, 9, 1))
        self.general_credit = ReceivableCredit.objects.create(account=self.general, description="Credit", amount="10.00", credit_date=date(2026, 9, 2))
        self.iea_payment = ReceivablePayment.objects.create(account=self.iea, amount="20.00", received_date=date(2026, 9, 2))

    def _user(self, username, role=UserProfile.Role.PARENT):
        user = User.objects.create_user(username=username, password="pass12345")
        profile = user.profile
        profile.team = self.team
        profile.role = role
        profile.save(update_fields=["team", "role"])
        person = Person.objects.create(team=self.team, user=user, first_name=username, last_name="Tester")
        return user, person

    def _capability(self, person, capability, **kwargs):
        return OrganizationCapabilityAssignment.objects.create(team=self.team, person=person, capability=capability, **kwargs)

    def test_admin_can_see_both_domains(self):
        user, _ = self._user("finance-admin", UserProfile.Role.ADMIN)
        self.assertEqual(allowed_finance_domains(user, self.team), frozenset({FinanceDomain.GENERAL, FinanceDomain.IEA}))
        self.assertEqual(set(finance_accounts_for_user(user, self.team)), {self.general, self.iea})

    def test_general_treasurer_capability_can_see_both_domains(self):
        user, person = self._user("general-treasurer")
        self._capability(person, OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE)
        self.assertEqual(set(finance_accounts_for_user(user, self.team)), {self.general, self.iea})

    def test_iea_treasurer_capability_cannot_see_general_domain(self):
        user, person = self._user("iea-treasurer")
        self._capability(person, OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.assertEqual(list(finance_accounts_for_user(user, self.team)), [self.iea])
        self.assertIsNone(finance_account_for_user(user, self.general.pk, self.team))
        self.assertEqual(list(finance_charges_for_user(user, self.team)), [self.iea_charge])
        self.assertEqual(list(finance_credits_for_user(user, self.team)), [])
        self.assertEqual(list(finance_payments_for_user(user, self.team)), [self.iea_payment])

    def test_legacy_treasurer_role_is_iea_only(self):
        user, _ = self._user("legacy-treasurer")
        season = Season.objects.create(team=self.team, name="2026-27", start_date=date(2026, 8, 1), end_date=date(2027, 7, 31))
        CommitteeAssignment.objects.create(team=self.team, season=season, user=user, role=CommitteeAssignment.Role.TREASURER, active=True)
        self.assertEqual(allowed_finance_domains(user, self.team), frozenset({FinanceDomain.IEA}))
        self.assertEqual(list(finance_accounts_for_user(user, self.team)), [self.iea])

    def test_unprivileged_user_gets_no_organization_finance_queryset(self):
        user, _ = self._user("ordinary-parent")
        self.assertEqual(list(finance_accounts_for_user(user, self.team)), [])
        self.assertEqual(list(finance_charges_for_user(user, self.team)), [])

    def test_other_organization_never_leaks_into_finance_queryset(self):
        user, _ = self._user("admin-boundary", UserProfile.Role.ADMIN)
        self.assertNotIn(self.other, finance_accounts_for_user(user, self.team))

    def test_inactive_capability_does_not_grant_access(self):
        user, person = self._user("inactive-finance")
        self._capability(person, OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE, active=False)
        self.assertEqual(list(finance_accounts_for_user(user, self.team)), [])

    def test_future_capability_does_not_grant_access_early(self):
        user, person = self._user("future-finance")
        self._capability(person, OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE, start_date=date.today() + timedelta(days=1))
        self.assertEqual(list(finance_accounts_for_user(user, self.team)), [])

    def test_expired_capability_does_not_grant_access(self):
        user, person = self._user("expired-finance")
        self._capability(person, OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE, end_date=date.today() - timedelta(days=1))
        self.assertEqual(list(finance_accounts_for_user(user, self.team)), [])

    def test_superuser_can_see_both_domains(self):
        user = User.objects.create_superuser(username="root-finance", email="root@example.com", password="pass12345")
        self.assertEqual(set(finance_accounts_for_user(user, self.team)), {self.general, self.iea})

    def test_context_exposes_general_finance_domains_without_iea_leakage(self):
        user, person = self._user("general-nav")
        self._capability(person, OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE)
        request = RequestFactory().get("/")
        request.user = user
        context = portal_context(request)
        self.assertTrue(context["portal_can_finance"])
        self.assertEqual(context["portal_finance_domains"], frozenset({FinanceDomain.GENERAL, FinanceDomain.IEA}))

    def test_context_exposes_iea_only_finance_domain(self):
        user, person = self._user("iea-nav")
        self._capability(person, OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        request = RequestFactory().get("/")
        request.user = user
        context = portal_context(request)
        self.assertTrue(context["portal_can_finance"])
        self.assertEqual(context["portal_finance_domains"], frozenset({FinanceDomain.IEA}))

    def test_context_hides_finance_for_unprivileged_user(self):
        user, _ = self._user("no-finance-nav")
        request = RequestFactory().get("/")
        request.user = user
        context = portal_context(request)
        self.assertFalse(context["portal_can_finance"])
        self.assertEqual(context["portal_finance_domains"], frozenset())
