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

## Preview 4B — dashboard family consolidation

Implemented shared dashboard presentation, removed remaining dashboard-local presentation CSS, standardized workspace tabs and quick actions, and aligned Show Manager with the main dashboard family while preserving role-specific workflows.

## Preview 4C — People / Families presentation

Implemented `static/css/people-v290.css`, aligning roster cards, rider profiles, guardian/family cards, onboarding forms, and responsive behavior while preserving all privacy, role, Futures/Upper, and season-assignment semantics.

## Preview 4D — Horses presentation

Implemented `static/css/horses-v290.css`, aligning horse registry/detail/forms, Coggins/readiness, show-horse planning, Horse of the Day, leased-horse planning, and Hoofprint-adjacent surfaces without changing horse or competition behavior.

## Preview 4E — IEA Competition presentation

Implemented `static/css/competition-v290.css`, aligning Shows, Show Detail, Standings, Season Archive, and Record Book while preserving genuine IEA terminology, point riders, H8/H14 exclusions, postseason tracks, qualification thresholds, and advancement behavior.

## Preview 4F — Operations / Communications presentation

Implemented `static/css/operations-v290.css`, aligning calendar, action items, lessons, volunteer, committees, and communication accents. The legacy calendar inline stylesheet is intentionally retained for v2.9 and is listed for ArenaLine 3.0 cleanup in `docs/V3_0_KICKOFF_REVIEW.md`.

## Preview 4G — Finance presentation

Implemented `static/css/finance-v290.css`, aligning finance summaries, treasurer worklists, accounts, budgets, ledger tables, family receivables/accounts, dues, credits, payments, assistance, reimbursement, and fundraising surfaces without changing accounting behavior.

## Preview 4H — Administration, forms, and destructive actions

Implemented `static/css/admin-v290.css`, aligning Users, Season Setup, Branding, generic forms, and delete/confirmation screens. Shared history-back behavior now has a safe dashboard fallback, and destructive confirmations no longer use direct `javascript:history.back()` links.

## Preview 4I — final responsive, theme, and navigation polish

Implemented:

- added `static/css/final-polish-v290.css` as the final cross-module responsive/accessibility layer;
- added consistent `:focus-visible` treatment for links, buttons, summaries, and form controls;
- improved mobile navigation scrolling, menu-panel behavior, touch-target sizing, action stacking, table overflow, and footer rhythm;
- verified the global shell against the `ARENA_MODULES` registry rather than the historical menu layout;
- moved Finance out of Operations and made it an independent top-level module menu for authorized finance users;
- retained Operations for Calendar, Action Items, Lessons, Volunteer, and Committees only;
- retained Competition as the IEA-specific destination for Shows, Standings, Season History, and Record Book;
- retained People and Horses as independent platform modules;
- retained Communications as the notification utility surface;
- retained Manage for organization administration: Users, Season Setup, Branding, Audit Log, and staff-only Django admin;
- renamed the People menu item from `Parents` to `Parents & guardians` to match current domain language;
- simplified Manage role gating so it is explicit and no longer depends on mixed template `and/or` precedence;
- added `portal/tests/test_v290_preview4_navigation.py` to protect the module/menu map, Finance separation, administration map, final-polish CSS, and mobile navigation behavior.

### Final navigation map

| ArenaLine area | Global navigation surface |
| --- | --- |
| Core | Dashboard, My Team |
| People & Families | Riders, Parents & guardians |
| Horses | Horse registry |
| IEA Competition | Shows, Standings, Season history, Record book |
| Operations | Calendar, Action items, Lessons, Volunteer, Committees |
| Finance | Finance dashboard, Family receivables, Dues setup, Accounts & categories, Season budget, Reports, Fundraising, Reimbursements |
| Communications | Notifications utility |
| Organization administration | Users, Season setup, Branding, Audit log, staff-only Django admin |

Finance visibility remains permission-aware through `portal_can_finance`; module availability remains independent through `portal_enabled_modules`.

## Preview 4 goals

1. ~~Dashboard and role-specific dashboard consistency.~~
2. ~~People / Families presentation.~~
3. ~~Horses presentation.~~
4. ~~IEA Competition presentation.~~
5. ~~Operations / Communications presentation.~~
6. ~~Finance presentation.~~
7. ~~Administration / forms / destructive-action consistency.~~
8. ~~Responsive, light/dark, and navigation final polish.~~

Preview 4 implementation is complete pending the final staging validation gate.

## Guardrails

- Do not alter business logic or authorization merely to simplify presentation.
- Do not genericize genuine IEA terminology.
- Prefer existing shared semantic classes over adding page-specific CSS.
- Keep light and dark themes at feature parity.
- Preserve accessibility cues, focus states, semantic headings, and readable contrast.
- Avoid template-local `<style>` blocks unless a component is intentionally deferred or truly isolated.
- No database migrations are expected from Preview 4 UI work.

## Final validation gate

Run on staging after pulling the feature branch:

```bash
./portalctl upgrade
./portalctl exec web python manage.py check
./portalctl exec web python manage.py makemigrations portal --check --dry-run
./portalctl exec web python manage.py test \
  portal.tests.test_v290_preview4_presentation \
  portal.tests.test_v290_preview4_dashboards \
  portal.tests.test_v290_preview4_people \
  portal.tests.test_v290_preview4_horses \
  portal.tests.test_v290_preview4_competition \
  portal.tests.test_v290_preview4_operations \
  portal.tests.test_v290_preview4_finance \
  portal.tests.test_v290_preview4_administration \
  portal.tests.test_v290_preview4_navigation \
  portal.tests.test_v290_product_identity
./portalctl exec web python manage.py test portal
```

Expected results:

- Django system check passes;
- no migration/schema drift;
- all Preview 4 presentation/navigation contracts pass;
- the full portal regression suite remains green;
- desktop and mobile navigation follow the final module map above;
- Finance appears only for users with finance access and is no longer nested beneath Operations;
- all completed module/admin surfaces remain coherent in light and dark themes;
- shared Back/Cancel behavior works on generic and destructive forms;
- rider privacy, Horse & Hoofprint behavior, IEA scoring/qualification semantics, operational workflows, finance behavior, and administration permissions remain unchanged.
