# ArenaLine v3.0.0 — IEA Rulebook & Class Catalog Foundation

## Status

Design/source-verification phase. No schema migration has been introduced yet.

## Validation environment

All v3.0 development validation must run against the isolated ArenaLine staging installation before any production promotion is considered. This includes migration rehearsal, catalog seeding, scoring/qualification regression tests, permission tests, UI smoke tests, and full portal regression runs.

Production remains pinned to the released v2.9.0 line during this work. The v3.0 branch must not be validated by applying experimental migrations or seed data directly to production.

## Goal

Replace free-form, organization-authored IEA class definitions with a versioned, official IEA class catalog while preserving `SeasonClass` as the organization/season-specific instance used by existing rider assignments, shows, entries, results, scoring, and historical records.

The intended flow is:

`IEAClassCatalog -> SeasonClass -> Rider season assignments -> ShowClass -> Entries/results -> Qualification/scoring`

## Official source of truth

The IEA Rules & Policies page publishes separate General, Hunt Seat, Western, and Dressage rulebooks for the 2026–2027 season. The discipline rulebooks contain the authoritative class descriptions and eligibility language.

Initial source set:

- IEA General Rules & Regulations 2026–2027
- IEA Hunt Seat Rules & Regulations 2026–2027
- IEA Western Rules & Regulations 2026–2027
- IEA Dressage Rules & Regulations 2026–2027

The catalog must be built from those official sources and versioned by competition/rulebook season. Class names, codes, scoring flags, eligibility groupings, and other domain rules must not be invented from memory or inferred solely from existing ArenaLine data.

### Confirmed examples from the 2026–2027 rulebooks

Hunt Seat H3301/H3302 uses official class identifiers such as H1, H2, H3, etc. H8 is `Junior Varsity Beginner Equitation on the Flat - Walk/Trot`; its rule text explicitly states that individual points are tracked and that no team points are awarded in H8 during regular or post-season shows.

Western W3301/W3302 similarly defines class identifiers and separates horsemanship from reining/ranch-riding placement logic.

Dressage D3300 defines Upper School and Futures classes and separates Dressage Test from Dressage Seat Equitation (DSE) ability levels.

The complete catalog must be extracted and reviewed discipline by discipline before production seed data is committed.

## Existing ArenaLine model

`SeasonClass` currently stores:

- `season`
- `name`
- `team_level` (`futures`, `upper`, `both`)
- `discipline`
- `sort_order`
- `active`
- `class_code`

Existing `SeasonMembership.classes` is a many-to-many relationship to `SeasonClass`. This is important historical and operational data and must remain valid through the 3.0 migration.

## Proposed reference model

Introduce an IEA-specific reference model in the `competition_iea` domain. Working name: `IEAClassCatalogEntry`.

Proposed fields:

- `rulebook_season` — canonical version such as `2026-2027`
- `discipline` — hunt seat / western / dressage
- `class_code` — official identifier such as H1, W1, etc.
- `official_name`
- `team_level` — upper / futures / both where supported by the rulebook
- `ability_level` — open / intermediate / novice / beginner or discipline-specific equivalent
- `class_family` — e.g. flat, over_fences, horsemanship, reining, ranch_riding, dressage_test, dse
- `individual_applicable`
- `team_applicable`
- `team_points_enabled`
- `performance_class` — whether this is a performance class versus rail/group class where useful
- `active`
- `sort_order`
- `source_rule`
- `source_revision_date`

The model should be immutable or tightly controlled once used by a historical season. New rulebook seasons should create a new catalog version rather than mutating old definitions.

## SeasonClass relationship

Add an optional reference from `SeasonClass` to the catalog entry rather than replacing `SeasonClass`.

Conceptually:

- catalog entry = official IEA reference definition
- season class = organization-specific activation/instance for one season

Existing historical `SeasonClass` rows should initially retain their current data and may have a null catalog reference until safely reconciled.

For a new IEA season, the preferred workflow becomes:

1. choose the applicable IEA rulebook season;
2. choose participating discipline(s);
3. load/select official catalog classes;
4. generate organization `SeasonClass` rows from those entries;
5. allow administrators to activate/deactivate applicable classes without editing the official definition;
6. assign riders to those season classes;
7. allow show classes to select only from valid season classes.

## Migration strategy

### Phase A — reference model only

Create the versioned catalog model and seed verified 2026–2027 official data. Do not change existing `SeasonClass` behavior yet.

### Phase B — optional SeasonClass catalog link

Add a nullable foreign key from `SeasonClass` to the catalog. Preserve existing rows and existing uniqueness behavior during migration.

### Phase C — reconciliation

Provide deterministic matching for existing classes using discipline + class code + team level where possible. Do not silently attach ambiguous legacy classes.

### Phase D — catalog-backed season setup

Update Season Setup so new IEA seasons derive classes from the official catalog rather than requiring free-form creation.

### Phase E — show-class restrictions

Update show-class creation to select from valid season classes and preserve all current historical show/result relationships.

## Scoring and rule-data boundary

Rules currently represented directly in application logic should be reviewed one by one before moving them to catalog data.

A rule belongs in catalog/reference data when it is an official property of a specific class/rulebook version. Example: the 2026–2027 Hunt Seat H8 rule explicitly disables team points while still tracking individual points.

Do not move organization policy or runtime authorization into the catalog.

## Guardrails

- Preserve historical `SeasonClass` primary keys and relationships.
- Preserve rider season assignments through migration.
- Preserve existing results, qualification history, show classes, and scoring history.
- Do not rename `Team` or perform unrelated platform-schema changes as part of this feature.
- Keep the catalog in the IEA competition boundary, not generic ArenaLine core.
- Never overwrite historical catalog versions when a later IEA rulebook changes a class.
- Do not seed unverified class definitions.
- Add regression coverage before changing scoring behavior.
- Run all migration, seed, scoring, permission, presentation, and full-suite validation on ArenaLine staging first.
- Do not use production as a v3.0 test environment.

## First implementation slice

1. Extract the full official 2026–2027 Hunt Seat, Western, and Dressage class tables from the IEA rulebooks.
2. Review the extracted catalog against existing ArenaLine `SeasonClass` assumptions.
3. Add baseline tests for current class/scoring behavior, especially H8/H14 handling and historical season assignments.
4. Introduce the catalog reference model and migration.
5. Seed only the verified 2026–2027 catalog.
6. Add model-level tests proving rulebook-season version isolation.
7. Deploy the feature branch to ArenaLine staging, apply migrations there, run the focused v3.0 tests, then run the full portal regression suite.
8. Perform staging UI smoke tests before considering the slice complete.

## Deferred until source extraction is complete

- automatic legacy class reconciliation;
- Season Setup UI changes;
- show-class UI restrictions;
- migration of hard-coded scoring rules;
- qualification-rule refactoring.

These depend on a reviewed source catalog and should not be implemented from assumptions.