from datetime import date
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableAccountPerson, ReceivableCharge, ReceivablePayment
from portal.model_modules.people import Person
from portal.models import Team, UserProfile
class FinanceWorkspaceTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Workspace Barn");self.general=ReceivableAccount.objects.create(team=self.team,name="General Account",finance_domain=FinanceDomain.GENERAL);self.iea=ReceivableAccount.objects.create(team=self.team,name="IEA Account",finance_domain=FinanceDomain.IEA);self.general_charge=ReceivableCharge.objects.create(account=self.general,description="Board",amount="125.00",charge_date=date(2026,9,1));self.iea_charge=ReceivableCharge.objects.create(account=self.iea,description="Show fee",amount="75.00",charge_date=date(2026,9,2))
    def _user(self,username,role=UserProfile.Role.PARENT):
        user=User.objects.create_user(username=username,password="pass12345");profile=user.profile;profile.team=self.team;profile.role=role;profile.save(update_fields=["team","role"]);person=Person.objects.create(team=self.team,user=user,first_name=username,last_name="Tester");return user,person
    def _grant(self,person,capability):OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=capability)
    def test_admin_workspace_contains_both_domains(self):
        user,_=self._user("admin",UserProfile.Role.ADMIN);self.client.force_login(user);r=self.client.get(reverse("finance_workspace"));self.assertEqual(r.status_code,200);self.assertContains(r,"General Barn");self.assertContains(r,"IEA");self.assertContains(r,"General Account");self.assertContains(r,"IEA Account")
    def test_iea_treasurer_workspace_does_not_render_general_data(self):
        user,p=self._user("iea-treasurer");self._grant(p,OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE);self.client.force_login(user);r=self.client.get(reverse("finance_workspace"));self.assertEqual(r.status_code,200);self.assertNotContains(r,"General Account");self.assertContains(r,"IEA Account")
    def test_iea_treasurer_cannot_guess_general_account_detail_url(self):
        user,p=self._user("iea-detail");self._grant(p,OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE);self.client.force_login(user);self.assertEqual(self.client.get(reverse("finance_receivable_account_detail",args=[self.general.pk])).status_code,403)
    def test_iea_treasurer_cannot_guess_general_statement_url(self):
        user,p=self._user("iea-statement");self._grant(p,OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE);self.client.force_login(user);self.assertEqual(self.client.get(reverse("finance_receivable_statement",args=[self.general.pk])).status_code,403)
    def test_unprivileged_user_cannot_open_workspace(self):
        user,_=self._user("parent");self.client.force_login(user);self.assertEqual(self.client.get(reverse("finance_workspace")).status_code,403)
    def test_general_treasurer_can_open_both_account_details(self):
        user,p=self._user("general-treasurer");self._grant(p,OrganizationCapabilityAssignment.Capability.MANAGE_ALL_FINANCE);self.client.force_login(user)
        for a in (self.general,self.iea):self.assertEqual(self.client.get(reverse("finance_receivable_account_detail",args=[a.pk])).status_code,200)
    def test_statement_accepts_date_range(self):
        user,_=self._user("statement-admin",UserProfile.Role.ADMIN);self.client.force_login(user);r=self.client.get(reverse("finance_receivable_statement",args=[self.general.pk]),{"start":"2026-09-01","end":"2026-09-30"});self.assertEqual(r.status_code,200);self.assertContains(r,"Sep 1, 2026");self.assertContains(r,"Sep 30, 2026");self.assertContains(r,"Board")
    def test_admin_account_form_offers_both_domains(self):
        user,_=self._user("account-form-admin",UserProfile.Role.ADMIN);self.client.force_login(user);r=self.client.get(reverse("finance_receivable_account_add"));self.assertContains(r,'value="general"');self.assertContains(r,'value="iea"')
    def test_iea_account_form_does_not_offer_general_domain(self):
        user,p=self._user("account-form-iea");self._grant(p,OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE);self.client.force_login(user);r=self.client.get(reverse("finance_receivable_account_add"));self.assertNotContains(r,'value="general"');self.assertContains(r,'value="iea"')
    def test_iea_treasurer_cannot_forge_general_account_post(self):
        user,p=self._user("account-post-iea");self._grant(p,OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE);self.client.force_login(user);r=self.client.post(reverse("finance_receivable_account_add"),{"name":"Forged General","finance_domain":"general","primary_person":"","notes":""});self.assertEqual(r.status_code,200);self.assertFalse(ReceivableAccount.objects.filter(team=self.team,name="Forged General").exists())
    def test_admin_can_post_charge_through_ui(self):
        user,_=self._user("post-admin",UserProfile.Role.ADMIN);self.client.force_login(user);r=self.client.post(reverse("finance_charge_add",args=[self.general.pk]),{"description":"October board","amount":"225.00","charge_date":"2026-10-01","due_date":"","charge_type":"board","notes":""});self.assertEqual(r.status_code,302);self.assertTrue(self.general.charges.filter(description="October board",amount="225.00").exists())
    def test_iea_treasurer_cannot_post_general_charge_by_url(self):
        user,p=self._user("post-iea");self._grant(p,OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE);self.client.force_login(user);r=self.client.post(reverse("finance_charge_add",args=[self.general.pk]),{"description":"Forbidden","amount":"50.00","charge_date":"2026-10-01"});self.assertEqual(r.status_code,403);self.assertFalse(self.general.charges.filter(description="Forbidden").exists())
    def test_unprivileged_user_cannot_post_payment(self):
        user,_=self._user("post-parent");self.client.force_login(user);r=self.client.post(reverse("finance_payment_add",args=[self.general.pk]),{"amount":"50.00","received_date":"2026-10-01","method":"check","reference":"","notes":""});self.assertEqual(r.status_code,403);self.assertFalse(self.general.payments.exists())
    def test_payment_allocation_cannot_target_charge_on_other_account(self):
        user,_=self._user("allocate-admin",UserProfile.Role.ADMIN);payment=ReceivablePayment.objects.create(account=self.general,amount="60.00",received_date=date(2026,9,10));self.client.force_login(user);r=self.client.post(reverse("finance_payment_allocate",args=[self.general.pk,payment.pk]),{"charge_id":self.iea_charge.pk,"amount":"25.00","notes":""});self.assertEqual(r.status_code,200);self.assertFalse(payment.allocations.exists())
    def test_payment_id_from_other_account_cannot_be_allocated(self):
        user,_=self._user("source-admin",UserProfile.Role.ADMIN);payment=ReceivablePayment.objects.create(account=self.iea,amount="60.00",received_date=date(2026,9,10));self.client.force_login(user);r=self.client.post(reverse("finance_payment_allocate",args=[self.general.pk,payment.pk]),{"charge_id":self.general_charge.pk,"amount":"25.00","notes":""});self.assertEqual(r.status_code,200);self.assertFalse(payment.allocations.exists())
    def test_admin_can_add_account_person_through_ui(self):
        user,_=self._user("people-admin",UserProfile.Role.ADMIN);person=Person.objects.create(team=self.team,first_name="Family",last_name="Contact");self.client.force_login(user);r=self.client.post(reverse("finance_account_person_add",args=[self.general.pk]),{"person":person.pk,"role":"billing_contact","statement_recipient":"on","notes":""});self.assertEqual(r.status_code,302);self.assertTrue(ReceivableAccountPerson.objects.filter(account=self.general,person=person,role="billing_contact",statement_recipient=True).exists())
    def test_iea_treasurer_cannot_add_person_to_general_account(self):
        user,p=self._user("people-iea");self._grant(p,OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE);person=Person.objects.create(team=self.team,first_name="General",last_name="Contact");self.client.force_login(user);r=self.client.post(reverse("finance_account_person_add",args=[self.general.pk]),{"person":person.pk,"role":"billing_contact"});self.assertEqual(r.status_code,403);self.assertFalse(self.general.people_links.filter(person=person).exists())
    def test_account_detail_only_lists_charges_with_balance(self):
        user,_=self._user("open-charge-admin",UserProfile.Role.ADMIN);paid=ReceivableCharge.objects.create(account=self.general,description="Paid item",amount="10.00",charge_date=date(2026,9,3));payment=ReceivablePayment.objects.create(account=self.general,amount="10.00",received_date=date(2026,9,4));from portal.model_modules.finance import ReceivableAllocation;ReceivableAllocation.objects.create(charge=paid,payment=payment,amount="10.00");self.client.force_login(user);r=self.client.get(reverse("finance_receivable_account_detail",args=[self.general.pk]));self.assertContains(r,"Board");self.assertNotIn(paid,r.context["open_charges"]);self.assertContains(r,"Paid item")
    def test_payment_charge_query_preselects_same_account_charge(self):
        user,_=self._user("preselect-admin",UserProfile.Role.ADMIN);self.client.force_login(user);r=self.client.get(reverse("finance_payment_add",args=[self.general.pk]),{"charge":self.general_charge.pk});self.assertEqual(r.status_code,200);self.assertEqual(r.context["form"].initial.get("charge_id"),self.general_charge.pk)
    def test_payment_charge_query_does_not_preselect_other_account_charge(self):
        user,_=self._user("preselect-other-admin",UserProfile.Role.ADMIN);self.client.force_login(user);r=self.client.get(reverse("finance_payment_add",args=[self.general.pk]),{"charge":self.iea_charge.pk});self.assertEqual(r.status_code,200);self.assertIsNone(r.context["form"].initial.get("charge_id"))

    def test_admin_can_void_unallocated_payment_through_ui(self):
        user,_=self._user("void-ui-admin",UserProfile.Role.ADMIN)
        payment=ReceivablePayment.objects.create(account=self.general,amount="25.00",received_date=date(2026,9,7))
        self.client.force_login(user)
        response=self.client.post(reverse("finance_payment_void",args=[self.general.pk,payment.pk]),{"reason":"Duplicate"})
        self.assertRedirects(response,reverse("finance_receivable_account_detail",args=[self.general.pk]))
        payment.refresh_from_db();self.assertEqual(payment.status,payment.Status.VOID)

    def test_iea_treasurer_cannot_void_general_payment_by_url(self):
        user,_=self._user("void-ui-iea",UserProfile.Role.PARENT,OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        payment=ReceivablePayment.objects.create(account=self.general,amount="25.00",received_date=date(2026,9,7))
        self.client.force_login(user)
        response=self.client.post(reverse("finance_payment_void",args=[self.general.pk,payment.pk]),{"reason":"Forbidden"})
        self.assertEqual(response.status_code,403)
        payment.refresh_from_db();self.assertEqual(payment.status,payment.Status.POSTED)
