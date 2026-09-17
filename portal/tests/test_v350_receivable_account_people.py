from django.core.exceptions import ValidationError
from django.test import TestCase
from portal.model_modules.finance import FinanceDomain, ReceivableAccount, ReceivableAccountPerson
from portal.model_modules.people import Person
from portal.models import Team


class ReceivableAccountPeopleTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="Household Barn")
        self.other_team = Team.objects.create(name="Other Barn")
        self.parent = Person.objects.create(team=self.team, first_name="Pat", last_name="Parent")
        self.rider_one = Person.objects.create(team=self.team, first_name="Riley", last_name="Rider")
        self.rider_two = Person.objects.create(team=self.team, first_name="Robin", last_name="Rider")
        self.account = ReceivableAccount.objects.create(team=self.team, name="Rider Family General", finance_domain=FinanceDomain.GENERAL, primary_person=self.parent)

    def test_family_account_can_link_multiple_people_with_roles(self):
        responsible = ReceivableAccountPerson(account=self.account, person=self.parent, role=ReceivableAccountPerson.Role.RESPONSIBLE_PARTY, statement_recipient=True)
        responsible.full_clean(); responsible.save()
        for rider in (self.rider_one, self.rider_two):
            link = ReceivableAccountPerson(account=self.account, person=rider, role=ReceivableAccountPerson.Role.PARTICIPANT)
            link.full_clean(); link.save()
        self.assertEqual(self.account.people_links.count(), 3)
        self.assertEqual(self.account.people_links.filter(role=ReceivableAccountPerson.Role.PARTICIPANT).count(), 2)

    def test_same_family_can_have_separate_general_and_iea_accounts(self):
        iea = ReceivableAccount.objects.create(team=self.team, name="Rider Family IEA", finance_domain=FinanceDomain.IEA, primary_person=self.parent)
        for account in (self.account, iea):
            link = ReceivableAccountPerson(account=account, person=self.parent, role=ReceivableAccountPerson.Role.RESPONSIBLE_PARTY)
            link.full_clean(); link.save()
        self.assertEqual(self.parent.receivable_account_links.count(), 2)
        self.assertSetEqual(set(self.parent.receivable_account_links.values_list("account__finance_domain", flat=True)), {FinanceDomain.GENERAL, FinanceDomain.IEA})

    def test_person_from_another_organization_cannot_be_linked(self):
        outsider = Person.objects.create(team=self.other_team, first_name="Other", last_name="Person")
        link = ReceivableAccountPerson(account=self.account, person=outsider, role=ReceivableAccountPerson.Role.PARTICIPANT)
        with self.assertRaises(ValidationError): link.full_clean()
