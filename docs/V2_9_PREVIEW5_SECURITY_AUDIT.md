# ArenaLine v2.9.0 Preview 5 — Security & Data-Access Audit

## Purpose

Preview 5 verifies that ArenaLine's current role model, organization boundary, and delegated responsibilities are enforced by server-side data access rather than only by navigation or presentation.

This phase prefers explicit scoping and denial over convenience. A user who guesses or receives a URL must not gain access to records outside the organization, family, rider, season, Finance scope, or delegated show responsibility they are allowed to see.

## Security boundaries reviewed

### 1. Organization / tenant boundary

- ordinary authenticated users must resolve an assigned organization;
- object lookups are scoped to the current organization directly or through a trusted parent relation;
- records from another organization must not be readable, editable, deleted, exported, or downloaded by changing a primary key in a URL;
- the legacy unassigned-superuser compatibility behavior remains explicit and does not leak into ordinary accounts.

### 2. People & family privacy

- Parent/Guardian accounts may see only riders linked to their family relationships for private data;
- Rider accounts may see only their own private rider information;
- Coach/Admin access remains broader as defined by the current product role model;
- private contact, profile, family-account, and rider-development information uses the private visibility helpers rather than roster visibility alone.

### 3. Finance

- Rider accounts never receive Finance authority;
- Admin/Superuser Finance authority remains organization-scoped;
- Treasurer delegation is season-scoped;
- Family Account access is limited to Finance-authorized users or the appropriate linked family according to the existing family-account contract;
- ledger, receipts, exports, reimbursement artifacts, assistance, dues, fundraising, and show-finance objects are scoped before lookup or download.

### 4. Delegated roles

- Points Secretary authority is limited to points/qualification responsibilities;
- Team Parent roles are limited to their Futures or Upper coordination boundaries;
- Show Lead authority is limited to the assigned show and appropriate show-planning/show-day responsibilities;
- committee assignment does not silently upgrade a Parent/Rider account to general Coach/Admin authority.

### 5. Competition and show-day privacy

- point-rider designations remain hidden from Rider/Parent surfaces where required;
- family-facing show-day views expose only family-visible/published operational information;
- show-planning items respect `family_visible` and team-level boundaries;
- Hoofprint/horse-management mutation remains Coach/Admin or explicitly authorized Show Lead workflow access.

### 6. Mutations and destructive actions

- POST endpoints re-check server-side authority;
- mutations scope the target object to the current organization/season/show before changing it;
- archived-season protections remain enforced;
- delete/void/unlink operations fail closed on mismatched ownership or organization.

### 7. Exports, files, and downloads

- CSV exports apply the same data visibility rules as their HTML views;
- receipts/documents verify access before serving files;
- historical imports and administrative uploads remain management-only;
- file-serving routes do not become an authorization bypass.

## Existing baseline controls confirmed at Preview 5 start

The current v2.9 code already provided several important shared controls:

- `organization_for_view_user()` requires an organization for ordinary accounts while retaining the explicit superuser compatibility case;
- `_visible_riders()` narrows Parent accounts to linked riders and Rider accounts to themselves;
- `_can_view_private_rider()` provides a stricter private-information boundary;
- `_visible_action_items()` combines organization scoping with family visibility and rider/user relationships;
- `_can_finance()` explicitly denies Rider accounts and recognizes only Superuser, Admin, or Treasurer authority;
- `_finance_season_ids()` constrains delegated Treasurer access to assigned seasons;
- Finance dashboard/audit queries begin from the current organization and permitted seasons.

These helpers became the baseline contract for the endpoint-by-endpoint Preview 5 audit.

## Preview 5A — shared boundary baseline

Staging-validated:

- regression coverage for the organization boundary and shared visibility/Finance helper contract;
- retained the explicit unassigned-superuser compatibility behavior while requiring organization assignment for ordinary accounts;
- confirmed Rider Finance denial and season-scoped Treasurer behavior through existing hardening tests;
- confirmed existing fundraising/privacy/archive controls remain green under the v2.9 platform boundary.

## Preview 5B — cross-organization direct-object probe

Staging-validated:

- added `portal/tests/test_v290_preview5_cross_organization.py`;
- creates two independent organizations and logs in as an Administrator for Organization A;
- attempts direct access to Organization B records by primary key across People, Horses, Competition, Finance, Administration, and Season History;
- expects cross-organization direct-object access to fail as `404`, preventing both data disclosure and object-existence leakage through normal feature routes;
- code review confirms representative Rider, Horse, Show/Class/Entry, Finance, and User-management lookups are constrained to the current organization or a trusted organization-owned parent relation.

Representative probes cover:

- `rider_detail` and `rider_edit`;
- `horse_detail` and `horse_edit`;
- `show_detail` and `show_edit`;
- `finance_account_edit`;
- `user_edit` and `user_reset_password`;
- `season_review`.

## Preview 5C — private data, nested mutations, exports, and files

Staging-validated:

- added `portal/tests/test_v290_preview5_private_exports.py`;
- verifies Parent/Guardian private-rider access is family-specific rather than organization-wide;
- verifies Family Account access is family-specific and cross-organization membership IDs fail closed;
- confirms Rider and Parent/Guardian directory exports remain management-only;
- confirms Finance transaction and receivables exports reject a Parent without Finance authority;
- probes nested destructive/edit routes so a valid Organization A parent object cannot be combined with an Organization B child ID;
- confirms foreign guardian-link, show-class, and family-finance child objects fail before mutation;
- protects the receipt route expectation that authorization/object lookup happens before stored-file access.

Code review also confirmed:

- rider/parent CSV exports begin from the current organization and require management authority;
- Finance report/export querysets begin from the current organization and re-check Finance authorization;
- transaction receipt downloads scope the transaction to the current organization before opening the receipt;
- reimbursement receipt downloads scope the reimbursement to the current organization and then require either the requester or Finance authority;
- `rider_guardian_unlink` resolves the rider from the current organization first and then constrains the link to that rider;
- nested ShowClass/ShowEntry and Finance allocation lookups are constrained through an organization-owned parent relation.

A deliberate product distinction is retained: same-organization users may see the normal rider roster/profile surface, while private rider data is controlled separately through `_can_view_private_rider()` and family-finance data through `_can_view_family_account()`.

## Preview 5D — Competition, Hoofprint, and delegated-role boundaries

Staging-validated:

- added `portal/tests/test_v290_preview5_delegated_roles.py`;
- verifies Points Secretary can manage competition results and see the season review while remaining blocked from general show administration, historical imports, Horse Registry management, and Finance;
- verifies Futures Team Parent retains show-planning coordination access without gaining general show administration, Hoofprint/horse-list mutation, or Finance authority;
- verifies Show Lead can use assigned-show planning and Hoofprint/horse-list workflows but cannot use the same delegated authority on another show in the same organization;
- verifies Show Lead does not gain general show editing, Horse Registry creation, or Finance authority;
- verifies delegated roles receive `404` rather than foreign organization data when a Hoofprint/show URL contains another organization's show ID.

Code review confirmed:

- scoring/result mutation first resolves the ShowEntry through the current organization and then applies season-scoped points authority;
- historical CSV entry/import/template routes remain Coach/Admin management-only and scope the season to the current organization;
- Hoofprint and uploaded horse-list routes scope the show to the current organization before rendering, mutating, or serving a child document;
- Hoofprint finalization and horse-list upload require `_can_manage_show_horses()`, which is Coach/Admin or Show Lead for that specific show;
- show-planning access computes allowed team levels from the user's current delegated role, and individual planning-item mutations re-check both visibility and item-level authority;
- existing prize-list schedule coverage verifies Futures/Upper Team Parent edits stay squad-scoped and Rider accounts remain read-only even if a committee assignment is attached accidentally.

## Preview 5E — Operations and Communications access

Staging-validated:

- added `portal/tests/test_v290_preview5_operations_access.py`;
- verifies private Calendar events remain hidden from Parent/Rider accounts;
- verifies foreign-organization Calendar events fail closed;
- verifies Parents may RSVP only for linked riders;
- verifies Lesson detail access requires a visible/linked rider for non-managers;
- verifies Volunteer review remains management-only and organization-scoped;
- verifies hidden Action Items cannot be claimed through a guessed URL while family-visible claimable items remain usable;
- verifies Notifications may only be marked read by their actual owner.

Code review confirmed:

- Calendar list/detail visibility is filtered server-side;
- lesson attendance visibility is narrowed through `_visible_riders()` for non-managers;
- volunteer submission constrains the selectable rider queryset and volunteer review requires management authority;
- RSVP resolves both the event and rider through organization/visibility-scoped querysets;
- Action Item claim/complete routes resolve through `_visible_action_items()` before mutation;
- Notification mutation is scoped directly to `user=request.user`.

## Final audit sequence

1. ~~Platform/organization boundary and shared permission helpers.~~
2. ~~People / family privacy and account linking.~~
3. ~~Finance and financial downloads/exports.~~
4. ~~Competition, scoring, history, and Hoofprint access.~~
5. ~~Operations, calendar, lessons, volunteer, and communications access.~~
6. ~~Show Lead / Team Parent / Points Secretary delegated-role matrix.~~
7. ~~Cross-organization IDOR sweep, including representative nested mutations/download boundaries.~~
8. Final regression matrix and closeout.

## Guardrails retained

- Do not broaden permissions to make tests pass.
- Prefer organization-scoped `get_object_or_404(...)` patterns over fetching globally and checking afterward.
- Keep module availability separate from authorization.
- Preserve genuine IEA role/domain behavior unless a security issue requires narrowing access.
- No schema changes were required for Preview 5.

## Validation strategy

Preview 5 focused tests intentionally create multiple organizations and exercise guessed primary keys, nested objects, family relationships, delegated roles, exports, files, POST mutations, and archived-season protections.

The full `portal` suite remains the final regression gate for Preview 5 closeout.
