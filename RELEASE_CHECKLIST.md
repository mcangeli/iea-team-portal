# ArenaLine Release Checklist

This is the canonical release-promotion gate for ArenaLine.

A release is **not ready to move to `main` or receive a stable tag** until every item below is complete.

## 1. Release identity

- [ ] `VERSION` contains the release version.
- [ ] The intended release branch is green on staging.
- [ ] `python manage.py makemigrations --check --dry-run` reports no unexpected model changes.
- [ ] `python manage.py check` / deployment preflight passes.
- [ ] The full `portal` test suite passes on staging.

## 2. Product / presentation gate

- [ ] New or materially redesigned pages follow `docs/PRODUCT_AND_UI_GUIDE.md`.
- [ ] Established ArenaLine branding, typography, components, spacing, status treatments, and navigation patterns are reused where practical.
- [ ] Desktop, tablet, and mobile behavior have been reviewed.
- [ ] Authenticated light/dark presentation is correct where applicable.
- [ ] Empty/no-data/error states are intentional and branded.
- [ ] Authorization/privacy is enforced server-side; presentation does not substitute for permissions.
- [ ] Public-facing changes continue to use explicit publication/allow-list services.

## 3. Documentation gate

The following files must be reviewed and updated **before promotion to `main`**:

- [ ] `README.md` — current version, product/workflow overview, setup/install, update, operational and troubleshooting instructions remain accurate. Keep it an overview/instructions document rather than a roadmap or full changelog.
- [ ] `CHANGELOG.md` — add/update the concise user-facing entry for the release.
- [ ] `ROADMAP.md` — released/current/future status is accurate and new product decisions are reflected.
- [ ] `ARCHITECTURE.md` — update whenever boundaries, data flow, identity/relationship structure, permissions/publication, or major subsystem ownership changed.
- [ ] `docs/releases/<version>.md` — add/update the detailed release note for substantial releases, including migrations, compatibility notes, and validation status.
- [ ] `RELEASE_NOTES.md` — preserve/update legacy detailed history where the release/process still relies on it; do not use it as a substitute for `CHANGELOG.md` going forward.
- [ ] Any README references to old release numbers, obsolete commands, or deferred work are removed.

Documentation changes belong in the release branch and travel with the same promotion as the code. Documentation should be updated as the design changes, not postponed until after feature completion.

## 4. Promotion review

- [ ] Compare release branch against `main`.
- [ ] Confirm the release branch is not behind `main`.
- [ ] Confirm no unrelated experimental work is mixed into the release.
- [ ] Confirm migrations are intentional and reversible/backup-safe where applicable.
- [ ] Confirm production-sensitive behavior was exercised on staging.

## 5. Promote

- [ ] Fast-forward `main` when possible; avoid force pushes.
- [ ] Verify `main` matches the approved release commit.
- [ ] Create the stable annotated release tag (for example `v3.1.0`) on the approved commit.
- [ ] Push the stable tag.

Production stable installs follow release tags, not simply the head of `main`.

## 6. Production update

Use the normal production updater:

```bash
cd /opt/iea-team-portal/app
./portalctl git-status
./portalctl update
./portalctl health
```

`portalctl update` fetches stable tags, creates a validated database backup, switches to the selected release, rebuilds the application, performs deployment/migration checks, starts the release, and runs health checks.

`portalctl upgrade` does **not** select a newer Git revision. It rebuilds and upgrades the revision already checked out. Use it for an already-selected checkout, not for normal stable release promotion.

## 7. Post-release verification

- [ ] `./portalctl git-status` reports the expected stable tag and release version.
- [ ] `./portalctl health` passes.
- [ ] Expected migrations are applied.
- [ ] Version shown in the UI is correct.
- [ ] Smoke-test the major workflows changed by the release.
- [ ] Record any follow-up fixes as a new patch release rather than modifying an existing stable tag.

## Rule

**Do not promote a feature/release branch until code, tests, presentation, privacy/permissions, version identity, README, changelog, roadmap, architecture, and applicable release documentation are release-ready together.**
