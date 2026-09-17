from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import FinanceDomain, ReceivableAccount
from portal.model_modules.people import Person
from portal.models import Team, UserProfile
from portal.services.finance_operations import (
    allocate_credit_for_user,
    allocate_payment_for_user,
    create_charge_for_user,
    post_credit_for_user,
    post_payment_for_user,
)


class FinanceOperationsTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Operations Barn")
        self.general = ReceivableAccount.objects.create(team=self.team, name="General Account", finance_domain=FinanceDomain.GENERAL)
        self.iea = ReceivableAccount.objects.create(team=self.team, name="IEA Account", finance_domain=FinanceDomain.IEA)

    def _user(self, username, capability=None, role=UserProfile.Role.PARENT):
        user = User.objects.create_user(username=username, password="pass12345")
        profile = user.profile
        profile.team = self.team
        profile.role = role
        profile.save(update_fields=["team", "role"])
        person = Person.objects.create(team=self.team, user=user, first_name=username, last_name="Tester")
        if capability:
            OrganizationCapabilityAssignment.objects.create(team=self.team, person=person, capability=capability)
        return user

    def test_admin_can_create_general_charge(self):
        user = self._user("admin", role=UserProfile.Role.ADMIN)
        charge = create_charge_for_user(user, self.general.pk, description="September board", amount="600.00", charge_date=date(2026, 9, 1), team=self.team)
        self.assertEqual(charge.account, self.general)
        self.assertEqual(self.general.amount_due, charge.amount)

    def test_iea_treasurer_cannot_create_general_charge(self):
        user = self._user("iea", OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        with self.assertRaises(PermissionDenied):
            create_charge_for_user(user, self.general.pk, description="Board", amount="100.00", charge_date=date(2026, 9, 1), team=self.team)

    def test_iea_treasurer_can_create_iea_charge(self):
        user = self._user("iea-ok", OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        charge = create_charge_for_user(user, self.iea.pk, description="Show fee", amount="75.00", charge_date=date(2026, 9, 1), team=self.team)
        self.assertEqual(charge.account, self.iea)

    def test_general_treasurer_can_post_payment_to_either_domain(self):
        user = self._user("general", OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE)
        general_payment = post_payment_for_user(user, self.general.pk, amount="100.00", received_date=date(2026, 9, 2), team=self.team)
        iea_payment = post_payment_for_user(user, self.iea.pk, amount="50.00", received_date=date(2026, 9, 2), team=self.team)
        self.assertEqual(general_payment.account, self.general)
        self.assertEqual(iea_payment.account, self.iea)

    def test_payment_can_be_posted_and_partially_allocated(self):
        user = self._user("split", role=UserProfile.Role.ADMIN)
        charge = create_charge_for_user(user, self.general.pk, description="Board", amount="200.00", charge_date=date(2026, 9, 1), team=self.team)
        payment = post_payment_for_user(user, self.general.pk, amount="150.00", received_date=date(2026, 9, 2), team=self.team)
        allocation = allocate_payment_for_user(user, self.general.pk, payment_id=payment.pk, charge_id=charge.pk, amount="75.00", team=self.team)
        self.assertEqual(allocation.amount, charge.amount - charge.balance)
        self.assertEqual(payment.unapplied_amount, allocation.amount)

    def test_credit_can_be_posted_and_allocated(self):
        user = self._user("credit", role=UserProfile.Role.ADMIN)
        charge = create_charge_for_user(user, self.general.pk, description="Lesson", amount="80.00", charge_date=date(2026, 9, 1), team=self.team)
        credit = post_credit_for_user(user, self.general.pk, description="Courtesy credit", amount="25.00", credit_date=date(2026, 9, 2), team=self.team)
        allocation = allocate_credit_for_user(user, self.general.pk, credit_id=credit.pk, charge_id=charge.pk, team=self.team)
        self.assertEqual(allocation.amount, credit.amount)
        self.assertEqual(credit.unapplied_amount, 0)

    def test_source_from_other_account_cannot_be_allocated(self):
        user = self._user("boundary", role=UserProfile.Role.ADMIN)
        charge = create_charge_for_user(user, self.general.pk, description="Board", amount="100.00", charge_date=date(2026, 9, 1), team=self.team)
        payment = post_payment_for_user(user, self.iea.pk, amount="100.00", received_date=date(2026, 9, 2), team=self.team)
        with self.assertRaises(ValidationError):
            allocate_payment_for_user(user, self.general.pk, payment_id=payment.pk, charge_id=charge.pk, team=self.team)

    def test_charge_from_other_account_cannot_be_targeted(self):
        user = self._user("target-boundary", role=UserProfile.Role.ADMIN)
        charge = create_charge_for_user(user, self.iea.pk, description="Show fee", amount="100.00", charge_date=date(2026, 9, 1), team=self.team)
        payment = post_payment_for_user(user, self.general.pk, amount="100.00", received_date=date(2026, 9, 2), team=self.team)
        with self.assertRaises(ValidationError):
            allocate_payment_for_user(user, self.general.pk, payment_id=payment.pk, charge_id=charge.pk, team=self.team)
