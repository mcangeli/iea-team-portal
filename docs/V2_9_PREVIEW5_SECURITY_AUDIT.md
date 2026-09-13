# ArenaLine v2.9.0 Preview 5 — Security & Data-Access Audit

## Purpose

Preview 5 verifies that ArenaLine's current role model, organization boundary, and delegated responsibilities are enforced by server-side data access rather than only by navigation or presentation.

This phase should prefer explicit scoping and denial over convenience. A user who guesses or receives a URL must not gain access to records outside the organization, family, rider, season, Finance scope, or delegated show responsibility they are allowed to see.

## Security boundaries under review

### 1. Organization / tenant boundary

- ordinary authenticated users must resolve an assigned organization;
- object lookups must be scoped to the current organization directly or through a trusted parent relation;
- records from another organization must not be readable, editable, deleted, exported, or downloaded by changing a primary key in a URL;
- the legacy unassigned-superuser compatibility behavior remains explicit and should not leak into ordinary accounts.

### 2. People & family privacy

- Parent/Guardian accounts may see only riders linked to their family relationships;
- Rider accounts may see only their own private rider information;
- Coach/Admin access remains broader as defined by the current product role model;
- private contact, profile, family-account, and rider-development information must use the private visibility helpers rather than roster visibility alone.

### 3. Finance

- Rider accounts must never receive Finance authority;
- Admin/Superuser Finance authority remains organization-scoped;
- Treasurer delegation is season-scoped;
- Family Account access must be limited to Finance-authorized users or the appropriate linked family according to the existing family-account contract;
- ledger, receipts, exports, reimbursement artifacts, assistance, dues, fundraising, and show-finance objects must be scoped before lookup or download.

### 4. Delegated roles

- Points Secretary authority is limited to points/qualification responsibilities;
- Team Parent roles are limited to their Futures or Upper coordination boundaries;
- Show Lead authority is limited to the assigned show and appropriate show-planning/show-day responsibilities;
- committee assignment must never silently upgrade a Parent/Rider account to general Coach/Admin authority.

### 5. Competition and show-day privacy

- point-rider designations remain hidden from Rider/Parent surfaces where required;
- family-facing show-day views expose only family-visible/published operational information;
- show-planning items respect `family_visible` and team-level boundaries;
- Hoofprint/horse-management mutation remains Coach/Admin or explicitly authorized workflow access.

### 6. Mutations and destructive actions

- POST endpoints must re-check server-side authority;
- mutations must scope the target object to the current organization/season/show before changing it;
- archived-season protections remain enforced;
- delete/void/unlink operations should fail closed on mismatched ownership or organization.

### 7. Exports, files, and downloads

- CSV exports must apply the same data visibility rules as their HTML views;
- receipts/documents must verify access before serving files;
- historical imports and administrative uploads remain management-only;
- no file URL should become an authorization bypass.

## Existing baseline controls confirmed at Preview 5 start

The current v2.9 code already provides several important shared controls:

- `organization_for_view_user()` requires an organization for ordinary accounts while retaining the explicit superuser compatibility case;
- `_visible_riders()` narrows Parent accounts to linked riders and Rider accounts to themselves;
- `_can_view_private_rider()` provides a stricter private-information boundary;
- `_visible_action_items()` combines organization scoping with family visibility and rider/user relationships;
- `_can_finance()` explicitly denies Rider accounts and recognizes only Superuser, Admin, or Treasurer authority;
- `_finance_season_ids()` constrains delegated Treasurer access to assigned seasons;
- Finance dashboard/audit queries begin from the current organization and permitted seasons.

These helpers are the baseline contract; Preview 5 verifies that individual endpoints consistently use them.

## Preview 5A — shared boundary baseline

Implemented and staging-validated:

- regression coverage for the organization boundary and shared visibility/Finance helper contract;
- retained the explicit unassigned-superuser compatibility behavior while requiring organization assignment for ordinary accounts;
- confirmed Rider Finance denial and season-scoped Treasurer behavior through existing hardening tests;
- confirmed existing fundraising/privacy/archive controls remain green under the v2.9 platform boundary.

## Preview 5B — cross-organization direct-object probe

Implemented and staging-validated:

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

Implemented; awaiting staging validation:

- added `portal/tests/test_v290_preview5_private_exports.py`;
- verifies Parent/Guardian private-rider access is family-specific rather than organization-wide;
- verifies Family Account access is family-specific and cross-organization membership IDs fail closed;
- confirms Rider and Parent/Guardian directory exports remain management-only;
- confirms Finance transaction and receivables exports reject a Parent without Finance authority;
- probes nested destructive/edit routes so a valid Organization A parent object cannot be combined with an Organization B child ID;
- confirms foreign guardian-link, show-class, and family-finance child objects fail before mutation;
- protects the receipt route expectation that authorization/object lookup happens before stored-file access.

Code review for this slice also confirms:

- rider/parent CSV exports begin from the current organization and require management authority;
- Finance report/export querysets begin from the current organization and re-check Finance authorization;
- transaction receipt downloads scope the transaction to the current organization before opening the receipt;
- reimbursement receipt downloads scope the reimbursement to the current organization and then require either the requester or Finance authority;
- `rider_guardian_unlink` resolves the rider from the current organization first and then constrains the link to that rider;
- nested ShowClass/ShowEntry and Finance allocation lookups are constrained through an organization-owned parent relation.

A deliberate product distinction is retained: same-organization users may see the normal rider roster/profile surface, while private rider data is controlled separately through `_can_view_private_rider()` and family-finance data through `_can_view_family_account()`.

## Audit sequence

1. ~~Platform/organization boundary and shared permission helpers.~~
2. People / family privacy and account linking — private/family baseline covered; additional role matrix remains.
3. Finance and financial downloads/exports — baseline covered; delegated Treasurer edge cases remain.
4. Competition, scoring, history, and Hoofprint access.
5. Operations, calendar, lessons, volunteer, and communications access.
6. Show Lead / Team Parent / Points Secretary delegated-role matrix.
7. Cross-organization IDOR sweep — direct objects and representative nested mutations/download boundaries covered.
8. Final regression matrix and closeout.

## Guardrails

- Do not broaden permissions to make tests pass.
- Prefer organization-scoped `get_object_or_404(...)` patterns over fetching globally and checking afterward.
- Keep module availability separate from authorization.
- Preserve genuine IEA role/domain behavior unless a security issue requires narrowing access.
- No schema changes should be introduced unless a concrete security gap cannot be closed safely at the service/query layer.

## Validation strategy

Preview 5 adds focused tests that intentionally create two organizations and attempt cross-organization access using guessed primary keys. It also exercises Parent, Rider, Coach/Admin, Treasurer, Points Secretary, Team Parent, and Show Lead accounts against both allowed and denied endpoints.

The full `portal` suite remains the final regression gate for every Preview 5 slice.
