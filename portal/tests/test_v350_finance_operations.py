from datetime import date
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import FinanceDomain, ReceivableAccount
from portal.model_modules.people import Person
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Team, UserProfile
from portal.services.finance_operations import add_account_person_for_user, allocate_credit_for_user, allocate_payment_for_user, create_account_for_user, create_charge_for_user, post_credit_for_user, post_payment_for_user, remove_account_person_for_user, unallocate_credit_for_user, unallocate_payment_for_user, void_payment_for_user


class FinanceOperationsTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Operations Barn")
        self.general = ReceivableAccount.objects.create(team=self.team, name="General Account", finance_domain=FinanceDomain.GENERAL)
        self.iea = ReceivableAccount.objects.create(team=self.team, name="IEA Account", finance_domain=FinanceDomain.IEA)

    def _user(self, username, capability=None, role=UserProfile.Role.PARENT):
        user = User.objects.create_user(username=username, password="pass12345"); profile = user.profile; profile.team = self.team; profile.role = role; profile.save(update_fields=["team", "role"])
        person = Person.objects.create(team=self.team, user=user, first_name=username, last_name="Tester")
        if capability: OrganizationCapabilityAssignment.objects.create(team=self.team, person=person, capability=capability)
        return user

    def test_admin_can_create_general_receivable_account(self):
        user = self._user("account-admin", role=UserProfile.Role.ADMIN)
        person = Person.objects.create(team=self.team, first_name="Barn", last_name="Customer")
        account = create_account_for_user(user, team=self.team, name="Customer General", finance_domain=FinanceDomain.GENERAL, primary_person=person)
        self.assertEqual(account.finance_domain, FinanceDomain.GENERAL); self.assertEqual(account.primary_person, person)

    def test_iea_treasurer_can_create_iea_account(self):
        user = self._user("account-iea", OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        account = create_account_for_user(user, team=self.team, name="IEA Family", finance_domain=FinanceDomain.IEA)
        self.assertEqual(account.finance_domain, FinanceDomain.IEA)

    def test_iea_treasurer_cannot_forge_general_account(self):
        user = self._user("account-forge", OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        with self.assertRaises(PermissionDenied): create_account_for_user(user, team=self.team, name="Forbidden General", finance_domain=FinanceDomain.GENERAL)

    def test_admin_can_create_general_charge(self):
        user = self._user("admin", role=UserProfile.Role.ADMIN)
        charge = create_charge_for_user(user, self.general.pk, description="September board", amount="600.00", charge_date=date(2026, 9, 1), team=self.team)
        self.assertEqual(charge.account, self.general); self.assertEqual(self.general.amount_due, charge.amount)

    def test_iea_treasurer_cannot_create_general_charge(self):
        user = self._user("iea", OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        with self.assertRaises(PermissionDenied): create_charge_for_user(user, self.general.pk, description="Board", amount="100.00", charge_date=date(2026, 9, 1), team=self.team)

    def test_iea_treasurer_can_create_iea_charge(self):
        user = self._user("iea-ok", OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        charge = create_charge_for_user(user, self.iea.pk, description="Show fee", amount="75.00", charge_date=date(2026, 9, 1), team=self.team); self.assertEqual(charge.account, self.iea)

    def test_general_treasurer_can_post_payment_to_either_domain(self):
        user = self._user("general", OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE)
        general_payment = post_payment_for_user(user, self.general.pk, amount="100.00", received_date=date(2026, 9, 2), team=self.team)
        iea_payment = post_payment_for_user(user, self.iea.pk, amount="50.00", received_date=date(2026, 9, 2), team=self.team)
        self.assertEqual(general_payment.account, self.general); self.assertEqual(iea_payment.account, self.iea)

    def test_payment_can_be_posted_and_partially_allocated(self):
        user = self._user("split", role=UserProfile.Role.ADMIN); charge = create_charge_for_user(user, self.general.pk, description="Board", amount="200.00", charge_date=date(2026, 9, 1), team=self.team)
        payment = post_payment_for_user(user, self.general.pk, amount="150.00", received_date=date(2026, 9, 2), team=self.team)
        allocation = allocate_payment_for_user(user, self.general.pk, payment_id=payment.pk, charge_id=charge.pk, amount="75.00", team=self.team)
        self.assertEqual(allocation.amount, charge.amount - charge.balance); self.assertEqual(payment.unapplied_amount, allocation.amount)

    def test_credit_can_be_posted_and_allocated(self):
        user = self._user("credit", role=UserProfile.Role.ADMIN); charge = create_charge_for_user(user, self.general.pk, description="Lesson", amount="80.00", charge_date=date(2026, 9, 1), team=self.team)
        credit = post_credit_for_user(user, self.general.pk, description="Courtesy credit", amount="25.00", credit_date=date(2026, 9, 2), team=self.team)
        allocation = allocate_credit_for_user(user, self.general.pk, credit_id=credit.pk, charge_id=charge.pk, team=self.team)
        self.assertEqual(allocation.amount, credit.amount); self.assertEqual(credit.unapplied_amount, 0)

    def test_source_from_other_account_cannot_be_allocated(self):
        user = self._user("boundary", role=UserProfile.Role.ADMIN); charge = create_charge_for_user(user, self.general.pk, description="Board", amount="100.00", charge_date=date(2026, 9, 1), team=self.team); payment = post_payment_for_user(user, self.iea.pk, amount="100.00", received_date=date(2026, 9, 2), team=self.team)
        with self.assertRaises(ValidationError): allocate_payment_for_user(user, self.general.pk, payment_id=payment.pk, charge_id=charge.pk, team=self.team)

    def test_charge_from_other_account_cannot_be_targeted(self):
        user = self._user("target-boundary", role=UserProfile.Role.ADMIN); charge = create_charge_for_user(user, self.iea.pk, description="Show fee", amount="100.00", charge_date=date(2026, 9, 1), team=self.team); payment = post_payment_for_user(user, self.general.pk, amount="100.00", received_date=date(2026, 9, 2), team=self.team)
        with self.assertRaises(ValidationError): allocate_payment_for_user(user, self.general.pk, payment_id=payment.pk, charge_id=charge.pk, team=self.team)

    def test_generic_payment_posts_matching_financial_transaction_without_season(self):
        user=self._user("ledger-admin",role=UserProfile.Role.ADMIN)
        deposit=FinancialAccount.objects.create(team=self.team,name="General Checking",finance_domain=FinanceDomain.GENERAL)
        category=FinancialCategory.objects.create(team=self.team,name="Barn Income",kind=FinancialCategory.Kind.INCOME)
        payment=post_payment_for_user(user,self.general.pk,amount="125.00",received_date=date(2026,9,5),deposit_account=deposit,income_category=category,reference="CHK-101",team=self.team)
        self.assertIsNotNone(payment.financial_transaction_id)
        tx=payment.financial_transaction
        self.assertEqual(tx.kind,FinancialTransaction.Kind.INCOME);self.assertEqual(tx.account,deposit);self.assertEqual(tx.category,category);self.assertEqual(tx.amount,payment.amount);self.assertIsNone(tx.season)

    def test_payment_rejects_deposit_account_from_other_finance_domain(self):
        user=self._user("domain-ledger-admin",role=UserProfile.Role.ADMIN)
        iea_deposit=FinancialAccount.objects.create(team=self.team,name="IEA Checking",finance_domain=FinanceDomain.IEA)
        category=FinancialCategory.objects.create(team=self.team,name="Income",kind=FinancialCategory.Kind.INCOME)
        with self.assertRaises(ValidationError):
            post_payment_for_user(user,self.general.pk,amount="50.00",received_date=date(2026,9,5),deposit_account=iea_deposit,income_category=category,team=self.team)

    def test_payment_form_scopes_deposit_accounts_to_receivable_domain(self):
        user=self._user("form-ledger-admin",role=UserProfile.Role.ADMIN)
        general_deposit=FinancialAccount.objects.create(team=self.team,name="General Bank",finance_domain=FinanceDomain.GENERAL)
        iea_deposit=FinancialAccount.objects.create(team=self.team,name="IEA Bank",finance_domain=FinanceDomain.IEA)
        FinancialCategory.objects.create(team=self.team,name="Income",kind=FinancialCategory.Kind.INCOME)
        self.client.force_login(user)
        response=self.client.get(__import__("django.urls",fromlist=["reverse"]).reverse("finance_payment_add",args=[self.general.pk]))
        qs=response.context["form"].fields["deposit_account"].queryset
        self.assertIn(general_deposit,qs);self.assertNotIn(iea_deposit,qs)

    def test_void_payment_voids_linked_financial_transaction(self):
        user=self._user("void-ledger-admin",role=UserProfile.Role.ADMIN)
        deposit=FinancialAccount.objects.create(team=self.team,name="Void Bank",finance_domain=FinanceDomain.GENERAL)
        category=FinancialCategory.objects.create(team=self.team,name="Void Income",kind=FinancialCategory.Kind.INCOME)
        payment=post_payment_for_user(user,self.general.pk,amount="90.00",received_date=date(2026,9,6),deposit_account=deposit,income_category=category,team=self.team)
        tx_id=payment.financial_transaction_id
        void_payment_for_user(user,self.general.pk,payment_id=payment.pk,reason="Duplicate payment",team=self.team)
        payment.refresh_from_db();tx=FinancialTransaction.objects.get(pk=tx_id)
        self.assertEqual(payment.status,payment.Status.VOID);self.assertEqual(tx.status,FinancialTransaction.Status.VOID);self.assertEqual(tx.void_reason,"Duplicate payment");self.assertEqual(tx.voided_by,user)

    def test_allocated_payment_must_be_unallocated_before_void(self):
        user=self._user("void-allocated-admin",role=UserProfile.Role.ADMIN)
        charge=create_charge_for_user(user,self.general.pk,description="Board",amount="50.00",charge_date=date(2026,9,1),team=self.team)
        payment=post_payment_for_user(user,self.general.pk,amount="50.00",received_date=date(2026,9,6),charge_id=charge.pk,team=self.team)
        with self.assertRaises(ValidationError):
            void_payment_for_user(user,self.general.pk,payment_id=payment.pk,reason="Cannot void yet",team=self.team)
        payment.refresh_from_db();self.assertEqual(payment.status,payment.Status.POSTED)

    def test_payment_allocation_can_be_voided_and_reallocated(self):
        user=self._user("reallocate-admin",role=UserProfile.Role.ADMIN)
        first=create_charge_for_user(user,self.general.pk,description="Board",amount="60.00",charge_date=date(2026,9,1),team=self.team)
        second=create_charge_for_user(user,self.general.pk,description="Lessons",amount="60.00",charge_date=date(2026,9,1),team=self.team)
        payment=post_payment_for_user(user,self.general.pk,amount="60.00",received_date=date(2026,9,8),charge_id=first.pk,team=self.team)
        allocation=payment.allocations.get()
        unallocate_payment_for_user(user,self.general.pk,allocation_id=allocation.pk,reason="Wrong charge",team=self.team)
        allocation.refresh_from_db();first.refresh_from_db();payment.refresh_from_db()
        self.assertEqual(allocation.status,allocation.Status.VOID);self.assertEqual(first.balance,first.amount);self.assertEqual(payment.unapplied_amount,payment.amount)
        replacement=allocate_payment_for_user(user,self.general.pk,payment_id=payment.pk,charge_id=second.pk,team=self.team)
        self.assertEqual(replacement.amount,payment.amount);self.assertEqual(second.balance,0)

    def test_removing_account_person_soft_deactivates_relationship(self):
        user=self._user("people-admin",role=UserProfile.Role.ADMIN)
        person=Person.objects.create(team=self.team,first_name="Billing",last_name="Contact")
        link=add_account_person_for_user(user,self.general.pk,person=person,role="billing_contact",statement_recipient=True,team=self.team)
        remove_account_person_for_user(user,self.general.pk,link_id=link.pk,team=self.team)
        link.refresh_from_db();self.assertFalse(link.active);self.assertFalse(link.statement_recipient)
    def test_credit_allocation_can_be_voided_and_reallocated(self):
        user=self._user("credit-reallocate-admin",role=UserProfile.Role.ADMIN)
        first=create_charge_for_user(user,self.general.pk,description="Board",amount="40.00",charge_date=date(2026,9,1),team=self.team)
        second=create_charge_for_user(user,self.general.pk,description="Lessons",amount="40.00",charge_date=date(2026,9,1),team=self.team)
        credit=post_credit_for_user(user,self.general.pk,description="Adjustment",amount="40.00",credit_date=date(2026,9,8),charge_id=first.pk,team=self.team)
        allocation=credit.allocations.get()
        unallocate_credit_for_user(user,self.general.pk,allocation_id=allocation.pk,reason="Wrong charge",team=self.team)
        allocation.refresh_from_db();first.refresh_from_db();credit.refresh_from_db()
        self.assertEqual(allocation.status,allocation.Status.VOID);self.assertEqual(first.balance,first.amount);self.assertEqual(credit.unapplied_amount,credit.amount)
        replacement=allocate_credit_for_user(user,self.general.pk,credit_id=credit.pk,charge_id=second.pk,team=self.team)
        self.assertEqual(replacement.amount,credit.amount);self.assertEqual(second.balance,0)
