# ArenaLine v2.9.0 Preview 6 — Deployment & Release Cleanup

## Purpose

Preview 6 turns the validated v2.9 application into a release candidate by aligning release identity, deployment tooling, operational documentation, backup/restore behavior, static/media handling, and staging/production readiness.

This phase should not change product behavior unless a concrete deployment defect requires it.

## Preview 6A — release identity

Staging validated.

- Root `VERSION` is `2.9.0`.
- Django `settings.SITE_VERSION` reads the root `VERSION` file.
- The UI version link therefore targets the matching `v2.9.0` repository tag once that release tag exists.
- `portalctl` derives `RELEASE_VERSION` from the same root `VERSION` file.
- Upgrade database backups use `pre-v2.9.0-<timestamp>.sql`.
- Upgrade logs use `upgrade-v2.9.0-<timestamp>.log`.
- Deployment output reports `Starting v2.9.0...`.
- `portal/tests/test_v290_preview6_release_identity.py` protects the shared version source-of-truth contract.

## Preview 6B — deployment health and backup verification

Staging validated with the full 350-test portal suite green.

### Backup integrity

Both regular upgrades and Git-driven updates run a lightweight integrity check immediately after `pg_dump`:

- the backup must exist and be non-empty;
- the backup must contain the PostgreSQL plain-text dump signature;
- deployment stops before build/start if the dump is empty or malformed.

This is a fast deployment-time verification and does not replace periodic restore drills.

### Post-start health verification

`portalctl` provides:

```bash
./portalctl health
```

The same health routine runs automatically after:

- `./portalctl upgrade`;
- `./portalctl update`;
- `./portalctl rollback-code`.

The health routine verifies:

1. Docker Compose service state;
2. PostgreSQL readiness with `pg_isready`;
3. Django system checks;
4. migration/schema preflight;
5. collected-static manifest presence;
6. writable media volume from the web container;
7. Caddy configuration validity.

An upgrade is not reported as complete until those checks pass.

### Existing runtime safeguards retained

- PostgreSQL Compose healthcheck;
- web startup waits for a healthy database;
- web startup runs `portal_preflight` before migrations;
- image build runs `collectstatic`;
- media uses a persistent named volume;
- Caddy blocks public `/media/finance/*` access so financial receipts remain permission-gated through Django.

Regression coverage: `portal.tests.test_v290_preview6_deployment_health`.

## Preview 6C — environment isolation and recovery runbook

Staging validated, including the documented restore/recovery checks.

### Staging / production isolation

`portal/tests/test_v290_preview6_environment_isolation.py` protects the deployment identities documented in the two environment templates.

The regression contract requires staging and production to use distinct:

- Compose project names;
- PostgreSQL volume names;
- media volume names;
- gateway ports;
- PostgreSQL database names;
- PostgreSQL users.

It also protects:

- `PORTAL_ENVIRONMENT=production` vs `staging`;
- production `stable` vs staging `preview` update channels;
- staging email disabled by default;
- staging local/private cookie/HSTS defaults vs production secure defaults;
- Compose use of environment-selected named volumes and loopback gateway binding.

### Restore and rollback runbook

`docs/BACKUP_RESTORE_ROLLBACK.md` documents:

- the distinction between code-only rollback and database restore;
- a staging-first restore drill;
- explicit backup validation;
- explicit staging-volume verification before destructive steps;
- `psql -v ON_ERROR_STOP=1` restore behavior;
- post-restore `preflight`, `health`, and application verification;
- a production rollback decision path;
- recovery evidence that should be retained for a release.

Database restoration is deliberately **not** exposed as an automatic `portalctl` shortcut because selecting the wrong database/volume is inherently destructive. The runbook keeps the target and backup path explicit.

### Media recovery boundary

The recovery documentation explicitly calls out that PostgreSQL backups do not contain uploaded files. ArenaLine media requires separate volume/filesystem backup coverage for rider photos, Coggins documents, Hoofprint horse-list uploads, and Finance receipts.

`docs/STAGING.md` links to the recovery runbook, validates dump signatures before restore, restores with `ON_ERROR_STOP=1`, uses `portalctl health` after startup, and requires a staging restore drill before v2.9 production promotion.

## Preview 6D — production operator and release-candidate gate

Implemented; awaiting final staging validation.

### Production-facing documentation cleanup

The root README now identifies the product as **ArenaLine v2.9.0** rather than the obsolete IEA Team Portal v2.0.0 release. Production setup/update guidance now references:

- the v2.9.0 release tag;
- `portalctl preflight` and `portalctl health`;
- shared version/deployment behavior;
- validated PostgreSQL backups;
- explicit database recovery documentation;
- separate uploaded-media backup requirements;
- the v2.9 architecture/module boundary;
- the v2.9 release-candidate checklist.

### Release-candidate checklist

Added `RELEASE_CHECKLIST_v2.9.0.md` as the production-promotion gate. It covers:

1. source/release identity;
2. application regression tests;
3. functional visual checks;
4. Preview 5 security/data-access guarantees;
5. staging isolation and restore-drill evidence;
6. production environment/preflight checks;
7. exact-tag production promotion;
8. immediate post-promotion smoke checks;
9. rollback decision path;
10. release evidence retention.

Production promotion should use the exact validated `v2.9.0` tag rather than an unpinned feature branch.

Regression coverage: `portal.tests.test_v290_preview6_release_candidate`.

## Preview 6 completion status

1. ~~Release identity and version plumbing.~~
2. ~~Backup restore drill instructions and rollback decision path.~~
3. ~~`portalctl` post-start deployment health checks.~~
4. ~~Docker Compose production/staging configuration review.~~
5. ~~Static manifest and uploaded-media runtime verification.~~
6. ~~Environment examples and staging-vs-production safety defaults.~~
7. ~~Production deployment documentation / operator checklist cleanup.~~
8. v2.9 release-candidate final regression gate — awaiting final validation.

## Guardrails

- Production and staging must remain isolated by Compose project, database volume, media volume, and environment file.
- No production data migration should be introduced only for deployment cleanup.
- Backups must be created before upgrade/migration activity and verified before the deployment proceeds.
- Staging email delivery must remain disabled unless explicitly configured.
- Release tooling should derive the application version from one source of truth.
- The existing shared `.env` deployment model remains supported.
- Code rollback remains separate from database restore because schema compatibility must be evaluated per release.
- Destructive recovery commands must use explicit staging/production targets rather than inferring a Docker volume from context.
- The production `v2.9.0` tag must point to the exact commit that passed the final regression, deployment-health, restore-drill, and visual gates.
