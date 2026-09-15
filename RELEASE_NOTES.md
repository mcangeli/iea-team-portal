# Release Notes

> **Current release history:** ArenaLine's concise current changelog now lives in `CHANGELOG.md`, with detailed release documents under `docs/releases/`. This file is retained as the detailed historical record for earlier release families.
>
> Current stable release: **v3.2.3 — People & Operations Polish**. See `CHANGELOG.md` and `docs/releases/v3.2.3.md`.

## v3.0.0 — IEA Class Catalog Foundation

ArenaLine v3.0.0 establishes the official, versioned IEA class-catalog foundation and completes the private-portal cleanup needed before public/external publishing work begins.

### Official IEA class catalog
- Added versioned 2026–2027 IEA class reference data for Hunt Seat, Western, and Dressage.
- Added 42 season-assignable youth placement classes: H1–H14, W1–W14, and D1–D14.
- Catalog metadata includes class code/name, discipline, team level, class family, scoring eligibility, season assignability, source rule, revision date, active state, and display order.
- `SeasonClass` remains organization-specific and can link to the official catalog without rewriting historical/manual classes.

### Season Setup
- Added season-level IEA catalog configuration for rulebook season and participating disciplines.
- Added official class selection/link/sync to Season Class create/edit workflows.
- Added conservative reconciliation tooling that matches explicit code/discipline/team-level compatibility and does not guess from display names.

### Show Setup and show-only classes
- Normal official classes flow through `IEAClassCatalogEntry → SeasonClass → ShowClass → Entries/results`.
- Added direct catalog links for official show-only classes.
- Added optional warm-up classes H7x/H8x, H13x/H14x, W7x/W8x, W13x/W14x, D7x/D8x, and D13x/D14x.
- Warm-up entries require the corresponding same-show prerequisite class and never award individual/team points.
- Added Hunt Seat Varsity Open Championship (VOC) as a show-only class with same-show H1/H2 eligibility/ranking logic and non-scoring behavior.

### Catalog-driven scoring policy
- Replaced Hunt Seat-only scoring exceptions with effective catalog metadata where available.
- H8/H14, W8/W14, and D8/D14 are all treated as no-team-points classes.
- `team_points_enabled=False` blocks point-rider/team-track designation.
- `individual_points_enabled=False` suppresses result points for both season-backed and direct show-only classes.
- Retained the former H8/H14 heuristic only as a compatibility fallback for unlinked historical rows.
- Added a data migration to reconcile invalid catalog-linked point-rider/team-entry state from older behavior.

### Presentation and architecture cleanup
- Removed the legacy Calendar inline `<style>` block and moved its presentation into the shared Operations stylesheet.
- Preserved Month/Agenda views, filtering, responsive behavior, light/dark presentation, and mobile switching.
- Refreshed ArenaLine architecture documentation and clarified the generic platform vs. `competition_iea` boundary.
- Established the public/external guardrail that nothing becomes public merely because it exists internally; future public data must be explicitly published and allow-listed.

### Migrations
- `0048_v300_iea_class_catalog.py`
- `0049_v300_seed_iea_class_catalog.py`
- `0050_v300_seasonclass_catalog_link.py`
- `0051_v300_iea_season_catalog_configuration.py`
- `0052_v300_seasonclass_multidiscipline_uniqueness.py`
- `0053_v300_showclass_catalog_link.py`
- `0054_v300_seed_iea_show_only_warmups.py`
- `0055_v300_seed_iea_voc.py`
- `0056_v300_reconcile_catalog_non_team_entries.py`

### Validation and release
- Focused catalog, season setup, Show Setup, warm-up, VOC, and scoring-policy tests passed on staging.
- The full portal regression suite passed with 425 tests before production promotion.
- Stable production promotion uses the `v3.0.0` release tag and `./portalctl update`.
- Added `RELEASE_CHECKLIST.md` so future releases cannot be promoted to `main` until version identity, README, release notes, roadmap, architecture/supporting docs, tests, and tagging are aligned.

See `docs/releases/v3.0.0.md` for the focused v3.0.0 release document.

## v2.1.5 — Post-Show Horse History

v2.1.5 completes the 2.1.x horse-operations progression by preserving what actually happened after each show and carrying that history into season summaries and the Team Record Book.

### Post-show Horse History

The remainder of this file preserves the detailed historical 2.x release notes from the original release record. For current release documentation, use `CHANGELOG.md` and `docs/releases/`.
