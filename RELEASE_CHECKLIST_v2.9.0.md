# ArenaLine v2.9.0 Release Candidate Checklist

This checklist is the final production-promotion gate for ArenaLine v2.9.0.

## 1. Source and release identity

- [ ] Feature branch is current and clean.
- [ ] `VERSION` is `2.9.0`.
- [ ] Footer/UI reports v2.9.0.
- [ ] README describes ArenaLine v2.9.0 rather than an older IEA Team Portal release.
- [ ] Release tag `v2.9.0` will point to the exact validated promotion commit.

Useful checks:

```bash
./portalctl git-status
cat VERSION
git status --short
```

## 2. Application regression gate

- [ ] `python manage.py check` passes.
- [ ] `makemigrations portal --check --dry-run` reports no unintended model changes.
- [ ] Complete `portal` test suite passes.
- [ ] Preview 4 presentation/navigation tests pass.
- [ ] Preview 5 security/data-access matrix passes.
- [ ] Preview 6 deployment/release tests pass.

Final suite:

```bash
./portalctl exec web python manage.py check
./portalctl exec web python manage.py makemigrations portal --check --dry-run
./portalctl exec web python manage.py test portal
```

Known validated Preview 6B baseline: **350 tests green** before the final documentation-only RC cleanup.

## 3. Functional visual gate

Validate both light and dark mode, plus desktop and mobile widths.

- [ ] Login/product identity.
- [ ] Dashboard and role dashboards.
- [ ] People / Riders / Parents & Guardians.
- [ ] Horse Registry and Horse & Hoofprint workflows.
- [ ] Competition / Shows / Standings / History / Record Book.
- [ ] Operations / Calendar / Action Items / Lessons / Volunteer / Committees.
- [ ] Finance top-level navigation and Finance pages for an authorized account.
- [ ] Finance is absent for a Rider and unauthorized Parent account.
- [ ] Notifications / Communications.
- [ ] Manage / Users / Season Setup / Branding / Audit Log.
- [ ] Back/Cancel/destructive-action navigation behaves correctly.

## 4. Security and data-access gate

- [ ] Cross-organization direct-object probes remain 404/denied.
- [ ] Parent private rider access remains linked-family-only.
- [ ] Rider accounts have no Finance authority.
- [ ] Treasurer access is appropriately scoped.
- [ ] Points Secretary cannot gain general management/Finance authority.
- [ ] Futures/Upper Team Parent remains squad-scoped.
- [ ] Show Lead authority remains assigned-show-specific.
- [ ] Private calendar/action items and notifications remain visibility-scoped.
- [ ] CSV/file/receipt/Hoofprint download paths enforce server-side authorization.
- [ ] Archived-season mutation protections remain active.

See `docs/V2_9_PREVIEW5_CLOSEOUT.md` for the full security matrix.

## 5. Staging deployment gate

- [ ] Staging uses `arenaline-staging` Compose project.
- [ ] Staging DB volume is `arenaline-staging_postgres_data`.
- [ ] Staging media volume is `arenaline-staging_media_data`.
- [ ] Staging gateway is isolated from production (normally 127.0.0.1:8089).
- [ ] Staging `EMAIL_HOST` is blank.
- [ ] Staging uses different DB credentials and secret key from production.
- [ ] `./portalctl preflight` passes.
- [ ] `./portalctl health` passes.
- [ ] Staging restore drill from a v2.9 backup has been completed successfully.

## 6. Production pre-promotion gate

Before changing production:

- [ ] Confirm `/opt/iea-team-portal/app` is the production checkout.
- [ ] Confirm production `.env` is `/opt/iea-team-portal/.env`.
- [ ] Confirm `PORTAL_ENVIRONMENT=production`.
- [ ] Confirm `PORTAL_UPDATE_CHANNEL=stable`.
- [ ] Confirm production volume names and APP_PORT.
- [ ] Confirm `DJANGO_DEBUG=0`.
- [ ] Confirm secure cookies enabled.
- [ ] Confirm allowed host / CSRF trusted origin match the production hostname.
- [ ] Confirm SMTP settings are intentionally configured.
- [ ] Confirm there is enough disk space for a fresh DB backup and image rebuild.
- [ ] Confirm uploaded media has an independent backup/snapshot policy.

Run:

```bash
cd /opt/iea-team-portal/app
./portalctl git-status
./portalctl preflight
```

Do not promote if preflight fails.

## 7. Promotion procedure

Recommended release flow:

1. Merge/promote the validated v2.9 branch to the release commit.
2. Create tag `v2.9.0` at that exact commit.
3. Fetch the new tag on production.
4. Run:

```bash
cd /opt/iea-team-portal/app
./portalctl update v2.9.0
```

The updater must:

- create and validate a PostgreSQL backup before switching code;
- record rollback metadata;
- build the image;
- run Django deployment checks and migration preflight;
- start services;
- run the post-start ArenaLine health check.

## 8. Immediate post-promotion verification

- [ ] `./portalctl health` passes.
- [ ] `./portalctl git-status` reports v2.9.0/tagged release.
- [ ] Public HTTPS login page loads.
- [ ] Sign-in succeeds.
- [ ] Footer reports v2.9.0.
- [ ] Dashboard loads.
- [ ] One representative Rider profile loads.
- [ ] One Show/Competition page loads.
- [ ] Horse Registry loads.
- [ ] Calendar loads.
- [ ] Finance loads for an authorized account.
- [ ] Finance does not appear for a Rider.
- [ ] Static assets/images load correctly.
- [ ] Existing uploaded media remains available.
- [ ] Finance receipt media is not publicly accessible through `/media/finance/`.

Useful commands:

```bash
./portalctl health
./portalctl git-status
./portalctl ps
docker compose logs --tail=200
```

## 9. Rollback decision path

If deployment health fails or a release-critical regression is found:

1. Stop further production changes.
2. Preserve the upgrade log and backup path.
3. Determine whether the issue is code-only or involves incompatible schema/data changes.
4. For a code-only rollback, use `./portalctl rollback-code`.
5. If database restoration is required, follow `docs/BACKUP_RESTORE_ROLLBACK.md`; do not improvise a restore against a production volume.
6. Re-run `./portalctl health` after recovery.

Never assume code rollback alone makes a migrated database backward-compatible.

## 10. Release evidence to retain

- [ ] Release commit SHA.
- [ ] `v2.9.0` tag SHA.
- [ ] Final full-test result/count.
- [ ] Production preflight result.
- [ ] Backup filename and integrity-check success.
- [ ] Upgrade log filename.
- [ ] Post-start health result.
- [ ] Production visual smoke-pass result.
- [ ] Any rollback/recovery notes, if applicable.

## Release decision

ArenaLine v2.9.0 is ready for production promotion only when all applicable items above are checked and the release tag points to the exact commit that passed the final regression and staging deployment gates.
