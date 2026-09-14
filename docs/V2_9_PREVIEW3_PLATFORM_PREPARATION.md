# ArenaLine v2.9.0 Preview 3 — Platform / Module Preparation

## Purpose

Preview 3 turns the product-domain boundaries established in Preview 2C into stable application seams. It is intentionally preparatory: current ArenaLine installations continue to expose every existing module, and `Team` remains the persisted tenant model.

The goal is to make later organization-level module configuration and a future `Organization` / `Program` model possible without another navigation or platform-wide refactor.

## Preview 3A — module registry and navigation boundary

Implemented:

- moved the ArenaLine module registry into `portal/modules.py`;
- retained the stable module IDs established during Preview 2C;
- added `resolve_enabled_modules()` as the validation/order boundary for module sets;
- made `core` mandatory at the resolver boundary;
- ignore unknown module IDs rather than exposing invalid module state to templates;
- added `enabled_modules_for_organization()` as the future organization configuration seam;
- kept all existing modules enabled by default;
- made `templates/base.html` conditionally render domain navigation from `portal_enabled_modules`;
- kept role/permission checks independent from module availability checks.

No database field or module administration UI is introduced in this preview.

## Preview 3B — organization context boundary

Implemented:

- added `portal.platform.organization_for_user()`;
- generic platform code can resolve the current organization context without directly depending on `UserProfile.team`;
- the helper still returns the existing `Team` instance in v2.9;
- required-context behavior preserves the existing permission failure semantics;
- the shared context processor now obtains its tenant through this platform boundary;
- no model/table/relationship rename is performed.

## Preview 3C — shared shell / operating-context boundary

Implemented:

- expanded `portal.platform` with `default_organization()`, `active_period_for_organization()`, `role_for_user()`, and `can_manage_organization()`;
- moved login branding tenant lookup, active-season lookup, role lookup, and shell management authority out of the context processor;
- added `portal_organization` as the generic template context contract;
- retained `portal_team` as a v2.9 compatibility alias for feature templates that still use persisted Team vocabulary;
- moved the shared ArenaLine shell (`templates/base.html`) entirely to `portal_organization`;
- preserved all existing database relationships, URLs, permissions, and visible navigation behavior.

This makes the application shell organization-oriented even though the current persisted tenant is still `Team`.

## Preview 3D — generic Operations / Communications context boundary

Implemented:

- moved action-item, calendar, RSVP, and announcement entry points to `organization_for_user()`;
- moved active-period lookup in those generic workflows to `active_period_for_organization()`;
- preserved persisted `team` and `season` fields as compatibility details behind the platform boundary;
- preserved existing permission checks, URLs, forms, notification behavior, and IEA-specific audience logic;
- replaced one remaining generic calendar-delete reference to “team record” with “organization record”;
- added focused regression coverage preventing these generic domain entry points from drifting back to `_team(request.user)` / `_active_season()`.

This is intentionally not a blanket terminology replacement. Genuine team-level and IEA competition code continues to use team semantics.

## Preview 3E — Finance organization / operating-period boundary

Implemented:

- moved the family-finance view domain to `organization_for_user()` for tenant resolution;
- moved active finance-period lookup to `active_period_for_organization()`;
- covered receivables, dues setup/generation, home barns, family accounts, credits, service agreements, assistance claims, and family payments;
- preserved persisted `team` / `season` fields, finance permission checks, audit events, validation, and transaction behavior;
- retained existing finance forms and query filters so this remains a context-boundary refactor rather than a finance-model rewrite;
- added Finance-specific regression coverage to prevent direct `_team(request.user)` / `_active_season()` usage from returning to the family-finance domain.

The finance domain is now organization-oriented at the application boundary while remaining fully compatible with the v2.9 Team-backed schema.

## Preview 3F — Administration organization boundary

Implemented:

- added `organization_for_view_user()` to preserve the legacy authenticated-view rule that ordinary users require an assigned organization while an unassigned superuser may continue to resolve no tenant;
- moved committee administration, user onboarding/account management, password reset, and audit-log entry points to the platform organization boundary;
- moved active-period lookups in administration to `active_period_for_organization()`;
- preserved persisted `profile__team`, committee `team`, season, forms, permission checks, and audit records behind that boundary;
- changed generic audit-log presentation from “Team audit log” to “Organization audit log” while keeping stored Team-backed audit data unchanged;
- added focused regression coverage for the compatibility semantics and administration-domain boundary.

## Preview 3G — People / roster organization boundary

Implemented:

- routed the shared legacy `_team()` compatibility helper through `organization_for_view_user()`;
- removed direct `UserProfile.team` storage knowledge from the shared tenant resolver;
- moved People/Roster entry points themselves directly to `organization_for_view_user()` rather than leaving the domain dependent on the compatibility alias;
- moved active-period lookup in People/Roster to `active_period_for_organization()`;
- preserved the existing dashboard no-organization behavior, superuser/no-profile behavior, and ordinary-user assignment requirement;
- retained rider/guardian privacy and visibility services, family-account visibility, and roster query behavior;
- retained persisted `team` / `season` relationships behind the boundary;
- deliberately preserved explicit IEA semantics including Futures/Upper assignments, IEA member identifiers, season classes, and team/class assignment language;
- expanded focused People regression coverage to prevent direct `_team(request.user)` / `_active_season()` usage from returning while also protecting the IEA-specific vocabulary and privacy seams.

The shared `_team()` helper remains available as a compatibility API for legacy modules, but the People domain now consumes the ArenaLine platform services directly.

## Preview 3H — remaining generic-domain closure

Implemented:

- moved the horse registry and horse/show access entry points to `organization_for_view_user()`;
- moved horse active-period lookup to `active_period_for_organization()` while keeping persisted horse/team/show relationships unchanged;
- moved lesson scheduling, lesson groups, attendance, show availability, volunteer tracking, and volunteer exports directly to the platform organization/operating-period services;
- moved role-dashboard entry points directly to the platform services while preserving the existing no-organization behavior and all role/committee authorization logic;
- preserved genuine IEA concepts in those surfaces, including Futures/Upper, Team Parent, Points Secretary, show leadership, team-level CSV output, and qualification/scoring summaries;
- audited the older split Finance modules (`finance_core`, `finance_reports`, `show_finance`, and `fundraising`) and intentionally left them on the `_team()` / `_active_season()` compatibility API because those helpers already delegate through the platform boundary and the transaction-heavy modules do not directly depend on profile tenant storage;
- added a Preview 3 closure regression protecting Horses, Lessons/volunteers, dashboards, and the shared compatibility seam.

Preview 3 is considered functionally complete once the staging validation gate below is green.

## Architectural rules

1. `Team` remains the database tenant in v2.9.
2. Generic platform code should prefer organization-oriented service boundaries when the concept is not specifically an IEA team.
3. IEA-specific workflows may continue to use team semantics where that meaning is real.
4. Module availability and user permission are separate concerns: enabling a module never grants access by itself.
5. All modules remain enabled by default until a later feature explicitly introduces organization-level configuration.
6. Stable module IDs are application contracts and should not be renamed casually.
7. `portal_organization` is the preferred shell/template tenant contract; `portal_team` is compatibility-only during the v2.9 transition.
8. Persisted `team` / `season` field names may remain behind generic organization / operating-period service boundaries until a later intentional schema migration.
9. `_team()` is compatibility-only; new generic platform code should resolve organization context through `portal.platform` directly.

## Current module IDs

- `core`
- `people`
- `horses`
- `competition_iea`
- `operations`
- `finance`
- `communications`

## Regression coverage

Preview 3 adds focused tests for:

- default module resolution;
- registry ordering;
- mandatory `core` behavior;
- rejection of unknown module IDs;
- module-aware navigation guards;
- organization module resolution defaults;
- current `Team`-backed organization lookup;
- unassigned-account behavior and required organization permission handling;
- legacy superuser view-context behavior through `organization_for_view_user()`;
- default organization and active operating-period service boundaries;
- organization role / management authority boundaries;
- generic `portal_organization` shell context;
- preservation of the `portal_team` compatibility alias;
- elimination of direct `portal_team` usage from the shared ArenaLine shell;
- generic Operations / Communications organization-context resolution;
- Finance organization / operating-period resolution;
- Administration organization / operating-period resolution;
- direct People/Roster organization / operating-period resolution;
- direct Horse, Lessons/volunteer, and role-dashboard organization / operating-period resolution;
- preservation of rider/guardian privacy and roster visibility services;
- preservation of IEA roster, team-level, dashboard-role, and volunteer export semantics;
- compatibility use of persisted team/season fields behind those boundaries;
- preservation of finance and administration permission/audit services;
- compatibility routing for legacy split Finance modules;
- theme-aware footer mark contrast;
- generic ArenaLine login branding and signature treatment.

## Validation gate

Run on staging after pulling the feature branch:

```bash
./portalctl upgrade
./portalctl exec web python manage.py check
./portalctl exec web python manage.py makemigrations portal --check --dry-run
./portalctl exec web python manage.py test portal.tests.test_v290_module_enablement portal.tests.test_v290_platform_boundaries portal.tests.test_v290_organization_shell portal.tests.test_v290_generic_domain_context portal.tests.test_v290_finance_context portal.tests.test_v290_administration_context portal.tests.test_v290_people_context portal.tests.test_v290_preview3_closure portal.tests.test_v290_product_identity
./portalctl exec web python manage.py test portal
```

Expected results:

- Django system check passes;
- no migration/schema drift;
- focused v2.9 tests pass;
- the full portal regression suite remains green;
- navigation and branding appear unchanged with all current modules present.

## Deliberately deferred

Preview 3 does **not** yet add:

- an `Organization` database model;
- an organization module-settings table;
- subscription or licensing controls;
- an admin UI for enabling/disabling modules;
- URL-level module enforcement;
- a generic competition-engine rewrite;
- migration of IEA terminology out of genuine IEA workflows.

Those features can now be built behind the module and organization boundaries established here rather than directly into the application shell.
