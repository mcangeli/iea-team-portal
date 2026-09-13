# ArenaLine v3.0.0 — Phase C Legacy Class Reconciliation

## Purpose

Phase C connects existing `SeasonClass` rows to verified `IEAClassCatalogEntry` records without rewriting historical class data or guessing from free-form names.

All validation and reconciliation must occur on ArenaLine staging first.

## Matching rule

A legacy class is eligible for automatic linkage only when all of the following are true:

- `catalog_entry` is currently null;
- discipline is Hunt Seat, Western, or Dressage;
- `class_code` is present;
- an active, season-assignable catalog row exists for the explicitly selected rulebook season;
- discipline matches exactly;
- class code matches case-insensitively;
- team level matches the catalog entry (or the catalog entry explicitly supports both teams).

Display names are intentionally not used for automatic matching.

## Safety behavior

- Existing catalog links are preserved.
- Missing class codes are reported and skipped.
- Unsupported disciplines are reported and skipped.
- Team-level mismatches are reported and not linked.
- Unknown codes are reported and not linked.
- Ambiguous matches are reported and not linked.
- Legacy `SeasonClass` name, code, discipline, sort order, activity state, primary key, assignments, shows, results, and scoring relationships are not rewritten.
- Dry-run is the default. Persistence requires `--apply` explicitly.

## Staging validation

Update the staging checkout and run:

```bash
cd /opt/arenaline-staging/app
git fetch origin
git checkout feature/v3.0.0-iea-class-catalog
git pull --ff-only origin feature/v3.0.0-iea-class-catalog
./portalctl preflight
./portalctl upgrade
./portalctl health
```

Focused tests:

```bash
./portalctl exec web python manage.py test \
  portal.tests.test_v300_iea_class_catalog \
  portal.tests.test_v300_seasonclass_catalog_link \
  portal.tests.test_v300_iea_class_reconciliation
```

Full regression suite:

```bash
./portalctl exec web python manage.py test portal
```

## Reconciliation dry run

First identify the staging ArenaLine season id that should use the 2026–2027 IEA rulebook. Then run:

```bash
./portalctl exec web python manage.py reconcile_iea_class_catalog \
  --rulebook-season 2026-2027 \
  --season-id <SEASON_ID>
```

Review every reported row. Expected statuses include:

- `match` — deterministic candidate; would be linked by `--apply`;
- `already_linked` — existing link left unchanged;
- `skipped (missing_class_code)`;
- `skipped (unsupported_discipline)`;
- `unmatched (no_catalog_match)`;
- `unmatched (team_level_mismatch)`;
- `ambiguous` — never linked automatically.

Do not use `--apply` until the dry-run report has been reviewed.

## Apply on staging only

If the dry-run matches are correct:

```bash
./portalctl exec web python manage.py reconcile_iea_class_catalog \
  --rulebook-season 2026-2027 \
  --season-id <SEASON_ID> \
  --apply
```

Then immediately repeat the command without `--apply`. Successfully reconciled rows should now report `already_linked` rather than `match`.

Finally rerun the focused tests, full portal suite, and `./portalctl health`.

## Production boundary

Phase C remains staging-only during v3.0 development. No reconciliation command should be run against the v2.9.0 production installation until the v3.0 release process explicitly authorizes production migration and reconciliation.
