# Release Notes

## v2.1.5 — Post-Show Horse History

v2.1.5 completes the 2.1.x horse-operations progression by preserving what actually happened after each show and carrying that history into season summaries and the Team Record Book.

### Post-show horse history
- Added a dedicated **Post-show Horse History** workspace for each show.
- A Coach/Admin can generate a draft history from the current registry-horse assignments and leased/show-specific horse planning records.
- Each history record preserves a snapshot of the horse identity, provider/ownership information, show-class coverage, and show-specific notes at the time the history is created.
- Draft records can be reviewed to distinguish horses that were actually used from horses that were only part of the plan.
- Draft records can separately identify which horses counted toward the team's horse contribution.
- Leased/show-specific planning placeholders can be reconciled after the show to the actual Horse Registry horse used without changing the original planning record.
- Finalized history is immutable through the normal workflow and retains the finalization user/timestamp.
- Post-show notes can be retained with the show-level history record.

### Record Book and season history
- Added a **Horse Legacy** section to the Team Record Book.
- Horse history includes Horse of the Day totals with Full Day, Morning, and Afternoon breakdowns, show appearances, class coverage, and first/latest recorded appearances.
- Added **Season Horse History** to Season Review so archived seasons preserve horse participation alongside rider/team performance.
- Record Book and Season Review prefer finalized post-show snapshots when available, while retaining fallback to existing show assignments for older shows that have not yet been finalized.
- Reconciled leased/show-specific horses contribute historical participation to the linked Horse Registry record once the post-show snapshot is finalized.

### Data and migration
- Added `ShowHorseHistory` and `ShowHorseHistoryRecord` models.
- Added migration `0044_v215_post_show_horse_history.py`.
- Added focused regression coverage for draft generation, leased-horse reconciliation, finalization locking, and management permissions.

### Validation
- `python manage.py check` passes with no issues.
- `python manage.py makemigrations portal --check --dry-run` reports no pending model changes.
- Focused v2.1.5 tests pass 4/4.
- The complete `portal.tests` regression suite was run successfully on the test server.
- Manual live testing of draft generation, usage/contribution editing, leased-horse reconciliation, finalization, Record Book, and Season Review completed successfully.

## v2.1.4 — Course & Show Operations

v2.1.4 expands the show-operations layer around courses, horse eligibility, Hoofprint readiness, and host-provided Show Horse Lists while hardening permissions and show-day history.

### Course Operations
- Added a Coach/Admin **Course Information** workspace for show-specific course details, including course type, ring, selected classes, course walk, designer, fence count, combinations, related distances, handy options, operational notes, private coach notes, uploaded media, and external links.
- Integrated course readiness/status into Coach/Admin dashboards, Show Lead operations, Show Detail, and Show Day.
- Assigned Show Leads can view Course Information and maintain posted course media without gaining access to private Coach/Admin notes or full course setup.
- Course uploads support JPG/JPEG, PNG, WEBP, HEIC/HEIF, and PDF with a 20 MB limit and phone-camera-friendly upload controls.
- Uploaded course files are served through an authenticated, role-authorized portal route instead of exposing raw media URLs.
- Course create/edit/media/remove activity is recorded in the operational audit trail.

### Horse season eligibility enforcement
- Show Horse assignments now enforce the horse's `HorseSeasonProfile` class eligibility by default.
- Coach/Admin users can make an intentional exception with an explicit eligibility override and required reason.
- Assigned Show Leads cannot introduce new ineligible classes.
- Eligibility overrides are visibly identified on the Show Horses workflow and retained in audit details.

### Hoofprint stabilization
- Added live-vs-finalized Hoofprint comparison so the portal can warn when the current horse plan differs from the latest immutable snapshot.
- Added non-blocking completeness warnings for missing classes, rider-facing horse descriptions, missing/expired Coggins information, and missing equipment/lead-change data.
- Preserved the existing ability to finalize when a coach intentionally needs a usable Hoofprint despite warnings.
- Horse of the Day history is protected: a show-horse assignment with an attached award cannot be deleted. The horse can instead be marked unavailable while the historical award remains intact.

### Show Horse List documents
- Added versioned Show Horse List documents per show.
- Upload is optimized for taking a photo of a printed list from a phone while still supporting electronic PDF/image files.
- Each new upload becomes a retained revision instead of silently replacing earlier source documents.
- Added separate internal operational notes and **Coach Notes for Riders & Parents**.
- Family-visible horse-list notes are surfaced in the Hoofprint/show-horse workflow and on My Show Day for participating riders/parents.
- Horse-list documents are delivered through authenticated portal routes and are not exposed as raw media URLs.

### Show Day / presentation hardening
- Added branded production 403, 404, and 500 error pages.
- Course Operations uses the established premium equestrian page hierarchy and supports the existing light/dark/mobile presentation.
- Added a focused regression test around the Show Day planning-item crash that previously surfaced when assigned planning items were present.
- The narrow `ShowPlanningItem.owner_id` compatibility extension remains in v2.1.4 to avoid destabilizing the oversized legacy Show Day module late in the release cycle; architectural removal is deferred to the planned 2.9.x cleanup.

### Data, migrations, and validation
- `0040_v214_show_courses.py` adds show course records.
- `0041_v214_horse_eligibility_override.py` adds persisted show-horse eligibility override data.
- `0042_v214_show_horse_list_documents.py` adds versioned Show Horse List documents and family-visible coach notes.
- `0043_alter_showbudgetline_options_alter_showentry_options_and_more.py` captures previously outstanding model-state changes for budget/show-entry ordering and reimbursement/show-day defaults.
- Added v2.1.4 regression coverage for horse eligibility, Hoofprint comparison/completeness, Course Operations permissions/media, protected documents, Show Horse List privacy, Show Day planning items, and Horse of the Day history protection.
- Added `RELEASE_CHECKLIST_v2.1.4.md` for upgrade, role, privacy, presentation, and live-server validation.
- Added and maintained `ROADMAP.md` as a living release artifact for future development planning.

## v2.1.3 — Show Readiness Preview

v2.1.3 extends Horse & Hoofprint Management into show-readiness planning and gives assigned Show Leads operational horse access for their shows.

### Horse contribution requirement
- Added a season-level **Rides per contributed horse** setting, defaulting to 5.
- Required horses are calculated from active planned/entered rider-class rides, not rider count.
- Fractional requirements always round up to the next whole horse (for example, 11 rides at 5 rides per horse requires 3 horses).
- Scratched rider entries do not count toward the required-horse total.

### Class coverage readiness
- A show is only horse-ready when both the total horse-count requirement is met and every class with an active rider entry has at least one available horse assigned.
- Readiness can therefore flag an uncovered class even when the team has enough horses overall.
- Canonical Season Class IDs are used in readiness displays when available.

### Leased horse planning
- Added show-specific leased-horse planning records.
- Leased horses count toward the total contribution requirement and expected class coverage.
- The leased-horse workflow intentionally allows temporary planning names such as `Lease Horse 1` when the actual horse is not yet known.
- Leased horses remain readiness-planning records and are **not automatically included on the Hoofprint**.

### Show Lead horse operations
- An actively assigned Show Lead can manage show-specific horse assignments for that show, including availability, class coverage, show overrides, and Horse of the Day.
- Show Leads can manage leased-horse readiness plans and finalize Hoofprint snapshots for their assigned show.
- Permanent Horse Registry records, Coggins records, and season horse eligibility remain Administrator/Coach responsibilities.
- The Show Lead dashboard links directly into Horse Readiness and Show Horses for the assigned show.

### Presentation and navigation
- Added a branded Horse Readiness workspace using the established Horse & Hoofprint page-intro, action hierarchy, class chips, readiness states, dark-mode treatment, and mobile layout.
- Show Horses now links directly to Horse Readiness and distinguishes registry/contributed horses from leased planning capacity.
- Season Setup surfaces the current rides-per-horse rule and links to its dedicated editor.

### Data and tests
- Added migration `0039_v213_show_readiness.py` for the season horse requirement and show-specific leased-horse records.
- Added focused readiness tests for round-up behavior, leased-horse contribution, class-coverage failure, and scratched-entry exclusion.

## v2.1.2 — Hoofprint Builder & Presentation Polish

v2.1.2 completes the first Horse & Hoofprint Management workflow from horse registry through show assignment and finalized Hoofprint output.

### Hoofprint Builder
- Added a live Hoofprint review driven by available horses assigned to the show.
- Added PDF preview plus immutable finalized Hoofprint snapshots with version history.
- Hoofprint PDFs render on US Letter landscape, repeat table headers across pages, and prioritize compact Class IDs such as `H1`, `H2`, `H8`, and `H14`.
- Barn names are the primary horse identity on Hoofprint output, with show names displayed secondarily when different.
- PDF responses disable caching and Preview links use cache-busting parameters so current output is shown reliably on mobile and desktop.

### Season class IDs
- Added a canonical Season Class ID used by linked Show Classes and Hoofprint output.
- Existing show-level class numbers are retained for compatibility and historical data.
- Season Setup exposes the Class ID for direct management and linked Show Classes inherit updates.

### Presentation polish
- Unified Horse Registry, Horse Detail, Coggins, season eligibility, Show Horses, Horse of the Day, and Hoofprint Builder around the v2 private-club/editorial design language.
- Standardized `page-intro` headers, eyebrow labels, action hierarchy, class chips, status treatments, forms, and empty states.
- Made barn names the primary ringside identity throughout the horse-management UI while preserving formal show names.
- Added dedicated Horse & Hoofprint light/dark styling and a compact mobile treatment for ringside use.

### Data and migrations
- Added immutable `HoofprintSnapshot` storage.
- Added canonical season-class code support and migration/backfill behavior.
- Latest v2.1.2 migrations: `0037_v212_hoofprint_snapshots.py` and `0038_v212_season_class_codes.py`.

## v2.1.1 — Show Horses

v2.1.1 connected the Horse Registry to individual shows.

- Added show horse assignments with per-show class selection, availability, notes, and equipment/lead-change overrides.
- Added Horse of the Day tracking for Full Day, Morning, and Afternoon sessions.
- Added Show Horses management and award history on horse profiles.
- Preserved registry defaults while allowing event-specific overrides.
- Added migrations `0035_v211_show_horse_assignments.py` and `0036_v211_horse_show_awards.py`.

## v2.1.0 — Horse Registry Foundation

v2.1.0 begins the Horse & Hoofprint Management work planned for the v2.1.x line.

### Horse registry
- Added a team-scoped Horse Registry with horse name/show name, breed/size, height, ownership/contributor information, home barn, photo, restrictions, crop/spur preferences, lead-change type, riding description, notes, and active/inactive status.
- Administrators and Coaches can add and edit horses; authenticated team members can view active horse profiles.
- Horse records are team-scoped so records from another team cannot be accessed through portal routes.

### Coggins tracking
- Added Coggins history as separate records instead of overwriting a single date/document.
- Each record stores test date, expiration date, optional document upload, and notes.
- The portal derives Current, Expiring Soon (within 30 days), and Expired status.
- Coggins documents and internal horse notes are only linked from the management view shown to Administrators and Coaches.

### Season class eligibility
- Added per-season Horse Season Profiles linked to existing `SeasonClass` records.
- Coaches can define which classes a horse is eligible for in each season without hard-coding class numbers into the horse record.
- Historical season eligibility remains intact when classes change in future seasons.

### Presentation and architecture
- Added Horses to the primary navigation.
- Added dedicated horse list, horse profile, Coggins, and season-eligibility screens with light/dark theme support.
- Horse models are isolated in `portal/horse_models.py` and loaded through `PortalConfig`, following the v2 modular architecture.
- Added migration `0033_v210_horse_registry.py` and focused v2.1.0 horse-registry tests.

### Next in v2.1.x
- v2.1.1: assign horses to shows and support show-specific availability/eligibility overrides.
- v2.1.2: build Hoofprint output from the show horse roster.
- v2.1.3: add show-readiness checks including horse-count guidance and Coggins warnings.

## v2.0.0 — Production Release

v2.0.0 is the first production release of the redesigned IEA Team Portal after the Preview 1–9 and RC1–RC2 validation cycle.

### Release status
- Promoted from RC2 with no feature changes.
- Validated by live role testing as Administrator, Coach, Rider, Parent/Guardian, and Show Lead.
- Latest migration: `0032_v200_squad_hero_images.py`.
- Future feature development moves to v2.1; v2.0.x is reserved for maintenance fixes.

### Highlights
- Role-aware dashboards for Coach, Team Parent, Show Lead, and Points Secretary.
- Rider lifecycle and historical season preservation.
- Redesigned Calendar, Show Day, Standings, Record Book, and Finance presentation.
- Parent/Guardian Family Account access with privacy-aware permissions.
- Self-service My Account for name/email, password, and notification preferences.
- Program, Futures, and Upper photographic hero branding.
- Git-based installation/update workflow with pre-update backups and rollback support.
- Production reverse-proxy/HTTPS guidance for Nginx, Apache, and Caddy.
- Polished light/dark “private riding club meets modern editorial design” presentation.

## v2.0.0 — Release Candidate 2

RC2 is the final review candidate for v2.0 and freezes the feature and visual scope after Preview testing.

Key RC2 work included role-aware dashboard permissions, Coach action-item visibility, Parent Family Account navigation, account self-service, reverse-proxy documentation, and Program/Futures/Upper photographic branding.

## v2.0.0 — Release Candidate 1

RC1 froze the v2 feature and visual scope after the Preview series and moved development into production-readiness testing.

Key RC1 work included role-oriented dashboard testing and permission cleanup, Show Lead action styling, Coach-assigned Action Item visibility, Parent Family Account navigation, user self-service account management, reverse-proxy deployment documentation, and final photographic branding.

## v2.0.0 — Preview 9: Final Presentation Polish

Preview 9 completed the planned v2 visual-design pass.

- Formalized the private-club palette: deep blue-green/charcoal, warm ivory, muted leather/brass, IEA blue, and restrained cyan.
- Built a purpose-designed dark palette rather than a simple inversion.
- Gave Shows, Riders, Standings, Record Book, Finance, and Calendar distinct but related presentation identities.
- Unified semantic status badges and action hierarchy.
- Polished tables, qualification progress, empty states, focus states, and restrained interaction motion.
- Added a dedicated mobile/ringside treatment for Show Day.
- No new migration was required.

## v2.0.0 — Preview 8: Photographic Branding

- Added a team-level hero/cover photograph.
- Added top/center/bottom crop-position control.
- Added **Manage → Branding** with live preview.
- Applied photography to Dashboard, role dashboards, and signed-out presentation.
- Added migration `0031_v200_team_branding.py`.

## v2.0.0 — Preview 7: Presentation Polish

- Established the “private riding club meets modern editorial design” direction.
- Reworked dashboard heroes, summaries, navigation, Riders, Shows, Record Book, forms, and login presentation.
- Preserved responsive behavior and light/dark theme support.

## v2.0.0 — Preview 6 / 6.1: Theme and Layout Stabilization

- Introduced the semantic light/dark theme layer.
- Honored system appearance on first visit and persisted user preference.
- Added the dashboard workspace overlap fix.

## v2.0.0 — Preview 5: Calendar Redesign

- Added Month and Agenda views.
- Added previous/next/Today navigation and type filtering.
- Added Futures/Upper filtering where the event source carries squad information.
- Added Calendar detail and RSVP-oriented behavior.
- No new migration was required.

## v2.0.0 — Preview 4: Rider Lifecycle

- Added active, graduated, left-team, and inactive rider lifecycle states.
- Added graduation year and lifecycle end date.
- Preserved historical rider records instead of deleting departed riders.
- Added migration `0030_v200_rider_lifecycle.py`.

## v2.0.0 — Preview 3: Role Dashboards

- Added Coach, Team Parent, Show Lead, and Secretary/Points dashboards.
- Added role-aware landing behavior and workspace switching for users with multiple assignments.
- Preserved existing privacy helpers and operational permissions.

## v2.0.0 — Preview 2: Git Installation & Updates

- Added `install.sh` for a permanent Git checkout at `/opt/iea-team-portal/app`.
- Reused the persistent `/opt/iea-team-portal/.env`.
- Added `./portalctl git-status`, Git-based update flow, pre-update PostgreSQL backups, migration preflight, persistent update logging, and guarded code rollback.
- Added stable/preview update-channel support.
- Git updates refuse a dirty source tree rather than overwriting local changes.

## v2.0.0 — Preview 1: View Architecture Refactor

- Replaced the former monolithic `portal/views.py` implementation with a compatibility/re-export layer.
- Moved active implementations into domain-oriented modules under `portal/view_modules/`.
- Preserved the external `portal.views.<name>` namespace and URL behavior.
- Added architecture documentation.