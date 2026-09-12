# v2.5.0 Release Validation Checklist

Use this checklist before promoting `feature/v2.5.0-show-host-operations` to production `main`.

## 1. Upgrade and migration validation

- [ ] Back up the database through the normal `portalctl` upgrade workflow.
- [ ] Deploy the latest feature-branch commit with the explicit-ref workaround.
- [ ] Run `./portalctl upgrade` successfully.
- [ ] Confirm migrations are applied in order after released `0044_v215_post_show_horse_history`:
  - [ ] `0045_v250_host_show_operations`
  - [ ] `0046_v250_host_show_duties`
  - [ ] `0047_v250_host_family_publication`
- [ ] Run `docker compose exec web python manage.py showmigrations portal` and confirm 0045–0047 are checked.
- [ ] Run `docker compose exec web python manage.py check` with no issues.
- [ ] Run `docker compose exec web python manage.py makemigrations portal --check --dry-run` and confirm no model drift.
- [ ] Run `./portalctl git-status` and confirm the expected feature commit.
- [ ] Run `./portalctl ps` and confirm services are healthy.

## 2. Full regression suite

- [ ] Run the complete portal test suite:

```bash
cd /opt/iea-team-portal/app
docker compose exec web python manage.py test portal.tests
```

- [ ] Confirm the full suite exits successfully with no failures/errors.
- [ ] Re-run any failing module independently before changing code so the failure is reproducible.

## 3. Host Show Workspace

- [ ] Hosted show appears in Host Shows.
- [ ] Non-hosted show cannot use Host Show Workspace.
- [ ] Host plan can be created and edited.
- [ ] Hosting budget appears even before Host Operations is initialized.
- [ ] Existing hosting Finance totals match the Host Workspace summary.
- [ ] Show Manager assignment/removal works for Coach/Admin.
- [ ] Multiple active Show Managers are supported.
- [ ] Personnel add/edit/remove works.
- [ ] Empty/partial host-plan states are understandable.

## 4. Role and permission matrix

- [ ] Admin has full host management and lifecycle authority.
- [ ] Coach has full host management and lifecycle authority.
- [ ] Assigned Show Manager manages active host operations for that show.
- [ ] Inactive/removed Show Manager loses management access.
- [ ] Show Lead can review Host Workspace/Command Center but cannot administer host operations solely because of Show Lead assignment.
- [ ] Parent/Rider cannot access private Host Workspace or Command Center.
- [ ] Mixed Show Manager + Show Lead role behaves as Show Manager for active host operations.
- [ ] Unauthorized POST/GET requests do not create Host Operations records as a side effect.
- [ ] Detailed Finance access remains governed by existing Finance permissions.

## 5. Show-Day Command Center

- [ ] Add/edit/complete readiness checkpoint.
- [ ] Add/edit duty assignment.
- [ ] Duty can move through Checked in, On duty, Handed off, and Complete.
- [ ] Handoff notes/relief are retained.
- [ ] Show Lead view-only behavior is correct.
- [ ] Empty Command Center explains when Host Plan has not been started.
- [ ] Host duty operations do not create or alter `VolunteerLog` or season volunteer-hour totals.

## 6. Family publication and privacy

- [ ] Family Host Information is inaccessible before explicit publication.
- [ ] Publish only selected sections and verify only those sections appear.
- [ ] Rider/Parent can access published information for their team.
- [ ] Internal host notes never appear.
- [ ] Personnel/staff records never appear.
- [ ] Hosting budget/Finance data never appears.
- [ ] Readiness checkpoints never appear.
- [ ] Duties/handoffs/Command Center data never appear.
- [ ] Existing Show Day updates retain their normal audience filtering.
- [ ] Unpublishing immediately removes family access without deleting the host plan.
- [ ] Published page with zero selected sections explains the state clearly.

## 7. Lifecycle and history

- [ ] Past-dated but non-Complete/Cancelled show remains operational.
- [ ] Coach/Admin can use **Mark Show Complete** from Host Workspace.
- [ ] Completion confirmation clearly explains the archive/read-only effect.
- [ ] Completed show leaves the active Show Manager Dashboard.
- [ ] Completed show appears in Hosted Show History.
- [ ] Show Manager retains historical review access but cannot edit host plan, personnel, readiness, duties, or publication settings.
- [ ] Coach/Admin retains correction access to archived host records.
- [ ] Already-published family information remains published after completion.
- [ ] Coach/Admin can **Reopen Show** and the show returns to Entries submitted / active operations.
- [ ] Cancelled hosted shows follow the same archived/read-only behavior.
- [ ] Unrelated users cannot use archived routes as a permission backdoor.

## 8. Presentation

Check desktop and phone-sized layouts in light and dark modes:

- [ ] Show Manager Dashboard and workspace selector.
- [ ] Host Shows active/history sections.
- [ ] Host Show Workspace.
- [ ] Command Center tables/actions.
- [ ] Publish Family Show Info form.
- [ ] Host Family Information page.
- [ ] Empty and partially configured host states.
- [ ] 403 page follows saved/system theme.
- [ ] 404 page follows saved/system theme.
- [ ] 500 page follows saved/system theme.

## 9. Release documentation and branch review

- [ ] `VERSION` is `2.5.0`.
- [ ] `ROADMAP.md` marks v2.5.0 feature-complete / release stabilization and accurately records 2.9.x cleanup.
- [ ] v2.5.0 release notes describe the final behavior and privacy model.
- [ ] PR title/body no longer describe the branch as only Preview 4.
- [ ] Review the complete diff against production `main`.
- [ ] Confirm no accidental debug output, experimental files, or unplanned migration exists.
- [ ] Confirm PR remains mergeable after final `main` comparison.

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
- Fix `portalctl` explicit branch/ref/tag behavior so feature deployments no longer require detached `FETCH_HEAD` checkout.
