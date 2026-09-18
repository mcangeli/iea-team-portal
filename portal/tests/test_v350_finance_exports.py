from django.core.exceptions import ValidationError
from django.test import TestCase
from portal.model_modules.finance import AccountingExportProfile, FinanceDomain
from portal.models import Team

class AccountingExportProfileTests(TestCase):
    def setUp(self):self.team=Team.objects.create(name="Export Barn")
    def test_profile_is_scoped_by_finance_domain(self):
        general=AccountingExportProfile.objects.create(team=self.team,name="QuickBooks",finance_domain=FinanceDomain.GENERAL,column_mapping={"Date":"transaction_date"})
        iea=AccountingExportProfile.objects.create(team=self.team,name="QuickBooks",finance_domain=FinanceDomain.IEA,column_mapping={"Date":"transaction_date"})
        self.assertNotEqual(general.pk,iea.pk)
    def test_profile_requires_mapping(self):
        profile=AccountingExportProfile(team=self.team,name="Empty",finance_domain=FinanceDomain.GENERAL,column_mapping={})
        with self.assertRaises(ValidationError):profile.full_clean()
    def test_profile_supports_csv_and_xlsx(self):
        self.assertEqual(set(AccountingExportProfile.FileType.values),{"csv","xlsx"})
