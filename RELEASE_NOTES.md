# Release Notes

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

RC2 is the final review candidate for v2.0. It freezes the feature and visual scope and incorporates the usability fixes verified during RC1 testing.

### Dashboard permissions and role behavior
- Coach accounts no longer receive Administrator-only dashboard switchers simply because Coaches can manage team operations.
- Team Parent, Show Lead, and Points Secretary dashboards require the corresponding explicit assignment for non-Administrators.
- Administrators retain access to all operational dashboards for review and support.
- Dashboard summary spacing no longer depends on whether a workspace switcher is rendered.
- Action Items assigned directly to a Coach are surfaced on the Coach dashboard.

### Family and account access
- Authorized Parents/Guardians can open Family Account information directly from the Rider profile as well as My Team.
- Added a self-service **My Account** area.
- Users can update first/last name and email, change their own password, and manage notification preferences.
- Username, role, team assignment, and linked Rider/Parent records remain Administrator-controlled.

### Squad photographic branding
- Added optional Futures Team and Upper Team hero photographs in addition to the overall Program hero.
- Each hero has an independent crop-position preference.
- Single-squad family and Team Parent contexts use the corresponding squad photograph.
- Mixed-squad families and unconfigured squad images fall back to the Program hero.
- Latest migration: `0032_v200_squad_hero_images.py`.

### Documentation and deployment
- README is the primary installation and operating guide.
- Added Nginx, Apache, and Caddy reverse-proxy/HTTPS examples.
- Clarified role access, My Account, Family Account, squad branding, updates, backups, and rollback.

### RC2 scope
- No new feature development is planned between RC2 and final v2.0.0 unless a release-blocking issue is found.
- RC2 itself adds no schema change beyond the squad-branding migration introduced at the end of RC1.

## v2.0.0 — Release Candidate 1

RC1 froze the v2 feature and visual scope after the Preview series and moved development into production-readiness testing.

Key RC1 work included:
- role-oriented dashboard testing and permission cleanup;
- Show Lead action styling and all-role dashboard spacing;
- Coach-assigned Action Item visibility;
- Parent Family Account navigation from Rider profiles;
- user self-service account management;
- reverse-proxy deployment documentation;
- final Program/Futures/Upper photographic branding.

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
- No migration was required.

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
