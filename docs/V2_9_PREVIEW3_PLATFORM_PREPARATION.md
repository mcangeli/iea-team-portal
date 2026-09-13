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

## Architectural rules

1. `Team` remains the database tenant in v2.9.
2. Generic platform code should prefer organization-oriented service boundaries when the concept is not specifically an IEA team.
3. IEA-specific workflows may continue to use team semantics where that meaning is real.
4. Module availability and user permission are separate concerns: enabling a module never grants access by itself.
5. All modules remain enabled by default until a later feature explicitly introduces organization-level configuration.
6. Stable module IDs are application contracts and should not be renamed casually.
7. `portal_organization` is the preferred shell/template tenant contract; `portal_team` is compatibility-only during the v2.9 transition.

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
- default organization and active operating-period service boundaries;
- organization role / management authority boundaries;
- generic `portal_organization` shell context;
- preservation of the `portal_team` compatibility alias;
- elimination of direct `portal_team` usage from the shared ArenaLine shell.

## Validation gate

Run on staging after pulling the feature branch:

```bash
./portalctl upgrade
./portalctl exec web python manage.py check
./portalctl exec web python manage.py makemigrations portal --check --dry-run
./portalctl exec web python manage.py test portal.tests.test_v290_module_enablement portal.tests.test_v290_platform_boundaries portal.tests.test_v290_organization_shell portal.tests.test_v290_product_identity
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
