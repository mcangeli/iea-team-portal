import io
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from openpyxl import Workbook
from portal.model_modules.finance import FinanceDomain, ImportedBankTransaction
from portal.models import FinancialAccount, FinancialTransaction, Team
from portal.services.finance_imports import stage_bank_import

class BankImportServiceTests(TestCase):
    def setUp(self):
        self.team=Team.objects.create(name="Import Barn");self.account=FinancialAccount.objects.create(team=self.team,name="General Checking",finance_domain=FinanceDomain.GENERAL)
        self.mapping={"date":"Date","description":"Description","amount":"Amount","reference":"Reference"}

    def test_csv_import_normalizes_signed_amounts_without_posting_ledger(self):
        data=b"Date,Description,Amount,Reference\n09/01/2026,Client payment,125.50,DEP-1\n09/02/2026,Feed store,-42.75,CARD-1\n"
        batch=stage_bank_import(team=self.team,financial_account=self.account,source_name="bank.csv",data=data,file_type="csv",column_mapping=self.mapping)
        rows=list(batch.transactions.order_by("transaction_date"))
        self.assertEqual(len(rows),2);self.assertEqual(rows[0].direction,ImportedBankTransaction.Direction.CREDIT);self.assertEqual(rows[0].amount,Decimal("125.50"));self.assertEqual(rows[1].direction,ImportedBankTransaction.Direction.DEBIT);self.assertEqual(rows[1].amount,Decimal("42.75"));self.assertEqual(FinancialTransaction.objects.count(),0)

    def test_duplicate_file_is_rejected(self):
        data=b"Date,Description,Amount\n09/01/2026,Deposit,10.00\n";mapping={"date":"Date","description":"Description","amount":"Amount"}
        stage_bank_import(team=self.team,financial_account=self.account,source_name="one.csv",data=data,file_type="csv",column_mapping=mapping)
        with self.assertRaises(ValidationError):stage_bank_import(team=self.team,financial_account=self.account,source_name="two.csv",data=data,file_type="csv",column_mapping=mapping)

    def test_duplicate_rows_inside_one_file_are_staged_once(self):
        data=b"Date,Description,Amount\n09/01/2026,Deposit,10.00\n09/01/2026,Deposit,10.00\n";mapping={"date":"Date","description":"Description","amount":"Amount"}
        batch=stage_bank_import(team=self.team,financial_account=self.account,source_name="dupes.csv",data=data,file_type="csv",column_mapping=mapping)
        self.assertEqual(batch.transactions.count(),1)

    def test_xlsx_uses_same_normalized_pipeline(self):
        wb=Workbook();ws=wb.active;ws.append(["Date","Description","Amount","Reference"]);ws.append(["2026-09-03","Lesson deposit",75,"X-1"]);stream=io.BytesIO();wb.save(stream)
        batch=stage_bank_import(team=self.team,financial_account=self.account,source_name="bank.xlsx",data=stream.getvalue(),file_type="xlsx",column_mapping=self.mapping)
        row=batch.transactions.get();self.assertEqual(row.amount,Decimal("75"));self.assertEqual(row.reference,"X-1");self.assertEqual(row.direction,ImportedBankTransaction.Direction.CREDIT)
