## v2.0.0 — Preview 2: Git Installation & Updates

Preview 2 introduces a Git-backed production deployment workflow while retaining compatibility with the existing Docker Compose project, persistent `.env`, database volume, media volume, backups, and logs.

### Git deployment
- Added `install.sh` for creating a permanent Git checkout at `/opt/iea-team-portal/app`.
- Existing `/opt/iea-team-portal/.env` is reused during migration from the ZIP/release-folder layout.
- Added `.env.example` for new installations; the installer never invents production secrets.
- Added `./portalctl git-status` to report repository, installed tag/ref, commit, update channel, and working-tree cleanliness.
- Added `./portalctl update`:
  - requires a clean Git working tree;
  - fetches repository changes and tags;
  - defaults to the newest stable version tag instead of following `main`;
  - supports an explicit tag/ref argument for preview testing;
  - creates a PostgreSQL backup before changing application code;
  - records previous commit/ref and backup metadata;
  - checks out the selected release in detached-tag mode;
  - rebuilds the application;
  - runs Django deployment checks;
  - runs migration/schema preflight;
  - prints the migration plan;
  - restarts the application;
  - writes a persistent update log.
- Added `PORTAL_UPDATE_CHANNEL=stable` with an optional `preview` channel.
- Added guarded `./portalctl rollback-code` using the previous commit recorded before the last update.
- Database rollback is intentionally not automatic; the command identifies the associated backup and warns when database restoration may be required.
- Git updates stop when local source changes are present rather than overwriting them.

### Compatibility
- Existing `./portalctl preflight`, `upgrade`, Compose commands, shared `.env`, backup path, logging path, and named Docker volumes remain supported.
- Existing ZIP installations can continue to run during the transition.
- Preview 1's modular view architecture remains unchanged.
- No database migration is required for Preview 2.

## v2.0.0 — Preview 1: View Architecture Refactor

Preview 1 starts the v2 branch with a behavior-preserving refactor of the portal view layer.

### Architecture
- Replaced the former ~354 KB monolithic `portal/views.py` implementation with a thin compatibility namespace.
- Moved public view implementations into domain modules under `portal/view_modules/`:
  - roster;
  - communications;
  - competitions;
  - show day;
  - scoring;
  - show planning;
  - lessons;
  - history;
  - administration;
  - core finance;
  - family finance;
  - fundraising;
  - finance reports;
  - show finance.
- Moved domain-specific private helpers beside their corresponding view modules.
- Retained genuinely cross-domain permissions, audit, and query helpers in `portal/view_modules/common.py`.
- Preserved all existing `portal.views.<name>` symbols so `portal/urls.py` does not need a routing rewrite in the same preview.
- Preserved all 180 URL-referenced view callables from v1.9.9.
- Added regression coverage that verifies representative compatibility exports and their new implementation modules.

### Scope
- No intended user-facing behavior changes.
- No database migration is required.
- Git-based installation/update tooling remains planned for Preview 2.
- Role-specific dashboards, rider lifecycle cleanup, and calendar redesign remain later v2.0 previews.
- Horse/Hoofprint management remains targeted for the v2.1 workstream after the v2.0 foundation is stable.

# Release Notes

Version-by-version changes for IEA Team Portal. For installation, configuration, and day-to-day usage, see `README.md`.

## v1.9.9 — Pre-v2 Stabilization

v1.9.9 is the final stabilization release before the v2 architecture work begins. It focuses on reliability, permission consistency, data integrity, performance, and production-readiness rather than adding major new product features.

### Permissions & archive protection
- Hardened legacy season-scoped mutation routes so archived seasons cannot be modified through older direct URLs.
- Archive protection now covers:
  - show edit/delete;
  - show class add/edit/delete;
  - rider entry add/edit/delete;
  - regular-season points-rider changes;
  - SeasonClass editing;
  - lesson group/lesson/attendance editing;
  - show availability changes;
  - volunteer-log review;
  - historical committee-assignment editing.
- These workflows now consistently use the same `_ensure_season_open()` protection already used by newer show-day features.
- Historical-data correction workflows introduced in v1.9.8 remain intentionally available for archived seasons.
- Archive and reopen authority remains Administrator-only.
- Reopening a season still does not automatically make it the active season.

### Error handling and partial-save prevention
- Rider creation is now transactional so a failed season-membership creation cannot leave behind a partially created Rider.
- Rider creation converts model validation failures into visible form errors instead of avoidable server errors.
- Added duplicate-safe handling around rider creation and several family-finance create workflows.
- Added reusable form/model validation handling so `full_clean()` failures can be surfaced back on the submitted form.
- Applied graceful validation handling to:
  - family charges;
  - family credits/adjustments;
  - service-agreement credits;
  - external financial-assistance awards.
- Empty parent/guardian link submissions now return a useful validation message.
- Repeated parent/guardian link submissions remain idempotent rather than creating duplicate relationships.
- Record Book and Season Review retain explicit no-data states for empty historical seasons.

### Performance and data integrity
- Individual qualification totals are grouped in a single season-level result query instead of recalculating totals rider-by-rider/class-by-class.
- Season Review and Rider History summary metrics now batch membership/classes, class points/wins, distinct shows, lesson attendance, and approved volunteer hours.
- Team Record Book totals now use grouped result aggregates instead of nested season → rider → class query loops.
- Show deletion now protects linked financial history. A Show cannot be deleted while referenced by:
  - financial ledger transactions;
  - family charges;
  - reimbursement requests;
  - show transaction allocations;
  - itemized show budget lines.
- The user receives a clear message identifying linked finance records rather than silently discarding or detaching finance history.
- Historical CSV/AccessIEA imports no longer rewrite status or shared metadata on an existing non-historical operational Show.
- Shows created by the historical import workflow continue to receive historical metadata and Complete status.

### Production readiness and upgrade diagnostics
- Production configuration now fails fast when critical environment values are missing or still use unsafe placeholders:
  - `DJANGO_SECRET_KEY` must be present and at least 32 characters;
  - `POSTGRES_PASSWORD` must be present and may not be `change-me`;
  - `DJANGO_ALLOWED_HOSTS` must contain at least one hostname.
- Development/debug mode retains local fallbacks for intentional development use.
- Docker `collectstatic` uses explicit build-only development values so production secrets are not required or baked into the image during build.
- `portalctl preflight` validates the shared `.env`, Docker, and Docker Compose before application checks.
- Both standalone preflight and upgrade run Django deployment checks, migration-schema preflight, and print the migration plan.
- Migration preflight reports pending migrations without applying them.
- `portalctl upgrade` preserves backup-before-upgrade behavior and writes a timestamped operator log under the persistent `logs/` directory.
- Upgrade logs include release/version information, Docker/Compose versions, backup/build/preflight/startup output, and final backup/log locations without printing secret values.

### Release notes
- No new database migration is required for v1.9.9.
- v1.9.9 intentionally closes the 1.9.x stabilization cycle.
- The large `portal/views.py` modularization/refactor remains the first architecture task for v2.x before major v2 feature work.

## v1.9.8 — Historical Data & Season Management

v1.9.8 adds a complete historical-season workflow centered on real AccessIEA Rider Performance exports. Managers can build prior-season roster/class structure, import results safely, correct rider-specific history, and archive seasons with a readiness review while keeping normal operational protections in place.

### Historical season workspace
- Added a manager-facing **Historical data** workspace for every season.
- Season Archive shows rider, show, and result counts at a glance.
- Added direct rider-by-rider historical result entry from the selected season.
- Historical entry uses the same SeasonMembership, SeasonClass, ShowEntry, and ShowResult structure as normal operations.
- Historical result entry remains available for archived seasons without reopening normal operational workflows.
- Rebuilt the Season Review historical-season presentation and added clearer season lifecycle messaging.
- Archive and reopen actions are audited and idempotent.
- Reopening an archived season for corrections does not automatically make it the active season.

### AccessIEA Rider Performance import
- Added a safe three-step bulk import workflow:
  1. upload CSV;
  2. preview and validate;
  3. explicitly commit.
- AccessIEA Rider Performance exports are detected automatically.
- Detection tolerates capitalization, spacing, and UTF-8 BOM differences in AccessIEA fixed headers.
- AccessIEA `#IEA` member number is the primary rider match; exact legal/preferred name is the fallback.
- Dated show columns are converted into historical shows/results.
- Region, Zone, and National Finals naming is recognized; Team and Individual finals columns become separate competition tracks on the same finals show.
- Blank AccessIEA show cells are ignored; a populated `0` is preserved as a real zero-point result.
- AccessIEA `Total Rider Points` and `# of Shows` are cross-checked and surfaced as warnings when they do not reconcile with the populated show columns.
- Existing matching results are previewed as duplicates and skipped instead of overwritten.
- Duplicate rows and conflicting show metadata are blocked.
- Out-of-season show dates are warnings rather than silently changed.
- Imports are atomic and may be committed against archived seasons without reopening them.
- The portal's own row-oriented historical CSV template remains supported.

### Historical roster and class bootstrap
- Added **Create missing historical roster/classes** for AccessIEA imports.
- Preview distinguishes between:
  - riders already on the selected season;
  - existing team riders missing from that historical season;
  - existing riders missing an IEA member number;
  - genuinely missing riders.
- Missing riders can be proposed from AccessIEA name and `#IEA`.
- Existing exact-name matches with a blank portal IEA number can receive the AccessIEA number on commit.
- Conflicting nonblank IEA numbers are never silently replaced.
- Missing SeasonMembership records, SeasonClass records, and rider class assignments can be proposed during preview.
- Team-level inference is intentionally conservative:
  - Varsity / Junior Varsity / JV → Upper School;
  - Future/Futures class naming → Futures;
  - an existing rider grade may resolve grades 4–8 vs 9–12;
  - unresolved team level blocks the row instead of guessing.
- Existing compatible classes are reused.
- Preview includes a **Proposed Historical Setup** summary before any write occurs.
- Roster/class bootstrap and results commit in one transaction; any failure rolls the import back.

### Historical result corrections
- Added rider-history **Edit** and **Delete** actions for imported historical results.
- Historical result editing remains available while the season is archived.
- Edit supports class, regular/finals competition track, placing, manual/calculated points, explicit points, horse name, and notes.
- Regular-season history is restricted to the Regular track; finals use Individual or Team.
- H8/H14 Walk/Trot remain blocked from Team-track finals edits.
- Duplicate rider/show/class/track combinations are blocked.
- Deleting a result removes only that rider's historical result and entry.
- Other riders on the same imported show are preserved.
- If the removed result was the final entry on an imported historical show, orphaned ShowClass/Show records are cleaned up automatically.
- Historical edits and deletes create audit events.
- Normal/non-historical show results cannot use the historical-only correction routes.

### Season archive readiness
- Added an Administrator-only **Archive readiness** review before closing a season.
- Readiness checks surface:
  - incomplete shows;
  - planned/entered rider entries without results;
  - season memberships with no class assignments;
  - open family charges;
  - unresolved Draft, Submitted, or Approved reimbursement requests.
- Readiness findings are warnings rather than hard blockers.
- Administrators can intentionally archive with warnings after explicit confirmation.
- Direct archive submissions without readiness confirmation are redirected to the review screen.
- Season Review now clearly identifies **Active season**, **Open / inactive**, and **Archived** states.
- Archive/reopen controls use an explicit Admin permission flag from the view.

### Import reconciliation and performance
- Added a one-time **Import Reconciliation** summary after successful historical imports.
- Reconciliation reports results created, duplicates skipped, shows touched, riders/memberships/classes created, class assignments added, IEA numbers added, and warning count.
- Optimized Season Archive counts using database annotations instead of per-season count queries.
- Optimized Historical Data rider show/result counts using annotated membership queries instead of per-rider queries.
- Added mobile/responsive polish for historical import, reconciliation, readiness, and archive controls.

### Release notes
- No new database migration is required for v1.9.8.
- Historical finance starting balances are intentionally deferred to the v1.9.9 stabilization/backlog.
- AccessIEA CSV is the supported primary historical import workflow; XLSX support remains optional rather than required.


## v1.9.7 — Show Day Operations & Team Coordination

v1.9.7 adds a mobile-first show-day operations layer for coaches, show leads, committee chairs, parents, and riders. It combines public show updates, estimated scheduling, rider check-in, results workflow, volunteer/checklist coordination, and a personal **My Show Day** experience while preserving the portal's existing role and privacy boundaries.

### Show-day public updates and active notifications
- Added show-scoped public updates with **Everyone**, **Futures Team**, and **Upper School Team** audiences.
- Futures and Upper Team Parent committee chairs can publish and revise public information only for their assigned team designation.
- Coach/Admin and assigned Show Leads can publish to either squad or everyone.
- Rider accounts are explicitly blocked from publishing even if accidentally assigned a Team Parent committee role.
- Updates can be revised silently or actively re-notified.
- Immediate in-portal notifications target relevant entered riders/families and operational staff.
- Optional email delivery uses the separate **Email show-day updates** preference.
- Retracted updates disappear from the public feed while notification/audit history is retained.
- Points Secretary receives relevant show-day notifications without gaining Team Parent publishing authority.

### Prize List / estimated schedule
- Added a class schedule page for each show.
- Preserves the original **Prize list time** separately from the current **Show-day estimate**.
- Supports blank times and short public schedule notes.
- Added one-screen schedule entry/editing for authorized classes.
- Added bulk schedule shifts from a selected class forward.
- Added **Reset estimates to prize list** without changing the published baseline.
- Admin/Coach, assigned Show Lead, and Points Secretary can edit the full schedule.
- Futures and Upper Team Parents are limited to their designated team/shared classes.
- Parent/Rider accounts remain read-only.
- Schedule is clearly labeled as estimated because official show announcements remain authoritative.

### Show Day Dashboard and rider check-in
- Added **Show → Open Show Day**, optimized for phone use.
- Dashboard combines:
  - rider check-in/status;
  - current estimated class schedule;
  - recent public show updates;
  - checklist/volunteer status;
  - Needs Attention items;
  - result-entry links for authorized users.
- Rider statuses include **Expected**, **Arrived**, **Running Late**, **Scratched**, and **Finished / Left**.
- Status updates record the updater, timestamp, and optional operational note.
- Admin/Coach and assigned Show Leads can update all participating riders.
- Futures Team Parent can update Futures riders; Upper Team Parent can update Upper riders.
- Ordinary linked Parent/Guardian can update only their own rider.
- Rider accounts can update only themselves.
- Points Secretary has operational context and result-entry access but does not gain rider check-in authority solely from the Secretary role.
- Operational **Scratched** status remains separate from the underlying `ShowEntry` status.

### Team Parent operational workspace
- Futures and Upper Team Parents receive squad-scoped show-day authority rather than Coach/Admin authority.
- Team Parent Show Day dashboards are restricted to the appropriate squad's operational riders and classes.
- Team Parents can manage their squad's planning/checklist items and publish updates for their squad.
- Points-rider designation, Finance, and unrelated private rider information remain unavailable.

### Checklist and volunteer coordination
- Expanded `ShowPlanningItem` into structured show-day coordination with:
  - **Checklist**;
  - **Volunteer**;
  - **Supply / Hospitality**.
- Items can be designated for **Everyone**, **Futures Team**, or **Upper School Team**.
- Admin/Coach and assigned Show Leads can manage all planning items.
- Team Parents can create/edit/complete items for their designated team.
- Linked families can see and claim applicable family-visible volunteer/supply items.
- Assigned or claiming users can mark their own items complete.
- Added duplicate-safe starter plans:
  - attending shows receive a lightweight operational checklist;
  - hosted + attending shows add setup, officials, parking, ring crew, hospitality, awards, and cleanup operations.
- Show Day Dashboard surfaces open checklist count, volunteer openings, Needs Attention warnings, and the logged-in user's assignments.

### My Show Day
- Added `/shows/<show-id>/my-day/` for riders and linked Parent/Guardian accounts.
- Shows only directly linked rider information:
  - arrival/check-in status;
  - active classes and current estimated/prize-list times;
  - public schedule notes;
  - personal volunteer/show-day assignments;
  - applicable public/squad show updates.
- Added clear empty states for unlinked accounts and linked riders not entered in the show.
- No points-rider designation or Finance information is exposed.
- Status and assignment actions return to My Show Day when initiated there.
- Mobile layout uses compact class/time rows, larger tap targets, and simplified show-day actions.

### Results and Needs Attention integration
- Existing Secretary / Points Secretary result-entry permission is surfaced directly from Show Day.
- Needs Attention can flag:
  - riders still Expected / not checked in;
  - riders Running Late;
  - missing results;
  - missing points-rider selections for authorized users;
  - classes without schedule times;
  - unfilled volunteer positions;
  - incomplete checklist items.

### Stabilization and permission hardening
- Tightened Team Parent dashboard scope so Futures and Upper operational data do not leak across squads.
- Admin, Coach, assigned Show Lead, and Points Secretary retain full-team operational scope.
- Removed repeated season-membership queries from Show Day schedule/result checks by reusing prefetched membership data.
- Archived seasons block show-day rider-status mutations and planning claim/completion changes.
- Invalid My Show Day status submissions return to the originating personal workflow.
- Added targeted regression coverage for:
  - show-update audience restrictions;
  - schedule permissions and bulk adjustments;
  - rider check-in;
  - Team Parent squad isolation;
  - Secretary full-team context;
  - planning/volunteer permissions;
  - My Show Day family privacy;
  - archived-season mutation protection.

### Migrations
- `0026_v197_show_day_updates.py`
  - adds `ShowDayUpdate`;
  - links notifications to show updates;
  - adds `UserProfile.email_show_updates`.
- `0027_v197_prize_list_schedule.py`
  - adds prize-list/current-estimate scheduling fields to show classes.
- `0028_v197_show_day_checkin.py`
  - adds show-day rider status/check-in records.
- `0029_v197_show_day_planning.py`
  - adds planning item type and team designation fields.

### Architecture
- The large `portal/views.py` modularization remains intentionally deferred.
- Modularizing `views.py` is the first planned architecture task for v2.x before major v2 feature work.

## v1.9.6.1 — Fundraising Policy & Family View

### Season fundraising policy
- Added one fundraising policy per season.
- Supported policy models:
  - Team-wide;
  - Family credit;
  - Hybrid.
- Team-wide requires a 0% default family credit.
- Family Credit requires a 100% default family credit.
- Hybrid supports a configurable default family-credit percentage.
- Policy can define whether family participation is optional.
- Policy can restrict which family charge types fundraising credits may offset.
- Policy includes a plain-language family message and internal notes.
- Fundraising policy changes are recorded in the audit log.

### Contribution guidance
- Contribution entry now displays the active season's fundraising model and default family-credit percentage.
- New contribution forms leave the family-credit amount blank so, when a family is selected, the policy default can be calculated automatically.
- Treasurer can still override the calculated family-credit amount when circumstances require it.
- Credits remain capped by the contribution amount and the selected charge's available balance.
- Charge-type restrictions from the fundraising policy are enforced server-side.

### Parent/Guardian family view
- Added **Family Account → Fundraising**.
- Linked Parent/Guardian accounts can see:
  - amount raised for their family;
  - family credit received;
  - amount retained for the team;
  - campaign/date detail;
  - the family charge a credit was applied to;
  - the season's family-facing fundraising policy.
- Donor names and team financial-account/category details are intentionally hidden.
- Parents still cannot see another rider's family fundraising.
- Youth Rider accounts remain blocked from family financial and fundraising information.

### Migration
- `0025_v1961_fundraising_policy.py`
- Adds `FundraisingPolicy`.

### Architecture
- No `views.py` refactor in this release; that remains the first v2.x architecture task.

## v1.9.6 — Fundraising & Family Finance Privacy

### Fundraising
- Added fundraising campaigns with Planned, Active, and Closed states.
- Campaigns support goals, dates, descriptions, notes, and season ownership.
- Added fundraising contribution tracking with:
  - donor name;
  - received date;
  - payment method/reference;
  - team financial account and income category;
  - optional rider/family attribution;
  - optional family receivable credit;
  - notes and audit history.
- Every posted contribution creates/updates exactly one team-ledger income transaction.
- Family fundraising credit is tracked separately from cash so fundraising does not double-count income.
- A contribution can be:
  - entirely team-wide;
  - attributed to a rider/family without changing their balance;
  - partially or fully applied as a family credit against a specific charge.
- Family credit cannot exceed the contribution amount or the available balance of the selected family charge.
- Campaign dashboards show Raised, Family Credits, Team Retained, and goal progress.
- Added campaign-level CSV contribution export.
- Closed campaigns cannot receive new contributions.
- Fundraiser-generated ledger transactions redirect edits/voids back to the fundraiser source workflow so ledger and family-credit records stay synchronized.
- Voiding a contribution is non-destructive: the contribution is retained, its ledger transaction is voided, and its family credit is cancelled.

### Family finance privacy
- Youth Rider logins are explicitly denied Finance access.
- Rider accounts cannot view their own family account.
- Family financial information is restricted to the Parent/Guardian actually linked to that rider, plus authorized Admin/Treasurer users.
- Rider accounts cannot access reimbursement lists/forms/receipts.
- Rider accounts cannot gain Finance access through an accidental Treasurer committee assignment.
- Finance navigation remains hidden for Rider accounts.
- Finance audit scope is unavailable to Rider accounts.
- Coaches can no longer see finance-related events through the general Manage audit log; Coach audit history is limited to non-financial operational activity.

### Finance integrity hardening
- A financial transaction cannot be reduced below the total of its existing show allocations.
- A transaction cannot be moved to a season that conflicts with its allocated shows.
- Category/type changes are blocked when they would invalidate an allocation tied to a specific show budget item.

### Audit
- Fundraising campaign and contribution changes are included in the v1.9.5 audit framework.

### Migration
- `0024_v196_fundraising.py`
- Adds `FundraisingCampaign`.
- Adds `FundraisingContribution`.
- Adds `Fundraising credit` as a FamilyCredit type.

### Architecture
- `portal/views.py` remains intentionally unrefactored in v1.9.x.
- The views modularization remains the first architecture task for v2.x.

## v1.9.5 — Operational & Audit Polish

### Audit history
- Added an immutable-style `AuditEvent` activity log for important portal changes.
- Added **Manage → Audit log** for Admin/Coach users.
- Added a Treasurer-scoped **Finance audit log** that is limited to finance-related record types and seasons where the user has Finance access.
- Audit events are recorded for:
  - financial transaction create/edit/void/reversal;
  - show allocation add/edit/remove;
  - show budget item create/edit;
  - reimbursement draft/submit/review/payment state changes;
  - family charges, credits, payments, service agreements, and assistance workflows;
  - financial account/category and season-budget changes;
  - user account changes;
  - committee assignments;
  - show results.
- Ledger and reimbursement rows include direct History links where appropriate.

### Finance ledger usability
- Added ledger filters for:
  - search text;
  - posted / void / all history;
  - income / expense;
  - season;
  - account;
  - category;
  - show;
  - date range.
- Pagination preserves active filters.
- CSV export now preserves the active ledger filters and includes status/void audit fields.

### Reimbursement workflow
- Reimbursements now support a true **Draft → Submit → Review → Paid** workflow.
- Drafts remain private to the submitter until submitted.
- Submitters can edit drafts and either save again or submit for review.
- Treasurer review cannot access Draft records.
- Paid remains a terminal state under the existing transition rules.

### Financial safety
- Family Payments are no longer permanently deleted.
- Voiding a Family Payment:
  - retains the FamilyPayment row;
  - removes it from family balance calculations;
  - voids the linked ledger transaction instead of deleting it;
  - records who voided it, when, and why.
- Voided Family Payments cannot be edited.
- Financial-assistance reimbursement corrections now void previously-created ledger transactions rather than deleting them.

### Show Finance polish
- Added printable Show Finance summaries.
- Added Hosting vs Participation planned/actual summary cards.
- Added a warning when show allocations are included in show totals but are not assigned to a specific budget item.
- Existing itemized Show Budget and multi-show allocation behavior remains unchanged.

### Architecture
- The large `portal/views.py` refactor is intentionally **not** part of v1.9.5.
- Modularizing `views.py` is now the first planned architecture task for the v2.x line before major v2 feature work.

### Migration
- `0023_v195_operational_audit.py`
- Creates `AuditEvent`.
- Adds audit-safe void fields/status to `FamilyPayment`.

## v1.9.4.2.3 — Budget Item Label Fix

### Fixed
- Show allocation add/edit forms now display meaningful budget item labels instead of `ShowBudgetLine object (N)`.
- Budget items are shown as `Description · Category · $Planned Amount`, making similar hosted-show expenses much easier to identify during allocation.

### Database
- No migration is required.

## v1.9.4.2.2 — Itemized Hosted-Show Budgets

### Fixed
- Show budgets are no longer limited to one line per Scope + Type + Category.
- A hosted show can now contain multiple Administrative expense lines such as Insurance, Judge fee, Officials, Food, Permits, or Supplies.
- Removed the database uniqueness constraint that incorrectly treated those valid budget items as duplicates.

### Added
- Show Budget lines now include a required **Description / Budget item** field.
- Show allocations can optionally target a specific budget item.
- Plan vs Actual now calculates actuals against the selected budget item rather than repeating the category total on every same-category line.
- Multiple allocations from the same transaction to the same show/scope are supported when a payment covers more than one budget item.
- Existing budget lines receive their category name as an initial description during migration.
- Existing allocations remain valid and may be assigned to a budget item later.

### Migration
- `0022_v19422_itemized_show_budget.py`
- Removes the old show-budget uniqueness constraint.
- Removes the old one-allocation-per-transaction/show/scope constraint.
- Adds `ShowBudgetLine.description`.
- Adds optional `ShowTransactionAllocation.budget_line`.

## v1.9.4.2.1 — Show Budget Validation Fix

### Fixed
- Adding or editing a Show Budget line no longer runs an uncaught second model `full_clean()` after form validation.
- The Show is attached to the `ShowBudgetLineForm` instance before model validation.
- Duplicate Show Budget lines now return a normal form error instead of a 500 error.
- Category income/expense compatibility is validated in the form with a readable message.
- Hosting budget scope validation now stays inside the form rather than surfacing as a server error.

### Database
- No new migration is required.

## v1.9.4.2 — Multi-Show Financial Allocation

### Added
- One ledger payment or receipt can now be allocated across multiple shows.
- New `ShowTransactionAllocation` records distribute a transaction amount without creating duplicate ledger transactions.
- Each allocation records:
  - show;
  - Hosting operations vs Our team participation;
  - allocated amount;
  - optional notes.
- Allocation totals may be less than the source transaction, leaving a clearly displayed unallocated balance.
- Allocation totals can never exceed the source transaction amount.
- Hosting allocations are allowed only for shows marked **Hosting & attending**.
- Allocation management page shows Transaction Total, Allocated, and Unallocated amounts.
- Ledger rows now include **Allocate** / **Show allocations** actions.
- Show Finance now calculates income, expense, Budget vs Actual, and hosted-show P&L from allocation records.
- Hosted shows display Hosting income, Hosting expenses, Hosting surplus/loss, and Our Team Participation cost separately.
- Show-linked paid reimbursements automatically create a full allocation using the reimbursement's selected financial scope.
- Regression coverage for multi-show splitting and over-allocation prevention.

### Backward compatibility
- Existing v1.9.4.1 transactions that already have a show and Hosting/Participation scope are automatically migrated into a full-value allocation.
- Older show-linked transactions without a scope are not guessed. Show Finance flags them for explicit Treasurer allocation.

### Migration
- `0021_v1942_multi_show_allocations.py`
- Creates `ShowTransactionAllocation`.
- Adds show finance scope to reimbursement requests.
- Includes a data migration for existing classified single-show transactions.

### Accounting principle
The bank/ledger transaction remains the authoritative cash movement. Show allocations are management-reporting distributions only, so splitting a shared insurance, facility, transportation, or supply payment never duplicates the underlying expense.

## v1.9.4.1 — Project Hardening

### Fixed
- Reimbursement receipt downloads no longer fail because `Path` is now imported.
- Treasurer reimbursement visibility is season-aware; a Treasurer only receives finance access for seasons where that assignment is active.
- Hosted-show Budget vs Actual now matches real ledger activity by **Hosting operations** vs **Our team participation** scope.
- Existing show-linked transactions without a scope are preserved and surfaced as **Unclassified** for Treasurer review rather than guessed.
- Season Show Package funding now behaves like dues-covered funding for bulk per-show family charges.
- Direct web-server access to all `/media/finance/*` files is blocked; Finance receipts must use authenticated Django download views.
- Account balances and Finance reports exclude voided ledger entries.

### Added
- Show finance scope on ledger transactions.
- Non-destructive ledger transaction lifecycle: Posted / Void.
- Void audit fields: who, when, and why.
- Optional opposite-direction reversal entry when voiding.
- Ledger audit views for Posted, Voided, or All History.
- Voided transactions cannot be edited.
- Pagination for the Finance ledger and reimbursement inbox (50 rows/page).
- Formal reimbursement state transitions; Paid requests cannot be silently reopened.
- Targeted automated tests for season-specific Treasurer permissions, funding-policy routing, show-scope validation, and retained void history.

### Migration
- `0020_v1941_finance_hardening.py`
- Adds transaction scope, status, void audit metadata, and reversal linkage.

### Security
- Caddy now returns 404 for `/media/finance/*`, including legacy and new Finance receipts. Permission-checked Django receipt endpoints remain the supported access path.

## v1.9.4 — Show Finance & Funding Policies

### Added
- Distinguishes shows the team **attends** from shows it **hosts & attends**.
- Configurable season show-fee policies for Regular Season, Region Finals, Zone Finals, National Finals, and other/special events.
- Funding choices: Included in membership dues, Bill families per show, Season show package, or Manual/mixed.
- Optional default rider show fee and plain-language dues/package coverage notes.
- Show Finance workspace with ledger income, expenses, net result, family charges, outstanding family responsibility, show budget, and reimbursements.
- Show budget lines distinguish **Our team participation** from **Hosting operations**.
- Hosted-show finance guidance keeps hosting economics distinct from the team's own participation costs.
- Optional family show-charge generation from actual show participants, with duplicate protection.
- Shows covered by membership dues do not suggest family show charges and actively block bulk generation unless the funding policy is changed.
- Reimbursement workflow available to team users without granting ledger access: submit expense → Treasurer review → approved/rejected → paid.
- Marking a reimbursement Paid creates the corresponding expense transaction in the team ledger.
- Treasurer reimbursement inbox; non-finance users see only their own requests.
- Permission-checked private reimbursement receipt downloads.
- New transaction receipts are stored under the private finance receipt path.
- Show Detail displays Attending / Hosting & attending financial role and links authorized finance users to Show Finance.

### Migration
- Adds show funding-policy fields to Season.
- Adds Show financial role.
- Adds ShowBudgetLine and ReimbursementRequest.
- Updates the upload path for new FinancialTransaction receipts.
- Migration: `0019_v194_show_finance.py`.

### Design principle
Show cost and funding source are deliberately separate. A team's dues can cover show fees without generating family receivables, while another team can bill per show or use a mixed policy.

## v1.9.3 — Financial Reporting

### Added
- Financial Reports landing page with season selection.
- Budget vs Actual report with planned income/expense, actuals, percentage used/achieved, favorable/unfavorable variance, and net comparison.
- Family Receivables report with billed, credits, external assistance, payments, outstanding balance, overdue amount, due-soon amount, and status filters.
- Financial Assistance & Reimbursements report with award ceiling, allocated, submitted, approved, reimbursed, remaining eligibility, draft claims, and outstanding claims.
- Category Activity report with category/type filters and transaction drill-down.
- CSV exports for Budget vs Actual, Family Receivables, Assistance/Reimbursements, and Category Activity.
- Season switching on all Financial Report pages.
- Treasurer “Needs attention” worklist on the Finance dashboard for:
  - overdue family balances;
  - reimbursement claims not submitted;
  - submitted/approved reimbursements still outstanding;
  - riders missing a Home Barn;
  - rider barns missing a season dues rate;
  - memberships whose dues charge has not been generated.
- Print-friendly report styling.

### Notes
- No database migration is required.
- v1.9.3 uses the Finance, family receivable, dues, and assistance data introduced in v1.9.0-v1.9.2.x.

## v1.9.2.3 — Version-linked Documentation

### Improved
- The version number in the site footer is now a documentation link.
- Each release links to the GitHub repository at its matching version tag, where GitHub renders that release's README.
- The default repository is `mcangeli/iea-team-portal`.
- Added optional `PORTAL_REPOSITORY_URL` configuration so forks/installations can point the footer to another repository.
- If the application is running a development build without a release version, the link falls back to the repository root.

### Deployment note
- Publish a Git tag matching the `VERSION` value (for this release, `v1.9.2.3`) so the version-specific README link resolves.
- No database migration is required.

## v1.9.2.2 — UX Polish

### Improved
- Active navigation highlighting for Dashboard, My Team, Riders, Shows, Calendar, Competition, Team, Finance, and Manage areas.
- Parent menu headings remain visibly active while the user is on one of their child pages.
- Mobile tables use horizontal scrolling with a clear swipe cue and touch-friendly spacing.
- Long operational pages use sticky mobile action controls so common actions remain reachable without scrolling back to the top.
- Generic POST forms now warn before navigating away after unsaved changes.
- High-traffic empty states were clarified with more useful next-step guidance.
- Existing v1.9.2 contextual Back navigation and v1.9.2.1 mobile-menu behavior are preserved.

### Notes
- No database migration is required.
- This release is UX-only and keeps the v1.9.3 Finance/reporting roadmap intact.

## v1.9.2.1 — Navigation & Mobile Menu Polish

### Improved
- Opening one expanding navigation menu now closes any other open menu.
- Clicking outside the navigation closes open expanding menus.
- Escape closes the active expanding menu and returns focus to its menu heading.
- Added a compact mobile Menu button for authenticated users.
- On phones, the primary navigation is collapsed by default instead of occupying the top of every page.
- Mobile navigation is presented in a single-column, touch-friendly layout with larger tap targets.
- Competition, Team, and Manage expand inline on mobile.
- Choosing a navigation link closes the mobile menu automatically.
- Theme and Sign Out remain available inside the mobile navigation.
- The Menu icon changes to a close icon while the mobile navigation is open.

### Notes
- No database migration is required.
- This is a navigation/UX patch and preserves the planned v1.9.3 Finance/reporting release number.

## v1.9.2 — Contextual Navigation

### Added
- Consistent contextual back navigation on subordinate pages.
- Rider Profile → Back to Riders.
- Rider History → Back to Rider Profile.
- Family Account → Back to Family Receivables for Finance users, or Back to My Team for family users.
- Show Detail → Back to Shows.
- Show Planning / Availability / Show Week → Back to Show.
- Lesson Detail → Back to Lessons.
- Season Review → Back to Season History.
- Awards → Back to Season Review.
- Finance Receivables / Ledger / Accounts / Budget / Dues Setup → Back to Finance.
- Generic create/edit/delete forms receive a compact Back action using browser history, with Dashboard fallback when opened directly.

### Notes
- No database migration is required.
- This release is navigation/UX only.

## v1.9.1 — Membership Dues & Family Receivables

### Added
- Home Barn records for the team.
- `SeasonMembership.home_barn`, preserving a rider's barn historically by season.
- Home Barn selection during rider season enrollment and on the Season Membership page.
- Season-specific membership-dues rates by Home Barn.
- Individual dues-charge generation and active-season bulk dues generation.
- Family receivables dashboard with billed, credits/assistance, paid, and outstanding totals.
- Private rider/family account ledger.
- Family charges with due dates, charge type, show association, and notes.
- Family credits/adjustments.
- Conditional Service Agreement Credits with Pending, Applied, and Cancelled states and optional required hosted shows.
- External Financial Assistance Awards with configurable approved maximum, provider/program, eligibility notes, and status.
- Assistance Claims with Not Submitted, Submitted, Approved, Reimbursed, Denied, and Cancelled states.
- Tracking for requested, approved, reimbursed, and family-relief amounts on assistance claims.
- Automatic posting of received external reimbursements to the v1.9.0 team ledger only when a claim is marked Reimbursed.
- Family payments that automatically create corresponding team-ledger income transactions.
- Treasurer correction workflows for family credits and payments; editing or deleting a payment updates/removes its linked team-ledger transaction.
- Finance dashboard snapshots for outstanding family receivables and remaining active external-assistance eligibility.
- Family-account link in My Team for authorized parents/riders and Finance users.
- Django admin coverage for all new v1.9.1 finance models.

### Privacy and permissions
- Team Finance remains available to Administrators, active-season Treasurers, and superusers.
- Coach status alone does not grant Finance access.
- Parents/Riders can view only the family account for their authorized rider(s).
- Ordinary Coaches do not gain family-account access solely from their rider-management permissions.

### Accounting behavior
- Home-barn dues establish the rider's normal membership charge.
- Team credits and service agreements reduce family responsibility without pretending cash was received.
- External assistance awards are treated as reimbursable programs with an approved ceiling, not as immediate team income.
- Draft assistance claims do not reduce the family balance.
- Submitted, Approved, and Reimbursed claim allocations reduce family responsibility.
- Reimbursed claims require an account, income category, received date, and amount actually received; that cash receipt is posted to the team ledger.
- Family payments are separate from credits and post actual cash income to the team ledger.

### Migration
`0018_v191_family_finance.py`

## v1.9.0 — Team Finance Foundation

## Added
- Team financial accounts with calculated ledger balances.
- Income/expense/category transaction ledger.
- Optional show and rider transaction relationships.
- Receipt/document uploads with finance permission checks in the portal workflow.
- Season budgets with explicit Income/Expense direction.
- Budget-vs-actual dashboard.
- CSV ledger export.
- Created-by / updated-by audit fields and timestamps.
- Treasurer finance capability independent of primary portal role.
- Starter finance categories for existing teams.
- Premium light/dark Finance presentation consistent with the equestrian-club visual direction.

## Access
Administrators, active-season Treasurers, and superusers can access Finance. Coach status by itself does not grant financial access.

## Migration
`0017_v190_finance_foundation.py`

# IEA Team Portal v1.8.14 — Regional Advancement Tracking

## Added
Region Finals Individual entries placing 1st or 2nd are automatically identified as Zone qualifiers.

Futures and Upper School overall team placing can now be recorded on finals shows. A first-place overall team result at Region Finals is identified as advancing to Zone Finals.

Historical finals entry supports the same overall team placing fields.

## Corrected
Regular-season points qualification remains separate from post-season placement advancement.

The dashboard qualified-count calculation introduced in v1.8.13 has been corrected.

Zone-to-National advancement is not automatically inferred because National allotments vary by zone and season.

## Migration
`0016_v1814_regional_advancement.py`

# IEA Team Portal v1.8.13 — Equestrian Club Visual Refinement

## Refined
The portal now uses a more distinctive premium barn-club / equestrian-program visual language.

Dashboard gains a clubhouse-style hero and season-at-a-glance strip. Rider roster cards use larger editorial photography and season information. Record Book receives an honors-board treatment with Region, Zone, and National finalist counts.

Operational forms and show-day workflows remain deliberately straightforward.

Both light and dark themes receive the new treatment.

## Migration
No new migration.

# IEA Team Portal v1.8.12 — Dark Theme Surface Polish

## Fixed
Rider cards and several secondary card types now use proper dark-theme surfaces instead of retaining bright light-theme backgrounds.

Avatar placeholders, class chips, progress panels, and related card details have also been adjusted for better contrast in dark mode.

## Migration
No new migration.

# IEA Team Portal v1.8.11 — Welcome Dashboard & Dark Theme

## Added
The dashboard now displays `Welcome, <first name>` for the signed-in user, with username as a fallback.

A Light/Dark theme control has been added to the authenticated navigation. The selected theme persists in the user's browser.

## Refined
The light theme received a broader visual polish: layered neutral backgrounds, quieter card shadows, cleaner tables, improved spacing, and a more restrained equestrian-club/editorial look.

## Migration
No new migration.

# IEA Team Portal v1.8.10 — Historical Finals Results

## Added
Historical Results now asks for the competition level: Regular Season, Region Finals, Zone Finals, or National Finals.

Region, Zone, and National historical shows all use the same finals structure. Each class result can be marked Individual or Team, allowing one rider to have two separate results in the same class/show when appropriate.

The Track field appears dynamically for finals and stays hidden for Regular Season historical entries.

## Migration
No new migration. This release uses the post-season fields introduced by `0015_v189_postseason_competition_tracks.py`.

# IEA Team Portal v1.8.9 — Post-Season Competition Tracks

## Added
Region Finals, Zone Finals and National Finals are now distinct competition levels.

Finals entries have separate Individual and Team tracks. The same rider can therefore ride both tracks in the same class and receive separate results.

## Scoring safeguards
Post-season results are stored and reported independently from regular-season qualification totals. Finals points do not inflate a rider's regular-season class qualification points or regular-season team qualification total.

H8/H14 Walk/Trot remains individual-only for team scoring purposes and cannot be added as a Team-track finals entry.

## Reporting
Season Review, Rider History, printable Rider summaries, Show Detail and Show List now identify finals competition levels/tracks.

## Migration
`0015_v189_postseason_competition_tracks.py`

# IEA Team Portal v1.8.8 — Record Book & Season Review Layout

## Refined
Record Book and Season Review now visually follow the same presentation system as Standings.

Season Review now leads with team qualification cards, followed by individual class qualification progress and the rider season snapshot.

Record Book now uses the standard competition table layout for Rider/Class/Season records, with improved ranking and award cards.

This release is presentation-only and does not change scoring logic or the database schema.

## Migration
No new migration.

# IEA Team Portal v1.8.7 — Historical Season Page 500 Fix

## Fixed
Season Review and Team Record Book could return HTTP 500 because some queries still used the retired reverse relation name `season_memberships`. The current `SeasonMembership.rider` relation uses `related_name="memberships"`.

All stale references were replaced with `memberships`, including related filters used by announcements and show-entry rider selection.

Rider History also now handles an unexpectedly empty summary defensively.

## Migration
No new migration.

# IEA Team Portal v1.8.6 — Class-Specific Rider Points & H8/H14 Team Scoring

## Fixed — Rider points
Season points for an individual rider are qualification totals **per class**, not one total across all classes. The qualification calculation was already class-specific, but several history/reporting screens still displayed an all-class aggregate. Those displays have been corrected.

Rider History and printable summaries now show class point totals. Season Review shows class point totals per rider. The Record Book now ranks Rider/Class/Season records.

## Fixed — Team points
H8 and H14 Walk/Trot classes do not count toward team points. v1.8.6 excludes those classes from all team-scoring rows/totals and prevents a point-rider designation from being applied to them.

## Migration
No new migration.

# IEA Team Portal v1.8.5 — Historical Rider Results

## Added
A dedicated **Add Historical Results** workflow is now available from Rider Development History.

Administrators and Coaches can select a prior season, enter a historical show once, and record multiple class results for the rider. Archived seasons are intentionally supported.

Historical entries are stored in the portal's normal result structure so individual points, wins, qualification progress, season summaries, and record-book calculations continue to use one consistent source of truth. Historical imports are individual-only and do not designate a points rider, preventing them from changing team points-rider totals.

Rider Development History now displays individual result lines and marks imported shows as **Historical entry**.

## Migration
`0014_v185_historical_results.py`

## Included fixes
v1.8.5 includes the v1.8.3 user-creation double-submit protection and the v1.8.4 media upload/storage fix.

# IEA Team Portal v1.8.4 — Media Upload Storage Hotfix

## Fixed
Rider photo uploads could return a 500 error because `settings.STORAGES` defined only the `staticfiles` backend. In Django 5.2, uploaded model files use the `default` storage alias; without it, the first attempt to save an uploaded image can fail while ordinary non-file edits continue to work.

v1.8.4 adds the filesystem `default` storage backend while preserving WhiteNoise for static files. The existing Docker media volume at `/app/media` continues to provide persistent storage.

## Migration
No new database migration is required.

# IEA Team Portal v1.8.3 — User Creation Double-Submit Hotfix

## Fixed
Creating a Rider/Guardian login could successfully create the account but still display a database conflict error. This was consistent with two near-simultaneous onboarding submissions: the first request completed successfully while the second collided with the newly-created username/link.

v1.8.3 prevents duplicate submits in the browser and also reconciles raced requests on the server. If the same username is already linked to the intended Rider/Guardian, the request is treated as a successful create rather than an error.

## Migration
No new migration is required. v1.8.3 includes all prior migrations through `0013_v182_user_sequence_repair.py`.

# IEA Team Portal v1.8.2 — User Onboarding Sequence Repair

## Fixed
New Rider/Parent login creation could still fail with a generic database constraint message. v1.8.2 repairs PostgreSQL sequences for `auth_user` and `portal_userprofile`, which can become out of sync after historical restores or schema repair work.

The onboarding view now also maps common database constraints to specific messages and includes the unexpected constraint name when one is encountered.

## Migration
`0013_v182_user_sequence_repair.py`

# IEA Team Portal v1.8.1 — Startup Hotfix

## Fixed
v1.8.0 could fail during Docker image build while running `collectstatic` with:

`NameError: name 'CalendarEvent' is not defined`

The new EventRSVP and ActionItem models were declared before CalendarEvent in `models.py` and used direct class references. v1.8.1 changes those relationships to Django string-based forward references.

## Upgrade
No additional migration was added. v1.8.1 still includes `0012_v180_team_hub.py`, which will apply normally if the v1.8.0 build failed before migrations ran.

# IEA Team Portal v1.8.0 — Team Hub

## Major features

### My Team
A new family/team hub combines current rider enrollment, upcoming events, event RSVP requests, and action items. Parents with multiple linked riders see their family in one place.

### General calendar RSVP
Calendar events may now request rider/family responses using Going, Maybe, or Not going, with an optional deadline.

### Reusable action items
Managers can create team tasks and sign-ups associated with a rider, event, show, or season. Items may be directly assigned or opened for families to claim.

### Dashboard coordination
The dashboard now surfaces My Week and a manager Needs Attention area for RSVP gaps, overdue/unclaimed tasks, volunteer approvals, and show availability.

### Reminder expansion
The daily reminder command now includes general event RSVP reminders and due assigned action items.

## Fixed
Creating a login from a Rider has been hardened so account/profile/linking conflicts are handled transactionally and displayed as form errors rather than a 500 page.

## Migration
`0012_v180_team_hub.py`

## Roadmap
- Finance & Fundraising remains targeted for v1.9.0 or later.
- Horse & Hoofprint Management has been added to the v2.x.x roadmap.

# IEA Team Portal v1.7.3 — Rider Season Enrollment

## Added
The Add Rider workflow can now create the rider's first SeasonMembership at the same time as the permanent Rider record.

### Rider creation
- Optional season selector.
- Active season preselected when available.
- Futures / Upper School team selection.
- Season class selection.
- Season-specific notes.
- Dynamic class filtering by season and team level.

### Data model
This does not change the underlying model: a Rider is still created once, while SeasonMembership records represent that rider's participation each year.

## Database
No migration is required for v1.7.3.

# IEA Team Portal v1.7.2 — Validation & Calendar Editing

## Fixed
- Duplicate create attempts no longer produce raw 500 errors in the hardened workflows.
- Context-aware validation catches duplicates whose uniqueness includes season/show context that is assigned after normal form validation.

## Added
- Edit action for manually-created calendar events.
- Synced show calendar entries link to Edit Show.
- Synced lesson calendar entries link to Edit Lesson.
- Friendly fallback message for database constraint collisions in key create workflows.

## Database
No migration is required for v1.7.2.

# IEA Team Portal v1.7.1 — Existing Guardian Linking

## Fixed
The rider page previously allowed creating a new parent/guardian but did not expose the existing many-to-many family relationship workflow.

## Added
- **Create new parent** and **Link existing parent** are now separate actions on Rider profiles.
- The existing-parent workflow lists GuardianContact records on the same team that are not already linked to that rider.
- Relationship label and primary-contact status can be set when linking.
- Existing guardian user accounts are preserved and linked to the additional rider.
- A guardian can be unlinked from one rider without deleting the guardian contact or user account.

## Database
No migration is required for v1.7.1.

# IEA Team Portal v1.7.0 — Season History & Reporting

## Added
- Season archive and Season Review workspace.
- Administrator close/reopen season workflow.
- Rider Development History across seasons.
- Staff-only or family-visible rider development notes.
- Awards & Recognition.
- Printable end-of-season rider summaries.
- Team record book with historical season point totals, wins, and published awards.
- Delegated Points Secretary access for results, detailed standings, qualification review, and standings export.

## Privacy
Competition-reporting delegation does not expose rider contact details or unrelated private operational information. Rider history remains limited to staff and the rider/linked family.

## Database
Adds `0011_v170_season_history_reporting`:
- `Season.is_closed`
- `Season.closed_at`
- `RiderDevelopmentNote`
- `RiderAward`

## Upgrade
`./portalctl upgrade` creates the normal pre-upgrade database backup before applying the release.

### Show Day Dashboard / Rider Check-In — Preview 3
- Added the first combined Show Day dashboard.
- Added rider show-day status tracking:
  - Expected;
  - Arrived;
  - Running Late;
  - Scratched;
  - Finished / Left.
- Status changes record updater and timestamp plus an optional operational note.
- Futures and Upper Team Parents may update rider status only for their designated squad.
- Linked Parent/Guardian users may update only their own rider.
- Rider users may update only themselves.
- Assigned Show Leads and Coach/Admin may update all participating riders.
- Secretary / Points Secretary gets operational dashboard access and direct result-entry links through the existing points-management permission.
- Dashboard surfaces:
  - expected / arrived / late / finished counts;
  - schedule snapshot;
  - missing result count;
  - missing schedule-time warning;
  - points-rider attention for authorized users;
  - recent public show updates.
- Added migration `0028_v197_show_day_checkin.py`.
- Added targeted dashboard/check-in regression tests.

### Checklist & Volunteer Coordination — Preview 4
- Extended `ShowPlanningItem` with:
  - item type: Checklist / Volunteer / Supply-Hospitality;
  - team designation: Everyone / Futures / Upper.
- Added squad-scoped Team Parent planning permissions.
- Added per-item permission checks so Team Parents do not receive edit controls for Everyone or opposite-squad items.
- Added claim/release behavior for family-visible volunteer and supply items.
- Added completion/reopen action for managers and the person assigned to/claiming an item.
- Added audit events for item creation, edits, completion, and starter-plan generation.
- Added duplicate-safe starter show-day plan generation.
- Starter plans differ between Attending and Hosting & Attending shows.
- Show Day Dashboard now includes checklist and volunteer counts, planning warnings, and personal assignments.
- Added migration `0029_v197_show_day_planning.py`.
- Added targeted coordination permission and starter-plan tests.

### My Show Day & General-Use Polish — Preview 5
- Added `/shows/<id>/my-day/` personal show-day experience.
- Added a direct personal-rider helper independent of manager/committee permissions.
- My Show Day shows only linked rider entries, current class estimates, rider status, personal volunteer/supply assignments, and applicable public updates.
- Parents/riders can update permitted rider arrival status without leaving the personal workflow.
- Completing a personal show-day assignment can return directly to My Show Day.
- Added clear empty states for unlinked accounts and riders not entered in the show.
- Added My Show Day shortcuts from Show Detail and the operational Show Day Dashboard.
- Added mobile polish:
  - 44px+ primary controls;
  - compact time/class rows instead of a horizontal table;
  - two-up quick actions on phones;
  - readable personal assignment cards;
  - sticky status update action on small screens.
- Added targeted tests for rider privacy, class filtering, unauthorized check-in, personal assignments, and empty-state handling.
- No database migration is required beyond Preview 4 migration `0029_v197_show_day_planning.py`.

### Final Stabilization
- Tightened Show Day Dashboard scope for Team Parents:
  - Futures Team Parent sees Futures operational riders/classes only.
  - Upper Team Parent sees Upper operational riders/classes only.
  - Admin, Coach, assigned Show Lead, and Points Secretary retain full-team operational scope.
- Preserved ordinary parent/rider privacy by keeping non-operational Show Day views limited to directly visible riders.
- Removed repeated season-membership database lookups from Show Day schedule/result checks by reusing prefetched memberships.
- Archived seasons now block:
  - rider show-day status mutations;
  - planning-item claims/releases;
  - planning-item completion/reopen actions.
- Invalid rider-status submissions now return to My Show Day when that is where the action originated.
- My Show Day shortcut is hidden from the operational dashboard when the user has no personally linked rider.
- Show Detail exposes My Show Day directly to Parent/Guardian and Rider primary roles.
- Added release-candidate regression tests for:
  - Team Parent squad isolation;
  - Secretary full-team scope;
  - archived-season mutation protection;
  - My Show Day invalid-status redirect behavior.
- No new database migration is required beyond `0029_v197_show_day_planning.py`.
