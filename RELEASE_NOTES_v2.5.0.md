# v2.5.0 — Show Host Operations

v2.5.0 expands the IEA Team Portal from attending-show operations into a complete hosted-show operations workspace. It builds on shows marked **Hosting & attending** and reuses existing Show Planning, Courses, Schedule, Show Day, Horse/Hoofprint, Volunteer, and Finance systems rather than creating parallel data silos.

## Show Manager and Host Show Workspace

- Adds a show-scoped **Show Manager** assignment separate from Show Lead.
- Coach/Admin can assign multiple Show Managers.
- Assigned Show Managers manage active hosted-show operations without receiving unrelated team-management or transaction-level Finance authority.
- Show Leads can review Host Workspace and Command Center information without inheriting Show Manager administration rights.
- Adds Host Shows index, Host Show Workspace, Show Manager Dashboard, personnel roster, host readiness, and operational planning fields.
- Integrates Show Manager into the shared role-dashboard selector.

## Hosting budget

- Reuses the existing Finance hosting-budget model.
- Surfaces budgeted expenses, actual expenses, remaining budget, pending reimbursements, and hosting income where applicable.
- Show Managers receive operational totals without automatically receiving detailed Finance access.
- Hosting budget remains visible before the Host Plan is initialized.

## Show-Day Command Center

- Adds readiness checkpoints, owners, deadlines, completion/waiver states, and notes.
- Adds duty assignments for gate, ring, warm-up, check-in, parking, hospitality, horse operations, runners/communications, setup/teardown, and other duties.
- Supports planned, checked-in, on-duty, handed-off, and complete duty states.
- Host duties are operational staffing only and never create, satisfy, reduce, or alter regular season volunteer-hour requirements or `VolunteerLog`.

## Family communication

- Adds controlled Host Family Information publication for authenticated same-team users.
- Nothing becomes family-visible merely because it exists in Host Show Operations.
- Show Manager/Coach explicitly publishes selected sections.
- Publishable sections include Arrival & Check-in, Parking, Warm-up/Schooling, Ring Operations, Hospitality, Emergency Information, Prize List/Schedule links, and Rider & Family Notes.
- Internal host notes, personnel, readiness checkpoints, duties/handoffs, Command Center data, and budget information are never included.
- Existing Show Day update audience filtering is reused.
- Unpublishing removes family access without deleting the host plan.

## Lifecycle and history

- `Show.status`, not calendar date, controls the operational/archive boundary.
- Complete/Cancelled hosted shows leave the active Show Manager Dashboard and move into Hosted Show History.
- Historical Show Manager assignments remain intact for review.
- Show Managers retain read-only historical Host Workspace/Command Center access.
- Coach/Admin retain correction authority on archived host records.
- Host Workspace adds **Mark Show Complete** and **Reopen Show** controls for Coach/Admin, with an explicit confirmation before completion.
- Reopening returns the show to Entries submitted and restores active operations.
- Published family information remains available after completion until explicitly unpublished.

## Presentation and hardening

- Polishes host workflows for mobile, light/dark modes, empty states, and partially configured shows.
- Distinguishes an unstarted Host Plan from a meaningful 0% readiness state.
- Production 403/404/500 pages now honor saved/system theme and include a safe theme toggle.
- Permission checks occur before helper code can create Host Operations records on unauthorized requests.
- Adds regression coverage for role combinations, multiple/inactive managers, privacy, family publication, lifecycle, presentation, and lifecycle controls.
- Final stabilization also corrected reimbursement form team binding discovered by the full regression suite; the temporary compatibility shim is scheduled for normalization in v2.9.x.

## Data migrations

- `0045_v250_host_show_operations.py`
- `0046_v250_host_show_duties.py`
- `0047_v250_host_family_publication.py`

No schema change is required by the final lifecycle-control/stabilization work beyond `0047`.

## Validation

Release validation completed successfully on the final v2.5.0 release candidate:

- Django system check reported no issues.
- `makemigrations portal --check --dry-run` reported no model drift.
- Migrations `0045`, `0046`, and `0047` were confirmed applied.
- Focused regression suites passed after stabilization fixes.
- The complete `portal.tests` regression suite completed with no failures or errors.
- Final branch comparison against production `main` is clean and mergeable with no unexpected migrations or debug files.

v2.5.0 is release-ready pending explicit production merge approval.
