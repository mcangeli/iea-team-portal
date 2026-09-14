# ArenaLine Release Checklist

This is the canonical release-promotion gate for ArenaLine.

A release is **not ready to move to `main` or receive a stable tag** until every item below is complete.

## 1. Release identity

- [ ] `VERSION` contains the release version.
- [ ] The intended release branch is green on staging.
- [ ] `python manage.py makemigrations --check --dry-run` reports no unexpected model changes.
- [ ] `python manage.py check` / deployment preflight passes.
- [ ] The full `portal` test suite passes on staging.

## 2. Documentation gate

The following files must be reviewed and updated **before promotion to `main`**:

- [ ] `README.md` — current version, current setup/workflows, architecture summary, update instructions.
- [ ] `RELEASE_NOTES.md` or the current version-specific release note — user-visible changes, migrations, validation status.
- [ ] `ROADMAP.md` — released/current/future status is accurate.
- [ ] `ARCHITECTURE.md` — update whenever boundaries, data flow, or major subsystem ownership changed.
- [ ] Version-specific supporting docs/checklists are added or updated where appropriate.
- [ ] Any README references to old release numbers, obsolete commands, or deferred work are removed.

Documentation changes belong in the release branch and travel with the same promotion as the code.

## 3. Promotion review

- [ ] Compare release branch against `main`.
- [ ] Confirm the release branch is not behind `main`.
- [ ] Confirm no unrelated experimental/public-site work is mixed into the release.
- [ ] Confirm migrations are intentional and reversible/backup-safe where applicable.
- [ ] Confirm production-sensitive behavior was exercised on staging.

## 4. Promote

- [ ] Fast-forward `main` when possible; avoid force pushes.
- [ ] Verify `main` matches the approved release commit.
- [ ] Create the stable annotated release tag (for example `v3.0.0`) on the approved commit.
- [ ] Push the stable tag.

Production stable installs follow release tags, not simply the head of `main`.

## 5. Production update

Use the normal production updater:

```bash
cd /opt/iea-team-portal/app
./portalctl git-status
./portalctl update
./portalctl health
```

`portalctl update` fetches stable tags, creates a validated database backup, switches to the selected release, rebuilds the application, performs deployment/migration checks, starts the release, and runs health checks.

`portalctl upgrade` does **not** select a newer Git revision. It rebuilds and upgrades the revision already checked out. Use it for an already-selected checkout, not for normal stable release promotion.

## 6. Post-release verification

- [ ] `./portalctl git-status` reports the expected stable tag and release version.
- [ ] `./portalctl health` passes.
- [ ] Expected migrations are applied.
- [ ] Version shown in the UI is correct.
- [ ] Smoke-test the major workflows changed by the release.
- [ ] Record any follow-up fixes as a new patch release rather than modifying an existing stable tag.

## Rule

**Do not push a feature/release branch to `main` until code, version identity, README, release notes, roadmap, and applicable supporting documentation are all release-ready together.**
