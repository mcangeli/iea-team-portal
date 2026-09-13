# ArenaLine v3.0.0 — Phase A Staging Validation

This checklist validates the additive IEA class-catalog foundation on the isolated ArenaLine staging installation only.

## Branch

`feature/v3.0.0-iea-class-catalog`

## Scope in this slice

- Add `IEAClassCatalogEntry` in `portal/model_modules/competition_iea.py`.
- Register the model through `PortalConfig.import_models()`.
- Add migration `0048_v300_iea_class_catalog`.
- Seed the verified 2026–2027 Hunt Seat, Western, and Dressage placement catalog in `0049_v300_seed_iea_class_catalog`.
- Add focused v3.0 regression coverage.
- Do not alter `SeasonClass`, rider assignments, show classes, scoring, qualification, or production data.

## Staging deployment

From `/opt/arenaline-staging/app`:

```bash
git fetch origin
git checkout feature/v3.0.0-iea-class-catalog
git pull --ff-only origin feature/v3.0.0-iea-class-catalog
./portalctl preflight
./portalctl upgrade
./portalctl health
./portalctl git-status
```

## Migration verification

```bash
./portalctl exec web python manage.py showmigrations portal
./portalctl exec web python manage.py makemigrations --check --dry-run
```

Expected:

- `0048_v300_iea_class_catalog` applied.
- `0049_v300_seed_iea_class_catalog` applied.
- `makemigrations --check --dry-run` reports no model drift.

## Focused v3.0 test

```bash
./portalctl exec web python manage.py test portal.tests.test_v300_iea_class_catalog
```

Expected catalog assertions:

- 42 active, season-assignable 2026–2027 entries.
- 14 Hunt Seat, 14 Western, 14 Dressage.
- H8/H14, W8/W14, and D8/D14 retain individual-points eligibility but disable team points in reference data.
- A class code may coexist across different rulebook seasons.
- Duplicate class code within the same rulebook season + discipline is rejected.
- Existing Hunt Seat H8/H14 scoring exclusion behavior remains unchanged in this slice.

## Catalog data spot check

```bash
./portalctl exec web python manage.py shell -c '
from portal.model_modules.competition_iea import IEAClassCatalogEntry as E
print(E.objects.filter(rulebook_season="2026-2027").count())
print(list(E.objects.filter(rulebook_season="2026-2027", team_points_enabled=False).values_list("class_code", flat=True)))
'
```

Expected count: `42`.

Expected no-team-points codes: `H8`, `H14`, `W8`, `W14`, `D8`, `D14` (ordering may differ).

## Full staging regression

```bash
./portalctl exec web python manage.py test portal
```

The full portal suite must remain green before Phase A is considered validated.

## Staging UI smoke check

Because this slice intentionally adds no user-facing catalog UI, existing workflows should be unchanged. Verify at minimum:

- login and dashboard;
- Season Setup opens normally;
- existing season classes remain present and editable exactly as before;
- rider class assignments remain intact;
- show detail / show classes remain intact;
- standings and qualification pages render normally;
- existing Hunt Seat H8/H14 point-rider behavior remains unchanged.

## Promotion guardrail

Do not deploy this branch or migrations to production during Phase A validation. Production remains on the released v2.9.0 line until the v3.0 release process explicitly promotes a validated release candidate.
