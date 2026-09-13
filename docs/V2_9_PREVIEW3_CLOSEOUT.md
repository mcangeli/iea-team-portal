# ArenaLine v2.9.0 Preview 3 — Closeout Audit

## Status

Preview 3 is ready to close once the staging closeout test and full portal regression suite pass on the final branch head.

The preview successfully establishes the application seams needed for ArenaLine to evolve beyond a single IEA-team implementation without performing a destructive tenant-model migration.

## Verified platform contracts

### Module registry

The stable ArenaLine module IDs are centralized in `portal/modules.py`:

- `core`
- `people`
- `horses`
- `competition_iea`
- `operations`
- `finance`
- `communications`

All current modules remain enabled by default. `core` is mandatory. Unknown module IDs are filtered at the resolver boundary.

`competition_iea` remains explicitly competition-specialized; the remaining modules are platform scope.

### Organization context

Generic platform code resolves tenant context through `portal.platform` rather than depending directly on `UserProfile.team`.

The v2.9 persisted tenant remains `Team`. No Team-to-Organization schema rename is part of Preview 3.

The key organization seams are:

- `organization_for_user()`
- `organization_for_view_user()`
- `active_period_for_organization()`
- `role_for_user()`
- `can_manage_organization()`
- `enabled_modules_for_organization()`

Legacy authenticated-view behavior is preserved, including the existing unassigned-superuser behavior.

### Shared shell

The shared ArenaLine shell uses `portal_organization` as its tenant contract.

`portal_team` remains available only as a compatibility alias for older feature templates during the v2.9 transition.

Anonymous/login surfaces remain generic ArenaLine surfaces and do not select or expose a tenant before authentication.

### Generic domain boundaries

Preview 3 establishes organization/operating-period seams for:

- Operations / Communications
- Finance
- Administration
- People / Roster
- Branding

The shared legacy `_team()` and `_active_season()` compatibility helpers now delegate to ArenaLine platform services. That allows older modules to remain stable while still crossing the same platform boundary.

Persisted `team` and `season` field names remain valid implementation details behind these services.

### IEA specialization preserved

Preview 3 deliberately does not genericize genuine IEA concepts. The following remain IEA/team language where appropriate:

- Futures / Upper
- IEA classes and member numbers
- points riders and team points
- qualification rules
- Regionals / Zones / Nationals
- Hoofprint
- IEA competition workflows

This separation is intentional and is part of the ArenaLine modular architecture.

## Validation history

Throughout Preview 3, staging validation has remained green after each controlled slice, including focused v2.9 boundary tests and the full `portal` test suite.

The final closeout gate should run:

```bash
./portalctl upgrade
./portalctl exec web python manage.py check
./portalctl exec web python manage.py makemigrations portal --check --dry-run
./portalctl exec web python manage.py test \
  portal.tests.test_v290_module_enablement \
  portal.tests.test_v290_platform_boundaries \
  portal.tests.test_v290_organization_shell \
  portal.tests.test_v290_generic_domain_context \
  portal.tests.test_v290_finance_context \
  portal.tests.test_v290_administration_context \
  portal.tests.test_v290_people_context \
  portal.tests.test_v290_preview3_closeout \
  portal.tests.test_v290_product_identity
./portalctl exec web python manage.py test portal
```

Expected result:

- Django system check passes;
- no migration/schema drift;
- focused Preview 3 closeout tests pass;
- full portal suite remains green.

## Deliberately deferred beyond Preview 3

Preview 3 does not add:

- an `Organization` database model;
- destructive Team/Season model renames;
- organization module-settings persistence;
- subscription/licensing controls;
- an admin UI for enabling or disabling modules;
- URL-level module enforcement;
- a generic competition-engine rewrite;
- removal of all compatibility aliases;
- migration of genuine IEA terminology out of IEA workflows.

Finance is currently presented inside the Operations navigation group in the all-modules-enabled experience. Independent navigation behavior for arbitrary per-organization module combinations should be finalized when real module enablement/configuration is introduced; it is not user-visible in Preview 3 because all current modules remain enabled by default.

## Closeout decision

If the final staging gate remains green, Preview 3 should be considered complete.

Preview 4 can then focus on UI consolidation and presentation consistency on top of the stabilized ArenaLine module and organization boundaries, without reopening the tenant architecture work completed here.
