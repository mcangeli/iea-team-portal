# v2.5.0 Release Validation Checklist

Use this checklist before promoting `feature/v2.5.0-show-host-operations` to production `main`.

## 1. Upgrade and migration validation

- [x] Back up the database through the normal `portalctl` upgrade workflow.
- [x] Deploy the latest feature-branch commit with the explicit-ref workaround.
- [x] Run `./portalctl upgrade` successfully.
- [x] Confirm migrations are applied in order after released `0044_v215_post_show_horse_history`:
  - [x] `0045_v250_host_show_operations`
  - [x] `0046_v250_host_show_duties`
  - [x] `0047_v250_host_family_publication`
- [x] Run `docker compose exec web python manage.py showmigrations portal` and confirm 0045–0047 are checked.
- [x] Run `docker compose exec web python manage.py check` with no issues.
- [x] Run `docker compose exec web python manage.py makemigrations portal --check --dry-run` and confirm no model drift.
- [x] Run `./portalctl git-status` and confirm the expected feature commit.
- [x] Run `./portalctl ps` and confirm services are healthy.

## 2. Full regression suite

- [x] Run the complete portal test suite:

```bash
cd /opt/iea-team-portal/app
docker compose exec web python manage.py test portal.tests
```

- [x] Confirm the full suite exits successfully with no failures/errors.
- [x] Re-run any failing module independently before changing code so the failure is reproducible.

## 3. Host Show Workspace

- [x] Hosted show appears in Host Shows.
- [x] Non-hosted show cannot use Host Show Workspace.
- [x] Host plan can be created and edited.
- [x] Hosting budget appears even before Host Operations is initialized.
- [x] Existing hosting Finance totals match the Host Workspace summary.
- [x] Show Manager assignment/removal works for Coach/Admin.
- [x] Multiple active Show Managers are supported.
- [x] Personnel add/edit/remove works.
- [x] Empty/partial host-plan states are understandable.

## 4. Role and permission matrix

- [x] Admin has full host management and lifecycle authority.
- [x] Coach has full host management and lifecycle authority.
- [x] Assigned Show Manager manages active host operations for that show.
- [x] Inactive/removed Show Manager loses management access.
- [x] Show Lead can review Host Workspace/Command Center but cannot administer host operations solely because of Show Lead assignment.
- [x] Parent/Rider cannot access private Host Workspace or Command Center.
- [x] Mixed Show Manager + Show Lead role behaves as Show Manager for active host operations.
- [x] Unauthorized POST/GET requests do not create Host Operations records as a side effect.
- [x] Detailed Finance access remains governed by existing Finance permissions.

## 5. Show-Day Command Center

- [x] Add/edit/complete readiness checkpoint.
- [x] Add/edit duty assignment.
- [x] Duty can move through Checked in, On duty, Handed off, and Complete.
- [x] Handoff notes/relief are retained.
- [x] Show Lead view-only behavior is correct.
- [x] Empty Command Center explains when Host Plan has not been started.
- [x] Host duty operations do not create or alter `VolunteerLog` or season volunteer-hour totals.

## 6. Family publication and privacy

- [x] Family Host Information is inaccessible before explicit publication.
- [x] Publish only selected sections and verify only those sections appear.
- [x] Rider/Parent can access published information for their team.
- [x] Internal host notes never appear.
- [x] Personnel/staff records never appear.
- [x] Hosting budget/Finance data never appears.
- [x] Readiness checkpoints never appear.
- [x] Duties/handoffs/Command Center data never appear.
- [x] Existing Show Day updates retain their normal audience filtering.
- [x] Unpublishing immediately removes family access without deleting the host plan.
- [x] Published page with zero selected sections explains the state clearly.

## 7. Lifecycle and history

- [x] Past-dated but non-Complete/Cancelled show remains operational.
- [x] Coach/Admin can use **Mark Show Complete** from Host Workspace.
- [x] Completion confirmation clearly explains the archive/read-only effect.
- [x] Completed show leaves the active Show Manager Dashboard.
- [x] Completed show appears in Hosted Show History.
- [x] Show Manager retains historical review access but cannot edit host plan, personnel, readiness, duties, or publication settings.
- [x] Coach/Admin retains correction access to archived host records.
- [x] Already-published family information remains published after completion.
- [x] Coach/Admin can **Reopen Show** and the show returns to Entries submitted / active operations.
- [x] Cancelled hosted shows follow the same archived/read-only behavior.
- [x] Unrelated users cannot use archived routes as a permission backdoor.

## 8. Presentation

Check desktop and phone-sized layouts in light and dark modes:

- [x] Show Manager Dashboard and workspace selector.
- [x] Host Shows active/history sections.
- [x] Host Show Workspace.
- [x] Command Center tables/actions.
- [x] Publish Family Show Info form.
- [x] Host Family Information page.
- [x] Empty and partially configured host states.
- [x] 403 page follows saved/system theme.
- [x] 404 page follows saved/system theme.
- [x] 500 page follows saved/system theme.

## 9. Release documentation and branch review

- [x] `VERSION` is `2.5.0`.
- [x] `ROADMAP.md` marks v2.5.0 feature-complete / release stabilization and accurately records 2.9.x cleanup.
- [x] v2.5.0 release notes describe the final behavior and privacy model.
- [x] PR title/body no longer describe the branch as only Preview 4.
- [x] Review the complete diff against production `main`.
- [x] Confirm no accidental debug output, experimental files, or unplanned migration exists.
- [x] Confirm PR remains mergeable after final `main` comparison.

## 10. Production promotion

Do not merge until the release checklist and full regression suite are clean and explicit release approval has been given.

After approval:

```bash
cd /opt/iea-team-portal/app
git checkout main
git pull origin main
./portalctl upgrade
./portalctl git-status
./portalctl ps
```

Then perform a production smoke test as Admin/Coach and Show Manager.

## Deferred to v2.9.x

- Integrate Show Manager workspace discovery directly into the dashboard architecture and remove `dashboard_workspace_extensions.py`.
- Remove the v2.1.4 `ShowPlanningItem.owner_id` compatibility shim through the planned Show Day architecture cleanup.
- Normalize remaining dynamic model additions and oversized view modules.
- Replace the temporary reimbursement-form team-binding compatibility shim with the normalized finance-form architecture.
- Fix `portalctl` explicit branch/ref/tag behavior so feature deployments no longer require detached `FETCH_HEAD` checkout.
