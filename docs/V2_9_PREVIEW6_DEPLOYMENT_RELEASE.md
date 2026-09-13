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

Implemented; awaiting staging validation.

### Backup integrity

Both regular upgrades and Git-driven updates now run a lightweight integrity check immediately after `pg_dump`:

- the backup must exist and be non-empty;
- the backup must contain the PostgreSQL plain-text dump signature;
- deployment stops before build/start if the dump is empty or malformed.

This is a fast deployment-time verification and does not replace periodic restore drills.

### Post-start health verification

`portalctl` now provides:

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

## Remaining Preview 6 audit

1. ~~Release identity and version plumbing.~~
2. Backup restore drill instructions and rollback decision path.
3. ~~`portalctl` post-start deployment health checks.~~
4. Docker Compose production/staging configuration review.
5. ~~Static manifest and uploaded-media runtime verification.~~
6. Environment examples and staging-vs-production safety defaults.
7. Production/staging deployment documentation cleanup.
8. v2.9 release-candidate checklist and final regression gate.

## Guardrails

- Production and staging must remain isolated by Compose project, database volume, media volume, and environment file.
- No production data migration should be introduced only for deployment cleanup.
- Backups must be created before upgrade/migration activity and verified before the deployment proceeds.
- Staging email delivery must remain disabled unless explicitly configured.
- Release tooling should derive the application version from one source of truth.
- The existing shared `.env` deployment model remains supported.
- Code rollback remains separate from database restore because schema compatibility must be evaluated per release.
