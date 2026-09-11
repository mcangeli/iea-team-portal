# v2.1.5 Release Validation Checklist

Use this checklist before promoting `feature/v2.1.5-post-show-horse-history` to production `main`.

## 1. Upgrade / migration validation

- [x] Deploy the latest v2.1.5 feature branch to the test server.
- [x] Run `./portalctl upgrade` successfully.
- [x] Apply `0044_v215_post_show_horse_history.py`.
- [x] Run `python manage.py check` with no issues.
- [x] Run `python manage.py makemigrations portal --check --dry-run` and confirm no pending model changes.
- [x] Confirm application services are healthy after upgrade.

## 2. Automated regression validation

- [x] Run `portal.tests.test_v215_post_show_horse_history`.
- [x] Focused v2.1.5 suite passes 4/4.
- [x] Run the complete `portal.tests` regression suite.
- [x] Full regression suite passes on the test server.

## 3. Post-show horse-history workflow

- [x] Open a show with registry horses and leased/show-specific horses.
- [x] Generate a post-show horse-history draft.
- [x] Confirm registry and leased/show-specific horses are represented.
- [x] Edit whether each horse was actually used.
- [x] Edit whether each horse counted toward the team contribution.
- [x] Confirm show-class coverage is retained as snapshot data.
- [x] Add post-show notes.
- [x] Reconcile a leased/show-specific placeholder to an actual Horse Registry horse.
- [x] Finalize the post-show history.
- [x] Confirm finalized history is read-only in the normal workflow.

## 4. Historical reporting

- [x] Open Team Record Book and confirm Horse Legacy section renders.
- [x] Confirm Horse of the Day totals are shown with Full Day/Morning/Afternoon distinctions.
- [x] Confirm show appearances and class coverage render.
- [x] Open Season Review and confirm Season Horse History renders.
- [x] Confirm finalized post-show snapshots are used for reconciled historical participation.
- [x] Confirm older shows without finalized post-show history still use legacy assignment fallback.

## 5. Permissions / data integrity

- [x] Coach/Admin can generate, edit, reconcile, and finalize post-show horse history.
- [x] Non-management users cannot modify post-show history.
- [x] Reconciled registry horses must belong to the same team as the show.
- [x] Finalized history cannot be rebuilt through the normal service workflow.
- [x] Finalization requires at least one horse-history record.

## 6. Presentation / usability

- [x] Post-show History is reachable from Show Horses.
- [x] Draft/final state is clear to the user.
- [x] Actually Used and Counted as Contribution fields are usable in live testing.
- [x] Record Book horse history presentation works with existing rider/team records.
- [x] Season Review horse history presentation works with existing season content.

## 7. Release documentation

- [x] `VERSION` is `2.1.5`.
- [x] `RELEASE_NOTES.md` describes final v2.1.5 behavior and validation.
- [x] `ROADMAP.md` marks 2.1.5 stabilization complete and points next to 2.5.x Show Host Operations.
- [x] `RELEASE_CHECKLIST_v2.1.5.md` added.
- [ ] Review final branch diff against `main`.
- [ ] Mark PR #6 ready for review.
- [ ] Merge only after explicit release approval.

## Release summary

v2.1.5 closes the 2.1.x horse/show-operations arc by preserving the final historical horse record after a show. It connects readiness and show-day planning to durable horse participation, contribution, reconciliation, Horse of the Day, Record Book, and season-history reporting.
