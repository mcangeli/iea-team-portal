# ArenaLine v2.9.0 Preview 6 — Deployment & Release Cleanup

## Purpose

Preview 6 turns the validated v2.9 application into a release candidate by aligning release identity, deployment tooling, operational documentation, backup/restore behavior, static/media handling, and staging/production readiness.

This phase should not change product behavior unless a concrete deployment defect requires it.

## Preview 6A — release identity

Implemented; awaiting staging validation.

- Root `VERSION` is now `2.9.0`.
- Django `settings.SITE_VERSION` continues to read the root `VERSION` file.
- The UI version link therefore targets the matching `v2.9.0` repository tag once that release tag exists.
- `portalctl` continues to derive `RELEASE_VERSION` from the same root `VERSION` file.
- Upgrade database backups will therefore use `pre-v2.9.0-<timestamp>.sql` instead of the stale v2.5.0 name.
- Upgrade logs will use `upgrade-v2.9.0-<timestamp>.log`.
- Deployment output will report `Starting v2.9.0...`.
- Added `portal/tests/test_v290_preview6_release_identity.py` to protect the shared version source-of-truth contract.

## Remaining Preview 6 audit

1. ~~Release identity and version plumbing.~~
2. Backup creation, naming, integrity checks, and restore/rollback documentation.
3. `portalctl preflight` / `upgrade` behavior and deployment health checks.
4. Docker Compose production/staging configuration review.
5. Static files and uploaded media persistence/serving verification.
6. Environment examples and staging-vs-production safety defaults.
7. Production/staging deployment documentation cleanup.
8. v2.9 release-candidate checklist and final regression gate.

## Guardrails

- Production and staging must remain isolated by Compose project, database volume, media volume, and environment file.
- No production data migration should be introduced only for deployment cleanup.
- Backups must be created before upgrade/migration activity and must be checked for non-empty output.
- Staging email delivery must remain disabled unless explicitly configured.
- Release tooling should derive the application version from one source of truth.
- The existing shared `.env` deployment model remains supported.
