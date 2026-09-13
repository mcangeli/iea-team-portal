# ArenaLine v2.9.0 Preview 6 Closeout

## Status

Preview 6 is complete and staging validated.

Final validation on the feature branch:

- Django system check: passed
- migration dry-run check: passed
- deployment health checks: passed
- staging restore drill: passed
- final portal test suite: **359 tests passed**
- final visual smoke pass: passed

## What Preview 6 closed

- release/version identity aligned to `2.9.0` across Django, UI, backups, logs, and deployment tooling;
- upgrade and Git-update backups verified before deployment proceeds;
- post-start `portalctl health` verifies database, Django, migrations, static assets, media volume, and gateway configuration;
- production/staging environment isolation protected by regression tests;
- staging email remains disabled by default;
- backup/restore and rollback decision paths documented and staging-restored successfully;
- production README updated for ArenaLine v2.9.0 and current deployment commands;
- v2.9 release-candidate checklist added.

## Release-candidate decision

The validated feature branch is release-candidate ready.

Promotion should preserve the exact validated commit. The release process is:

1. merge the validated feature branch into `main` without introducing additional functional changes;
2. verify the resulting `main` commit is the intended validated release content;
3. create tag `v2.9.0` at that exact release commit;
4. follow `RELEASE_CHECKLIST_v2.9.0.md` for production preflight, backup, update, health verification, and smoke checks;
5. retain the production backup and deployment log as release evidence.

Any code change after this closeout invalidates the 359-test RC result and requires the affected regression checks plus the full `portal` suite again.

## Roadmap status

- Preview 1 — Architecture audit: complete
- Preview 2 — ArenaLine identity: complete
- Preview 3 — Platform/module preparation: complete
- Preview 4 — UI consolidation/navigation: complete
- Preview 5 — Security/data-access audit: complete
- Preview 6 — Deployment/release cleanup: complete

ArenaLine v2.9.0 is ready for release promotion.
