from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from portal.model_modules.capabilities import OrganizationCapabilityAssignment
from portal.model_modules.finance import AccountingExportProfile, FinanceDomain
from portal.model_modules.people import Person
from portal.models import FinancialAccount, FinancialCategory, FinancialTransaction, Team
from portal.services.finance_exports import QUICKBOOKS_MAPPING, normalized_export_rows, render_accounting_export


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

class AccountingExportServiceTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Export Service Barn")
        self.user=get_user_model().objects.create_user(username="exportadmin",password="pass")
        profile=self.user.profile;profile.team=self.team;profile.role=profile.Role.ADMIN;profile.save(update_fields=["team","role"])
        self.general=FinancialAccount.objects.create(team=self.team,name="Operating",finance_domain=FinanceDomain.GENERAL)
        self.iea=FinancialAccount.objects.create(team=self.team,name="IEA Checking",finance_domain=FinanceDomain.IEA)
        self.category=FinancialCategory.objects.create(team=self.team,name="Income",kind=FinancialCategory.Kind.INCOME)
        FinancialTransaction.objects.create(team=self.team,transaction_date=date(2026,9,1),kind=FinancialTransaction.Kind.INCOME,account=self.general,category=self.category,amount=Decimal("100.00"),description="Board")
        FinancialTransaction.objects.create(team=self.team,transaction_date=date(2026,9,2),kind=FinancialTransaction.Kind.INCOME,account=self.iea,category=self.category,amount=Decimal("50.00"),description="Show fee")
        self.export=AccountingExportProfile.objects.create(team=self.team,name="QuickBooks",finance_domain=FinanceDomain.GENERAL,column_mapping=QUICKBOOKS_MAPPING)
    def test_export_is_domain_scoped(self):
        rows=normalized_export_rows(self.user,self.export)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]["Memo"],"Board");self.assertEqual(rows[0]["Amount"],"100.00")
    def test_export_uses_accounting_friendly_type_and_excludes_void_transactions(self):
        posted=normalized_export_rows(self.user,self.export)
        self.assertEqual(posted[0]["Transaction Type"],"Deposit")
        tx=FinancialTransaction.objects.filter(account=self.general).first();tx.status="void";tx.save(update_fields=["status"])
        self.assertEqual(normalized_export_rows(self.user,self.export),[])
    def test_unsupported_file_type_is_rejected(self):
        self.export.file_type="pdf"
        with self.assertRaises(ValidationError):render_accounting_export(self.user,self.export)
    def test_csv_renderer_has_quickbooks_friendly_headers(self):
        data,mime=render_accounting_export(self.user,self.export)
        text=data.decode("utf-8-sig");self.assertEqual(mime,"text/csv");self.assertIn("Date,Transaction Type,Account,Category,Amount,Name,Memo,Reference",text);self.assertIn("Board",text);self.assertNotIn("Show fee",text)
    def test_xlsx_renderer_produces_workbook(self):
        self.export.file_type=AccountingExportProfile.FileType.XLSX;self.export.save(update_fields=["file_type"])
        data,mime=render_accounting_export(self.user,self.export)
        self.assertTrue(data.startswith(b"PK"));self.assertIn("spreadsheetml",mime)
    def test_iea_only_user_cannot_export_general_domain(self):
        user=get_user_model().objects.create_user(username="ieaexport",password="pass")
        p=user.profile;p.team=self.team;p.save(update_fields=["team"])
        person=Person.objects.create(team=self.team,user=user,first_name="IEA",last_name="Treasurer")
        OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):normalized_export_rows(user,self.export)


class AccountingExportUITests(AccountingExportServiceTests):
    def test_export_routes_resolve(self):
        from django.urls import reverse
        self.assertEqual(reverse("finance_accounting_exports"),"/finance/workspace/exports/")
        self.assertEqual(reverse("finance_accounting_export_detail",args=[self.export.pk]),f"/finance/workspace/exports/{self.export.pk}/")
        self.assertEqual(reverse("finance_accounting_export_download",args=[self.export.pk]),f"/finance/workspace/exports/{self.export.pk}/download/")
    def test_admin_can_preview_and_download_export(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        preview=self.client.get(reverse("finance_accounting_export_detail",args=[self.export.pk]))
        self.assertEqual(preview.status_code,200);self.assertContains(preview,"Board");self.assertNotContains(preview,"Show fee")
        download=self.client.get(reverse("finance_accounting_export_download",args=[self.export.pk]))
        self.assertEqual(download.status_code,200);self.assertIn("attachment;",download["Content-Disposition"])
    def test_download_filename_includes_profile_and_date_range(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        response=self.client.get(reverse("finance_accounting_export_download",args=[self.export.pk]),{"start_date":"2026-09-01","end_date":"2026-09-30"})
        self.assertEqual(response.status_code,200)
        self.assertIn('arenaline-general-quickbooks-2026-09-01-2026-09-30.csv',response["Content-Disposition"])
    def test_invalid_date_range_is_not_downloaded(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        response=self.client.get(reverse("finance_accounting_export_download",args=[self.export.pk]),{"start_date":"2026-10-01","end_date":"2026-09-01"})
        self.assertEqual(response.status_code,403)
    def test_iea_only_user_cannot_open_general_export_url(self):
        from django.urls import reverse
        user=get_user_model().objects.create_user(username="ieaexportui",password="pass")
        p=user.profile;p.team=self.team;p.save(update_fields=["team"])
        person=Person.objects.create(team=self.team,user=user,first_name="IEA UI",last_name="Treasurer")
        OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("finance_accounting_export_detail",args=[self.export.pk])).status_code,403)
        self.assertEqual(self.client.get(reverse("finance_accounting_export_download",args=[self.export.pk])).status_code,403)

    def test_admin_can_edit_export_profile_with_custom_mapping(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        response=self.client.post(reverse("finance_accounting_export_edit",args=[self.export.pk]),{
            "name":"Bookkeeper Export","finance_domain":FinanceDomain.GENERAL,"file_type":"csv","active":"on",
            "preset":"custom","column_mapping":'{"Txn Date":"transaction_date","Memo":"description","Total":"signed_amount"}',
        })
        self.assertEqual(response.status_code,302)
        self.export.refresh_from_db();self.assertEqual(self.export.name,"Bookkeeper Export");self.assertEqual(self.export.column_mapping["Txn Date"],"transaction_date")
    def test_quickbooks_profile_edit_defaults_to_quickbooks_preset(self):
        from portal.forms_v350_finance import AccountingExportProfileForm
        form=AccountingExportProfileForm(instance=self.export,allowed_domains={FinanceDomain.GENERAL})
        self.assertEqual(form.fields["preset"].initial,AccountingExportProfileForm.PRESET_QUICKBOOKS)

    def test_custom_profile_edit_defaults_to_custom_preset(self):
        from portal.forms_v350_finance import AccountingExportProfileForm
        self.export.column_mapping={"Txn Date":"transaction_date","Memo":"description"};self.export.save(update_fields=["column_mapping"])
        form=AccountingExportProfileForm(instance=self.export,allowed_domains={FinanceDomain.GENERAL})
        self.assertEqual(form.fields["preset"].initial,AccountingExportProfileForm.PRESET_CUSTOM)

    def test_custom_mapping_rejects_unknown_fields(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        response=self.client.post(reverse("finance_accounting_export_edit",args=[self.export.pk]),{
            "name":"Bad","finance_domain":FinanceDomain.GENERAL,"file_type":"csv","active":"on",
            "preset":"custom","column_mapping":'{"Mystery":"not_a_field"}',
        })
        self.assertEqual(response.status_code,200);self.assertContains(response,"Unknown export field")
        self.export.refresh_from_db();self.assertEqual(self.export.name,"QuickBooks")
    def test_iea_only_user_cannot_edit_general_export_url(self):
        from django.urls import reverse
        user=get_user_model().objects.create_user(username="ieaexportedit",password="pass")
        p=user.profile;p.team=self.team;p.save(update_fields=["team"])
        person=Person.objects.create(team=self.team,user=user,first_name="IEA Edit",last_name="Treasurer")
        OrganizationCapabilityAssignment.objects.create(team=self.team,person=person,capability=OrganizationCapabilityAssignment.Capability.MANAGE_IEA_FINANCE)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("finance_accounting_export_edit",args=[self.export.pk])).status_code,403)
