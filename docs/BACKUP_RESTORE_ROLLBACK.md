# ArenaLine Backup, Restore, and Rollback Runbook

## Purpose

This runbook defines the v2.9 operational recovery path for ArenaLine. It is intentionally explicit: database restoration is destructive, so ArenaLine does not expose it as an automatic `portalctl` shortcut.

Use this document for staging recovery drills and for production incident planning.

## What ArenaLine backs up automatically

`./portalctl upgrade` creates a PostgreSQL plain-text dump before build, deployment checks, migrations, or application startup proceed.

The backup is stored outside the Git checkout under the installation root:

```text
<installation-root>/backups/pre-v2.9.0-YYYYMMDD-HHMMSS.sql
```

The upgrade stops if the file is empty or does not contain the expected PostgreSQL dump signature.

Git-driven `./portalctl update` also creates a database backup and records rollback metadata in:

```text
<installation-root>/.portal-last-update
```

That metadata records the previous Git commit/ref, target ref, associated backup path, and update timestamp.

## Important distinction: code rollback vs database restore

`./portalctl rollback-code` changes application code only. It does **not** restore the database.

Use code-only rollback when all of the following are true:

- the problem is application code or presentation behavior;
- migrations applied by the newer version are backward compatible with the older code;
- no data migration or schema change makes the previous version unsafe.

Use database restore when any of the following are true:

- the release changed data in a way that must be undone;
- a migration is not backward compatible;
- the database is damaged or inconsistent;
- the operator explicitly needs the exact pre-upgrade database state.

When uncertain, do not start an older application against a newer schema. Preserve the current database, inspect the migration path, and restore into staging first.

## Staging restore drill

A restore drill should be performed against the isolated staging installation, never against production as the first test.

### 1. Confirm you are in staging

```bash
cd /opt/arenaline-staging/app
pwd
```

The path must begin with:

```text
/opt/arenaline-staging
```

Confirm the configured resources:

```bash
./portalctl config --volumes
./portalctl config --services
```

Expected staging identities include:

```text
arenaline-staging_postgres_data
arenaline-staging_media_data
```

Do not continue if a production volume name appears.

### 2. Select and validate a backup

Example:

```bash
BACKUP=/opt/arenaline-staging/backups/pre-v2.9.0-YYYYMMDD-HHMMSS.sql

test -s "$BACKUP"
grep -m1 '^-- PostgreSQL database dump' "$BACKUP"
```

Keep the path explicit. Do not select a backup using a wildcard in a production recovery procedure.

### 3. Stop staging application traffic

```bash
./portalctl stop web gateway
```

Leave the database service available for inspection until the replacement step.

### 4. Recreate only the staging database volume

```bash
./portalctl down

docker volume rm arenaline-staging_postgres_data

./portalctl up -d db
```

Never remove `iea-team-portal_postgres_data` during a staging drill.

### 5. Restore the dump

```bash
./portalctl exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB"' < "$BACKUP"
```

`ON_ERROR_STOP=1` makes `psql` stop on the first SQL error rather than silently continuing through a partial restore.

### 6. Run preflight and start ArenaLine

```bash
./portalctl preflight
./portalctl up -d --build
./portalctl health
```

Then run the application regression suite appropriate to the release candidate.

### 7. Verify the restored data

At minimum verify:

- expected organization and season are present;
- representative Riders and Horses are present;
- a representative Show and Hoofprint record loads;
- Finance totals/recent transactions match the expected backup point;
- uploaded media is available;
- `./portalctl health` passes.

The database backup does not contain uploaded media. Media recovery is a separate volume/filesystem concern.

## Media recovery

ArenaLine stores uploaded media in the configured Docker media volume. Database backups do not include those files.

For staging refreshes, production media may be copied read-only from the production volume into the staging media volume as described in `docs/STAGING.md`.

For production disaster recovery, the media volume requires its own host-level/container-volume backup strategy. A valid PostgreSQL dump alone is not a complete backup of rider photos, Coggins documents, Hoofprint horse-list uploads, or Finance receipt files.

Finance media remains protected from direct Caddy `/media/finance/*` serving and must continue to be downloaded only through permission-checked Django views.

## Production rollback decision path

When a production deployment fails:

1. Run `./portalctl health` and capture the failing check.
2. Preserve the upgrade log and the pre-upgrade database backup.
3. Determine whether the failure occurred before or after migrations/startup.
4. If the current code can be repaired forward safely, prefer a forward fix.
5. If code rollback is safe against the current schema, use `./portalctl rollback-code`.
6. If the older code is not safe against the current schema/data, restore the matching pre-upgrade database backup before starting the older release.
7. After any rollback or restore, run `./portalctl health` and the release smoke tests.

Never delete the pre-upgrade backup until the release has been accepted in production.

## Recovery evidence to retain

For a production release keep, at minimum:

- the exact Git release/tag or commit;
- the upgrade log;
- the pre-upgrade database backup;
- output from `./portalctl health`;
- the final migration state;
- the operator/date of deployment;
- any rollback or restore actions performed.

## v2.9 release-candidate expectation

Before v2.9 production promotion, perform at least one successful staging database restore drill from a valid ArenaLine backup and confirm the restored staging instance passes `./portalctl health` and the release regression tests.
