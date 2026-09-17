# ArenaLine v3.5 Preview 1C — Finance Reconciliation Foundation

Preview 1C separates customer amount due from net account position and establishes the service boundary for future finance workflows.

## Ledger semantics

- `amount_due`: sum of outstanding posted charge balances, floored per charge at zero.
- `unapplied_payment_total`: posted payment money not yet allocated to charges.
- `unapplied_credit_total`: posted credits not yet allocated to charges.
- `balance`: net account position (`amount_due - unapplied payments - unapplied credits`). A negative value represents customer credit.
- General and IEA ledgers remain separate finance domains.

## Compatibility

Legacy IEA receivables remain linked through compatibility fields. `reconcile_legacy_account()` compares the legacy family-charge amount due with the migrated receivable amount due. Migration 0093 repairs any Preview 1B legacy over-allocation by capping allocations at the charge amount while retaining excess source value as unapplied money/credit.

## Service boundary

`portal.services.finance_receivables` is the supported application boundary for posting and allocating receivables. Allocations are capped at the lesser of charge balance and source balance. Excess payments or credits remain unapplied for later allocation.

This boundary is intentionally reusable by later statement, CSV/XLSX import/export, QuickBooks exchange, and bank-reconciliation workflows.

## Preview 1C staging checks

```bash
./portalctl upgrade
./portalctl exec web python manage.py showmigrations portal | tail -15
./portalctl exec web python manage.py makemigrations --check
./portalctl exec web python manage.py test \
  portal.tests.test_v350_finance_foundation \
  portal.tests.test_v350_finance_domains \
  portal.tests.test_v350_finance_reconciliation \
  portal.tests.test_finance_hardening
```

Expected migrations include `0092_v350_receivable_account_semantics` and `0093_v350_repair_legacy_receivable_allocations`.
