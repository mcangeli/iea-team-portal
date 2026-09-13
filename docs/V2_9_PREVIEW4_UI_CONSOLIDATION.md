# ArenaLine v2.9.0 Preview 4 — UI Consolidation

## Purpose

Preview 4 consolidates ArenaLine presentation without redesigning the product or changing domain behavior. Preview 3 established the platform/module architecture; Preview 4 makes the visible application feel like one coherent system across those modules.

The guiding rule is simple: templates should express structure and meaning, while reusable presentation belongs in the shared ArenaLine CSS layer.

## Preview 4A — shared presentation contract

Implemented:

- unified `page-title` and `page-intro` spacing, typography, descriptive text, and action alignment;
- unified section-heading rhythm through `section-head`;
- normalized primary/secondary button presentation in light and dark themes;
- established consistent shared surfaces for cards, empty states, forms, finance cards, and table wrappers;
- standardized table container/header/hover treatment;
- improved theme-aware form controls and focus states;
- centralized dashboard workspace-tab styling in `static/css/arenaline-v290.css`;
- removed dashboard-local `<style>` presentation from `templates/portal/dashboard.html`;
- normalized roster filter-tab presentation and responsive behavior;
- added focused regression coverage for the shared presentation contract.

This first Preview 4 slice intentionally does not rewrite every template. Existing semantic classes such as `page-title`, `page-intro`, `section-head`, `entry-table`, `form-card`, `empty-state`, and `filter-tabs` now have a stronger common ArenaLine contract that later module passes can reuse.

## Preview 4B — dashboard family consolidation

Implemented:

- added `static/css/dashboard-v290.css` as the shared dashboard-family presentation layer;
- loaded the dashboard presentation layer from the shared ArenaLine base template;
- removed remaining template-local `<style>` blocks from the main, role, and Show Manager dashboard family;
- retained a common dashboard hero language for the main and role-specific dashboards;
- standardized workspace tabs, quick-action groups, course-status cards, summary spacing, dashboard hero marks, and responsive behavior;
- brought Show Manager into the same dashboard visual family with the shared ArenaLine hero treatment while preserving all hosted-show workflows;
- retained role-specific information architecture for coaches, team parents, show leads, points secretaries, and Show Manager rather than flattening those workflows into a generic dashboard;
- added focused regression coverage to prevent dashboard presentation from drifting back into template-local CSS.

Preview 4B is a presentation-only consolidation. No dashboard queries, permissions, role routing, show-host behavior, or competition logic are changed.

## Preview 4C — People / Families presentation

Implemented:

- added `static/css/people-v290.css` as the shared People / Families presentation layer;
- loaded the People presentation layer from the shared ArenaLine base template;
- aligned rider roster cards with the ArenaLine surface, typography, chip, hover, and theme treatment;
- improved rider roster section rhythm and roster-count presentation while preserving Futures / Upper School groupings;
- aligned rider profile hierarchy, contact strips, lifecycle banners, season-membership cards, class chips, and family-contact cards;
- aligned the parent / guardian directory with the same family contact-card presentation;
- aligned rider onboarding / editing forms and season-enrollment class choices with the shared ArenaLine form language;
- added responsive handling for rider profiles, family cards, and membership history;
- preserved `private_view`, `can_manage`, family-account, IEA member number, team-level, class-assignment, and season-assignment conditions unchanged;
- added focused regression coverage protecting both the new presentation layer and the existing IEA/privacy semantics.

Preview 4C remains presentation-only. Rider visibility, guardian relationships, account access, roster filters, IEA team assignments, and season enrollment behavior are unchanged.

## Preview 4D — Horses presentation

Implemented:

- added `static/css/horses-v290.css` as the ArenaLine horse-management presentation layer while retaining the existing `horses-v2.css` feature styles underneath it;
- loaded the Preview 4 horse layer from the shared ArenaLine base template;
- aligned horse registry cards, imagery, typography, metadata, status presentation, and hover behavior with the ArenaLine surface system;
- aligned horse-detail profile cards, detail lists, internal notes, Coggins/readiness panels, and season-eligibility history;
- aligned horse forms with the Preview 4 form language while preserving the existing two-column horse-data layout;
- aligned Show Horses, Horse of the Day, class chips, assignment notes, and action rows with the same visual system;
- aligned Horse Readiness statistics, readiness badges, missing-class warnings, Coggins warnings, success states, and leased-horse planning surfaces;
- preserved Horse & Hoofprint terminology, Coggins behavior, season eligibility, show-horse assignments, leased-horse planning, and all IEA-specific horse workflows unchanged;
- added focused regression coverage protecting the shared horse presentation hooks and Hoofprint/IEA terminology.

Preview 4D is presentation-only. Horse registry data, Coggins calculations, readiness rules, show assignments, Hoofprint behavior, and season eligibility logic are unchanged.

## Preview 4 goals

The remaining Preview 4 work should proceed module by module:

1. ~~Dashboard and role-specific dashboard consistency.~~
2. ~~People / Families presentation.~~
3. ~~Horses presentation.~~
4. IEA Competition presentation.
5. Operations / Communications presentation.
6. Finance presentation.
7. Administration / forms / destructive-action consistency.
8. Responsive and light/dark final polish.

## Guardrails

- Do not alter business logic or authorization merely to simplify presentation.
- Do not genericize genuine IEA terminology.
- Prefer existing shared semantic classes over adding page-specific CSS.
- Keep light and dark themes at feature parity.
- Preserve accessibility cues, focus states, semantic headings, and readable contrast.
- Avoid template-local `<style>` blocks unless a component is truly isolated and cannot reasonably belong to the shared presentation layer.
- No database migrations are expected from Preview 4 UI work.

## Validation gate

Run on staging after pulling the feature branch:

```bash
./portalctl upgrade
./portalctl exec web python manage.py check
./portalctl exec web python manage.py makemigrations portal --check --dry-run
./portalctl exec web python manage.py test portal.tests.test_v290_preview4_presentation portal.tests.test_v290_preview4_dashboards portal.tests.test_v290_preview4_people portal.tests.test_v290_preview4_horses portal.tests.test_v290_product_identity
./portalctl exec web python manage.py test portal
```

Expected results:

- Django system check passes;
- no migration/schema drift;
- Preview 4 presentation, dashboard-family, People / Families, and Horses tests pass;
- the full portal regression suite remains green;
- dashboards, People / Families, and horse-management screens render consistently in both light and dark modes;
- rider privacy, genuine IEA roster semantics, Horse & Hoofprint terminology, and horse-management behavior remain unchanged.
