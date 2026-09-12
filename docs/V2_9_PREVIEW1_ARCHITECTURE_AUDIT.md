# ArenaLine v2.9.0 Preview 1 — Architecture Audit

## Purpose

v2.9.x is the transition from the original **IEA Team Portal** into **ArenaLine**: a modular equestrian operations platform that can support an IEA team today, broader competition workflows in v3+, and barn-management modules in v4+ without forcing every organization to enable every feature.

Preview 1 is intentionally architecture-first. Its job is to identify what can be safely normalized now, what is still IEA-specific, and what must remain backward compatible while ArenaLine gains a cleaner platform boundary.

## Guiding principles

1. **No destructive migration for the sake of naming.** Existing teams, riders, families, horses, shows, finance records, Hoofprints, histories, and host-show data must upgrade in place.
2. **ArenaLine is modular.** Organizations should be able to use only the pieces they need and enable additional modules later.
3. **Generic core vs discipline modules.** Universal equestrian concepts belong in the platform core; IEA-specific rules should progressively move behind an IEA competition boundary.
4. **Public data remains explicit.** v3 public functionality will follow the existing public-by-explicit-publication rule.
5. **Prepare for barn management without prematurely building v4.** v2.9 should remove assumptions that make a future barn/organization model difficult, but should not introduce unfinished barn features.

---

## Current architecture observations

### 1. `Team` is currently both tenant and IEA team

`portal.models.Team` is the root relationship for seasons, riders, guardians, events, finance, shows, audit events, committee assignments, and most permission scoping.

This works well for the current single-team product but creates an architectural ambiguity for ArenaLine:

- an ArenaLine customer may be a barn, club, school, trainer program, or organization;
- that organization may run one or more teams;
- a barn may use Horse, Family, Finance, Lesson, or Show modules without an IEA team at all.

### Decision for 2.9

Do **not** rename the database `Team` model to `Organization` in v2.9. That would create unnecessary migration and compatibility risk.

Instead:

- treat `Team` as the current tenant boundary for v2.9;
- introduce platform terminology and service boundaries that avoid adding new direct assumptions that every tenant is an IEA team;
- prepare a future `Organization` / `Program` abstraction for a later major-version migration;
- document all places where new code should prefer generic words such as organization, program, member, participant, competition, and module when IEA semantics are not required.

---

## 2. Universal concepts already exist, but are mixed with IEA rules

### Broadly reusable ArenaLine concepts

These concepts can serve multiple disciplines and future barn operations:

- User / profile
- Rider / participant
- Guardian / household relationship
- Horse
- Season / operating period
- Show / competition event
- Show class / competition class
- Venue / location data
- Calendar events
- Documents
- Finance accounts, categories, transactions, budgets, reimbursements
- Communications / notifications
- Lessons and attendance
- Staff/role assignments
- Show planning and show-day operations
- Audit history
- Publication state

### IEA-specific concepts currently embedded in generic models/workflows

Examples found in the current codebase:

- `SeasonClass.TeamLevel`: Futures / Upper / Both
- `SeasonMembership.TeamLevel`: Futures / Upper
- grade-driven automatic Futures/Upper assignment
- `Show.CompetitionLevel`: Regular / Region / Zone / National
- `Show.iea_zone`
- `Show.iea_region`
- `Show.futures_team_place`
- `Show.upper_team_place`
- IEA class identifiers such as H1/H2/H8/H14
- points-rider logic
- 18-point qualification logic
- IEA horse-contribution ratio semantics
- Hoofprint workflows

### Decision for 2.9

Do not remove these fields yet. They are production data and behavior.

Instead, classify them as **IEA competition module concerns** and prevent new generic ArenaLine code from depending directly on them unless the workflow is explicitly IEA-specific.

---

## 3. Dynamic model fields should be normalized

Two runtime-contributed fields are currently imported through `PortalConfig.import_models()`:

### `SeasonClass.class_code`

Currently added dynamically in `portal/season_class_code.py` with `contribute_to_class()`.

It also contains signal behavior that:

- normalizes the code to uppercase;
- copies the canonical code into linked `ShowClass.class_number` values.

### `Season.rides_per_contributed_horse`

Currently added dynamically in `portal/show_readiness_models.py` with `contribute_to_class()`.

### Preview 1 target

Move these into normal model definitions while preserving:

- existing database columns;
- existing migration history;
- behavior and defaults;
- data compatibility;
- signal/service behavior where still appropriate.

No data migration should be needed solely to move field declarations into the normal model structure.

---

## 4. Compatibility monkey patches should be removed

### `show_planning_extensions.py`

Adds a runtime `ShowPlanningItem.owner_id` property returning `claimed_by_id or assigned_to_id`.

**Target:** move any remaining consumers to the real fields or a normal model property and remove the runtime patch.

### `dashboard_workspace_extensions.py`

Monkey-patches `dashboards._workspace_links` to inject the v2.5 Show Manager workspace.

**Target:** make Show Manager a first-class dashboard workspace in the dashboard module and remove the monkey patch.

### `reimbursement_form_extensions.py`

Monkey-patches `ReimbursementRequestForm.__init__` so its model instance receives `team` before model validation.

**Target:** implement that behavior directly in the form class and remove the patch.

### `portal/apps.py`

`PortalConfig` currently imports multiple model extension modules and runtime patches during application startup.

**Target:** shrink startup imports to genuine signal registration / application setup rather than using AppConfig as a patch loader.

---

## 5. View modularization is improved but incomplete

The v2.0 refactor established `portal/view_modules/` and left `portal/views.py` as a compatibility namespace.

That transition has worked, but v2.9 should finish the separation:

- keep URL compatibility where useful;
- remove unnecessary re-export dependency over time;
- define clear feature modules;
- move new horse, Hoofprint, Host Show, finance, dashboard, and administration views behind consistent domain boundaries;
- avoid another monolithic compatibility layer growing indefinitely.

### Proposed ArenaLine domain boundaries

#### Core
- authentication
- organization/team scope
- people / rider / guardian relationships
- roles / permissions
- audit
- communications
- documents
- calendar

#### Horses
- horse registry
- season availability
- Coggins / future health-document boundary
- horse history

#### Competition
- generic shows
- generic classes / entries / results
- venues
- show-day operations
- host operations
- publication boundary

#### IEA Competition
- Futures / Upper
- IEA class codes
- points rider
- IEA qualification
- Region / Zone / National semantics
- Hoofprint
- horse-contribution requirements

#### Finance
- accounts
- categories
- budgets
- reimbursements
- family finance
- fundraising
- show finance

#### Barn Operations — future v4+
- lessons / training
- boarding
- care schedules
- veterinary / farrier
- facility resources
- staff / instructor relationships

---

## 6. Navigation should become module-aware

The current navigation is role-aware but fundamentally assumes the same product modules are relevant to every installation.

ArenaLine should evolve toward two dimensions:

1. **Permission:** what is this user allowed to do?
2. **Module enablement:** what does this organization actually use?

### 2.9 preparation

Do not build a complete module marketplace or subscription system.

Instead:

- centralize navigation construction;
- stop adding dashboard/navigation behavior through monkey patches;
- create stable module identifiers in code where useful;
- make it possible for future versions to hide disabled modules cleanly.

Potential future module IDs:

- `core`
- `people`
- `horses`
- `competition`
- `competition_iea`
- `finance`
- `communications`
- `lessons`
- `host_operations`
- `public_portal`
- `barn_operations`

---

## 7. Branding transition should be separated from database identity

ArenaLine branding should replace the user-facing **IEA Team Portal** name throughout v2.9 without forcing risky package/database renames.

### Safe to rebrand in 2.9

- page titles
- login / error pages
- header/footer identity
- README and architecture documentation
- release documentation
- product copy
- emails / notifications where they name the product
- install/update messaging
- default branding assets

### Keep stable during 2.9 unless technically necessary

- Django app label `portal`
- Python package paths
- migration app label
- database table names
- existing URL names used internally
- Git repository name

A repository rename can be considered separately after the application transition is proven stable.

---

## 8. Show architecture should prepare for multiple disciplines

The existing `Team.discipline` and `SeasonClass.discipline` fields already recognize Hunt Seat, Western, Dressage, and multi/other values. This is a useful start, but competition behavior remains IEA-shaped.

### Long-term ArenaLine direction

Use a common competition engine for:

- local / schooling / open shows
- IEA
- USEF / USHJA hunter-jumper
- dressage
- Western disciplines
- future competition types

Each competition type should own its specialized:

- class/division vocabulary;
- membership identifiers;
- eligibility rules;
- scoring rules;
- entry requirements;
- qualification rules;
- result formats;
- required documents.

### 2.9 rule

Do not attempt a show-engine rewrite in 2.9. Instead, avoid introducing additional IEA-specific fields into the base `Show` model unless they are unavoidable for current IEA functionality.

---

# Preview 1 implementation plan

## Phase A — normalize temporary compatibility code

1. Move reimbursement team-binding into `ReimbursementRequestForm`.
2. Integrate Show Manager workspace links directly into dashboard workspace construction.
3. Replace/remove the `ShowPlanningItem.owner_id` runtime patch.
4. Reduce `PortalConfig.ready()` patch imports.
5. Add focused regression tests before removing each patch.

## Phase B — normalize runtime model field declarations

1. Move `SeasonClass.class_code` into the normal `SeasonClass` model declaration.
2. Preserve class-code normalization/synchronization behavior in an explicit service or signal module.
3. Move `Season.rides_per_contributed_horse` into the normal `Season` model declaration.
4. Run `makemigrations --check --dry-run` and require **no schema drift** unless an intentional migration is documented.

## Phase C — establish ArenaLine architecture boundaries

1. Update `ARCHITECTURE.md` from IEA Team Portal terminology to ArenaLine platform terminology.
2. Document Core, Horses, Competition, IEA Competition, Finance, and future Barn Operations boundaries.
3. Establish naming rules for generic vs IEA-specific code.
4. Inventory direct `Team` assumptions that should eventually become organization/program scoped.

## Phase D — view and URL normalization plan

1. Inventory all current view modules and standalone `*_views.py` files.
2. Define final feature ownership for each.
3. Identify compatibility re-exports that can be retired safely.
4. Keep existing user-facing URLs stable throughout v2.9 wherever possible.

## Phase E — Preview 1 validation gate

Required before Preview 1 is considered complete:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations portal --check --dry-run
docker compose exec web python manage.py test portal.tests
```

Additional focused tests must cover:

- dashboard workspace selection;
- Show Manager workspace visibility;
- reimbursement creation/model validation;
- Show Planning ownership behavior;
- SeasonClass class-code propagation;
- horse-readiness ride-ratio behavior.

---

# Explicitly deferred beyond Preview 1

- introducing a new `Organization` database model;
- migrating existing `Team` rows into organization/program records;
- building module enable/disable administration;
- genericizing all current IEA show fields;
- public routes (v3);
- barn-management features (v4);
- USEF/USHJA, dressage, Western, or local-show rule engines;
- repository rename.

These should be informed by the boundaries established here, not rushed into the cleanup release.

---

# Recommended v2.9.x sequence

## 2.9.0 Preview 1 — Foundation cleanup
Compatibility shims, dynamic fields, architecture boundaries, view/URL inventory.

## 2.9.0 Preview 2 — ArenaLine identity
User-facing rebrand, product copy, login/error screens, default branding, documentation.

## 2.9.0 Preview 3 — Platform/module preparation
Centralized module-aware navigation and organization-neutral service boundaries where safe.

## 2.9.0 Preview 4 — UI consolidation
Template structure, CSS cleanup, navigation consistency, mobile/light/dark review.

## 2.9.0 Preview 5 — Security/data audit
Permission matrix, model validation, constraints/index review, privacy boundaries, historical access.

## 2.9.0 Preview 6 — Deployment cleanup
`portalctl` branch/ref/tag handling, upgrade flow, installation language, ArenaLine deployment conventions.

## 2.9.0 Release Candidate
Full regression, migration validation, upgrade-from-v2.5 test, release documentation, and production readiness review.

---

## Architecture north star

ArenaLine should evolve toward:

**Organization / Program → enabled modules → People + Horses + Competition + Finance + Communications + Barn Operations**

IEA should become one competition specialization within that platform rather than the identity of the entire application.

The 2.9 series should make that future easier without destabilizing the mature IEA workflows that already work today.
