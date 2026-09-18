"""Normalized outbound accounting exports for ArenaLine v3.5."""
import csv
from io import BytesIO, StringIO
from openpyxl import Workbook
from django.core.exceptions import PermissionDenied, ValidationError
from portal.services.finance_access import allowed_finance_domains, financial_transactions_for_user

EXPORT_FIELDS={
    "transaction_date": lambda tx: tx.transaction_date.isoformat(),
    "kind": lambda tx: "Deposit" if tx.kind == tx.Kind.INCOME else "Expense",
    "account": lambda tx: tx.account.name,
    "category": lambda tx: tx.category.name,
    "amount": lambda tx: f"{tx.amount:.2f}",
    "signed_amount": lambda tx: f"{tx.amount if tx.kind == tx.Kind.INCOME else -tx.amount:.2f}",
    "payee": lambda tx: tx.payee or "",
    "description": lambda tx: tx.description or "",
    "reference": lambda tx: tx.reference or "",
    "status": lambda tx: tx.status,
}
QUICKBOOKS_MAPPING={"Date":"transaction_date","Transaction Type":"kind","Account":"account","Category":"category","Amount":"signed_amount","Name":"payee","Memo":"description","Reference":"reference"}

def validate_export_mapping(mapping):
    if not isinstance(mapping,dict) or not mapping:
        raise ValidationError("Choose at least one export column.")
    if any(not str(column).strip() for column in mapping):
        raise ValidationError("Export column names cannot be blank.")
    unknown=set(mapping.values())-set(EXPORT_FIELDS)
    if unknown:
        raise ValidationError("Unknown export field(s): "+", ".join(sorted(unknown)))
    return mapping

def export_transactions_for_profile(user,profile,*,start_date=None,end_date=None):
    if profile.finance_domain not in allowed_finance_domains(user,profile.team):
        raise PermissionDenied
    qs=financial_transactions_for_user(user,profile.team,profile.finance_domain).filter(status="posted").select_related("account","category").order_by("transaction_date","id")
    if start_date:qs=qs.filter(transaction_date__gte=start_date)
    if end_date:qs=qs.filter(transaction_date__lte=end_date)
    return qs

def normalized_export_rows(user,profile,*,start_date=None,end_date=None):
    mapping=validate_export_mapping(profile.column_mapping or {})
    rows=[]
    for tx in export_transactions_for_profile(user,profile,start_date=start_date,end_date=end_date):
        rows.append({column:EXPORT_FIELDS[field](tx) for column,field in mapping.items()})
    return rows

def render_accounting_export(user,profile,*,start_date=None,end_date=None):
    rows=normalized_export_rows(user,profile,start_date=start_date,end_date=end_date)
    headers=list(profile.column_mapping)
    if profile.file_type==profile.FileType.CSV:
        out=StringIO(newline="");writer=csv.DictWriter(out,fieldnames=headers);writer.writeheader();writer.writerows(rows)
        return out.getvalue().encode("utf-8-sig"),"text/csv"
    if profile.file_type!=profile.FileType.XLSX:
        raise ValidationError("Unsupported accounting export file type.")
    wb=Workbook();ws=wb.active;ws.title="ArenaLine Export";ws.append(headers)
    for row in rows:ws.append([row[h] for h in headers])
    out=BytesIO();wb.save(out)
    return out.getvalue(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
