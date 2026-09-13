# ArenaLine v2.9.0 Preview 5 Closeout

## Status

Preview 5 — Security & Data-Access Audit is complete pending the final closeout regression run on staging.

No schema changes were required during Preview 5. The work concentrated on proving and protecting the existing server-side authorization model with explicit multi-organization, family/privacy, delegated-role, export/file, and mutation coverage.

## Security guarantees covered

The v2.9 security contract now has focused regression coverage for:

- organization/tenant isolation;
- direct-object access by guessed primary key;
- nested child-object access through organization-owned parents;
- family/private rider visibility;
- Family Account visibility;
- Rider denial from Finance;
- Treasurer season-scoped Finance delegation;
- Points Secretary competition-only delegation;
- Futures/Upper Team Parent squad-scoped coordination;
- Show Lead assigned-show-only authority;
- point-rider/privacy behavior retained by existing competition tests;
- Hoofprint and horse-list upload/download/finalization scoping;
- Calendar private-event visibility;
- Lesson visibility for linked riders;
- Volunteer submission/review boundaries;
- Action Item visibility and mutation;
- Notification ownership;
- management-only roster/guardian exports;
- Finance reports/exports and receipt access;
- archived-season mutation protections.

## Preview 5 focused test files

- `portal/tests/test_v290_preview5_security_boundaries.py`
- `portal/tests/test_v290_preview5_cross_organization.py`
- `portal/tests/test_v290_preview5_private_exports.py`
- `portal/tests/test_v290_preview5_delegated_roles.py`
- `portal/tests/test_v290_preview5_operations_access.py`

These are intentionally supplemented by existing hardening/regression tests for Finance, fundraising privacy, archived-season permissions, show-day role behavior, prize-list scheduling, and host-show role behavior.

## Final staging regression matrix

Run the focused security matrix:

```bash
./portalctl exec web python manage.py test \
  portal.tests.test_v290_platform_boundaries \
  portal.tests.test_v290_preview5_security_boundaries \
  portal.tests.test_v290_preview5_cross_organization \
  portal.tests.test_v290_preview5_private_exports \
  portal.tests.test_v290_preview5_delegated_roles \
  portal.tests.test_v290_preview5_operations_access \
  portal.tests.test_finance_hardening \
  portal.tests.test_v196_fundraising_privacy \
  portal.tests.test_v197_prize_list_schedule \
  portal.tests.test_v197_release_candidate \
  portal.tests.test_v199_archive_permissions \
  portal.tests.test_v250_host_role_matrix
```

Then run the full application regression suite:

```bash
./portalctl exec web python manage.py test portal
```

The Preview 5 closeout gate is green only when both commands pass.

## Security posture carried into Preview 6

Preview 6 should not relax these boundaries while cleaning deployment/release behavior. In particular:

- production/staging configuration changes must not bypass organization resolution;
- media/file serving changes must preserve application authorization for protected artifacts;
- version/release cleanup must not alter role or module authorization behavior;
- operational scripts should run preflight/check/migration validation before deployment;
- production deployment should continue to separate persistent database/media state from application code updates.

## Next phase

After the final Preview 5 closeout gate passes, proceed to Preview 6 — Deployment & Release Cleanup.

Primary Preview 6 targets include:

- correct v2.9 version identity across the UI, `VERSION`, release metadata, and backup naming;
- deployment/preflight consistency;
- staging/production environment documentation cleanup;
- Docker/service startup and health behavior;
- static/media handling verification;
- backup/restore and upgrade-path verification;
- release notes/checklist preparation for the v2.9 release candidate.
