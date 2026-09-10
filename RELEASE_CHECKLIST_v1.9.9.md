# IEA Team Portal v1.9.9 Final Release Checklist

## Release identity
- [x] `VERSION` is `1.9.9`.
- [x] README identifies v1.9.9 as the current release.
- [x] v1.9.9 release notes are consolidated into final-release format.
- [x] No v1.9.9 section is marked in progress.
- [x] Final ZIP must extract to `iea-team-portal-v1.9.9/`.
- [ ] Publish Git tag `v1.9.9` so the footer documentation link resolves to the matching release.

## Functional stabilization
- [x] Archived-season mutation protection is consistent across legacy show, class, entry, lesson, availability, volunteer, and committee routes.
- [x] Historical correction workflows remain available where explicitly intended.
- [x] Rider creation is transactional.
- [x] Key family-finance model validation errors return to forms instead of becoming avoidable 500 errors.
- [x] Empty/duplicate guardian linking is handled gracefully.
- [x] Qualification, Season Review/Rider History, and Record Book query-heavy paths were reduced.
- [x] Finance-linked Shows are protected from deletion.
- [x] Historical imports do not mutate metadata/status on existing non-historical Shows.

## Production readiness
- [x] Production settings fail fast for missing/unsafe `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, and `DJANGO_ALLOWED_HOSTS`.
- [x] Docker build uses explicit build-only development values for `collectstatic`.
- [x] `portalctl preflight` validates environment, Docker/Compose, Django deployment checks, schema preflight, and migration plan.
- [x] `portalctl upgrade` preserves pre-upgrade database backup.
- [x] Upgrade logs are written to the persistent `logs/` directory without printing secrets.
- [x] No new database migration is required for v1.9.9.

## Static release validation
- [x] Python AST parse for `portal` and `config`.
- [x] Python bytecode compilation for `portal` and `config`.
- [x] `bash -n portalctl`.
- [x] URL-to-view consistency.
- [x] Template named-route consistency.
- [x] v1.9.9 feature assertions.
- [x] ZIP integrity and top-level-folder validation.

## Runtime acceptance
- [x] Preview 1 accepted by user in live environment.
- [x] Preview 2 accepted by user in live environment.
- [x] Preview 3 accepted by user in live environment.
- [x] Preview 4 accepted by user in live environment.
- [ ] Final package upgrade/install remains final acceptance check.

## v2 handoff
- [x] Major feature expansion intentionally excluded from v1.9.9.
- [x] `portal/views.py` modularization/refactor remains the first v2.x architecture task.
