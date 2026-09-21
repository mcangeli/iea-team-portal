# ArenaLine

**Current version: v3.7.2**

ArenaLine is a private, self-hosted equestrian operations platform with discipline-specific competition modules. The included IEA module supports team administration, riders and families, horses and Hoofprint workflows, shows, scoring, qualification, operations, finance, communications, history, hosted-show management, and an explicitly published public spectator experience.

v3.7.0 completes the Barn Finance architecture with domain-separated Accounts Payable and Receivables, generic budgeting, unified operational reporting, transaction traceability, historical as-of reporting, and compatibility bridges for established IEA finance workflows.

> ArenaLine is independent software. The included IEA competition workflows are not an official IEA website or IEA product.

## Documentation map

- `README.md` — product overview, installation, setup, operation, updating, and troubleshooting.
- `ROADMAP.md` — canonical product roadmap and committed future release direction.
- `CHANGELOG.md` — concise release history/changelog.
- `ARCHITECTURE.md` — technical/domain boundaries and compatibility strategy.
- `docs/PRODUCT_AND_UI_GUIDE.md` — standing ArenaLine branding, UI, privacy, and documentation rules.
- `docs/releases/` — detailed release-specific notes; current release notes: `docs/releases/v3.7.0.md` (v3.7.1/v3.7.2 are maintenance releases).
- `RELEASE_CHECKLIST.md` — release-promotion gates.
- `RELEASE_NOTES.md` — retained detailed historical release notes for earlier releases.

The README intentionally remains an overview/instructions document; roadmap decisions and changelog history belong in their dedicated files.

## v3.7.2 maintenance release

### IEA receivable identity repair

v3.7.2 repairs legacy IEA receivable accounts created during the Barn Finance migration so account names use the rider's actual name rather than Django's historical-model representation. Where a canonical Person relationship can be safely resolved through the legacy identity bridge, the receivable account's primary customer is also restored. Existing manually named accounts and existing primary-customer assignments are preserved.

## v3.7.0 highlights

### Barn Finance Completion

ArenaLine Finance now provides a unified operational workspace across General Barn and IEA finance while preserving domain separation. The v3.7.0 architecture completes Accounts Payable, receivables operations, generic budgeting, reporting/export, transaction traceability, historical as-of reporting, and compatibility with established IEA finance records without introducing a second ledger.

Existing finance receipts remain private and are served through authenticated ArenaLine download endpoints rather than public media URLs.

## v3.6.2 highlights

### Flexible IEA Team Lessons

IEA scheduling is occurrence-first. **Team membership determines IEA lesson eligibility; the individual lesson occurrence determines who is actually scheduled.** A lesson may contain Futures riders, Upper riders, or both. The scheduling workspace supports occurrence-level rider selection, optional horse planning, Schedule Another with explicit roster copying, and month navigation. Barn Lesson Programs retain their recurring series/enrollment model.

### Family lesson visibility

Parent/Guardian Dashboard schedules include upcoming Barn and IEA lesson occurrences for linked riders while preserving relationship-based privacy and excluding unrelated riders, past lessons, and cancelled lessons.

### Multi-instance deployment isolation

Every installation must define a unique `COMPOSE_PROJECT_NAME` in its shared `.env`. `portalctl` passes that identity explicitly to Docker Compose so staging and production cannot silently share the default Compose project. Persistent database/media volume names must also remain installation-specific. `./portalctl status` reports the scoped installation services.

## v3.6.1 / v3.6.0 highlights

### Barn Dashboard and My Team

The root **Dashboard** is the general ArenaLine barn/program cockpit for everyone. It surfaces permission-aware schedules, action items, operational snapshots, quick actions, and authorized horse, lesson, and finance context. IEA competition details and team announcements remain in **My Team**, which is the dedicated team hub and entry point for authorized Coach, Team Parent, Points Secretary, Treasurer, Show Lead, and Show Manager workspaces.

### Independent hero branding

**Manage → Branding** provides separate Barn Dashboard and IEA Team hero images, while retaining Futures and Upper squad imagery. The general dashboard no longer inherits the IEA Team photograph when a distinct Barn image is configured.

### Account security

**My Account** supports verified email changes: the current password is required and the active email remains unchanged until the new address is verified. Users may optionally enable authenticator-app TOTP MFA, receive one-time recovery codes, and disable MFA only after confirming their current password.

ArenaLine defaults email delivery to the server's local Postfix service. Containerized deployments must make the host Postfix service reachable from the web container before verification mail can be delivered.

Focused v3.6 dashboard/security regressions and manual presentation/MFA checks have passed on staging. Clean system/migration checks and the complete portal suite remain the release-promotion gates.

## Roles and dashboards

| Role / assignment | Primary use |
| --- | --- |
| Administrator | Full organization administration; can review every operational dashboard |
| Coach | Roster, classes, shows, results, qualification, IEA Team Lessons, availability and organization operations |
| Trainer / Assistant Trainer | Barn Lesson Program instruction and permitted Barn lesson operations |
| Parent/Guardian | Linked riders, family-visible schedules, actions, volunteer activity and permitted family finance |
| Rider | Own rider/team information and My Lessons/self-rescheduling where eligible; staff strategy and private information remain restricted |
| Futures / Upper Team Parent | Squad-scoped coordination dashboard |
| Show Lead | Assigned-show operations, planning, volunteers and Show Day |
| Secretary / Points Secretary | Standings, missing results and qualification review |
| Treasurer | Finance operations without requiring Administrator access |
| Manage Horses capability | Organization-wide horse records/care/documents without broader Coach/Admin authority |
| Current Boarder / Responsible Party | Scoped management of the related horse's records only |

Administrators can open all role workspaces. Lesson management follows its own domain permissions: Coaches manage IEA Team Lessons, while active Trainers / Assistant Trainers manage Barn Lesson Programs. Horse-management capability remains independent of organizational lesson roles.

## Recommended first-time setup

1. Install ArenaLine and configure the persistent `.env`.
2. Sign in as Administrator.
3. Open **Manage → Branding** and configure Barn Dashboard, IEA Team, Futures, and Upper imagery.
4. Open **Manage → Season Setup** and create/activate the current season.
5. Configure the season's official IEA rulebook/catalog and participating disciplines.
6. Review/create the official season classes needed by the organization.
7. Add people through **People**, link/create login access only where needed, and assign current barn roles/relationships.
8. Grant **Manage Horses** from a Person profile when someone needs organization-wide horse management without broader Coach/Admin access.
9. Link riders to their current season, Futures/Upper team, home barn, and classes; link parents/guardians through the rider's family relationships.
10. Configure organization groups/programs and committees where needed.
11. Add Horses, maintain People↔Horse participation/care-team relationships, and configure required horse compliance records.
12. Add care history, due dates, Coggins, and supporting horse documents as appropriate.
13. Add Shows, official show classes, availability, entries, and Show Lead assignments.
14. Configure Barn Lesson Programs/Series and IEA Team Lessons; generate or create occurrences and prepare lesson rosters.
15. Add Calendar events, announcements, volunteer requirements, and Action Items.
16. Configure ArenaLine Station devices/PINs if using shared-device work tracking.
17. If using Finance, configure its accounts/categories/rates before entering family activity.
18. Add prior-season information through the historical-data tools when desired.

## Core workflows

### People, riders, seasons, and families

A **Person** is the canonical human identity. A login account is optional and is managed separately as access. A Person may hold multiple barn roles and relationships simultaneously. Capabilities such as **Manage Horses** are authorization, not organizational roles.

A **Rider** remains the competition-compatible rider record. A **Season Membership** places that rider on a specific season's Futures or Upper roster and stores season-specific classes, home barn, and notes. Do not delete a Person/Rider simply because they graduate or leave the organization; use lifecycle/effective-date controls so history remains intact.

Parent/guardian relationships are represented through People while legacy family structures remain compatibility bridges. One parent/guardian may be linked to multiple riders.

### Shows and Show Day

Create the Show first, then configure its classes/schedule, rider availability, and entries. Results are recorded against the appropriate rider and class.

A show can include availability, entries, points-rider designation, results, Show Lead assignment, planning/checklists, volunteers, Show Week communication, Show Day status, Prize List/Schedule, Horse & Hoofprint workflows, show finance, and deliberate public publication where enabled.

**Points-rider designation is staff strategy and is intentionally hidden from Rider and Parent accounts.**

Show Day is designed for phone/tablet use at the ring. Full-team operators can use the complete class order, squad Team Parents remain Futures/Upper scoped, and ordinary family/rider views remain read-only for operational controls.

### Points and qualification

Rider points are tracked **per class**. Qualification/postseason behavior remains part of the IEA competition module and should be changed only from verified official rule sources.

Team scoring eligibility is catalog-driven. H8/H14, W8/W14, and D8/D14 do not count toward team points.

Use **Competition → Standings** for individual progress and team scoring. Postseason records support Regionals, Zones, and Nationals, including individual and team results.

### Horses, care, compliance, and Hoofprint

ArenaLine includes Horse Registry, identifiers, People↔Horse relationships, care history/scheduling, protected documents, Coggins tracking, configurable compliance requirements, season class eligibility, show horse assignments, Horse of the Day, Horse Readiness, Show Horse Lists, Course Operations, Hoofprint Builder/finalized snapshots, and post-show horse history/Record Book summaries.

Care records preserve completed history and optional next-due dates. Coggins remains a specialized source of truth. Show workflows evaluate configured requirements through the show's date, and unresolved required compliance blocks readiness/Hoofprint finalization.

Organization-wide horse management may be delegated with **Manage Horses**. A current Boarder / Responsible Party relationship provides management only for the related horse.

### Lessons

Barn Lesson Programs are managed separately from IEA Team Lessons. A Barn program contains recurring series with enrollment, capacity, eligible Trainer/Assistant Trainer instruction, and generated or manual occurrences. IEA Team Lessons use season membership for rider eligibility and Coach instruction, while each new lesson occurrence stores its own explicit scheduled roster. Futures and Upper riders may be scheduled together. Legacy pre-v3.6.2 occurrences retain their season/team roster fallback.

The lesson-day workspace records attendance and Person/Horse assignments against the actual occurrence. Occurrences preserve historical snapshots even when a recurring series later changes.

Move/make-up operations move one participant rather than the entire lesson and preserve source/destination history. Eligible Riders can use **My Lessons** to reschedule only themselves. Whole-occurrence rescheduling remains a separate staff operation.

### Station and work history

ArenaLine Station is a tablet/shared-device surface for barn operations. Station devices use their own activation secrets and Person PINs rather than full portal credentials. Staff and working students can clock in/out for their current work roles; managers can review, edit, approve, summarize, and export work history.

### Calendar, communication, and volunteers

Calendar supports Month and Agenda views, event-type filtering, RSVP-enabled events, and operational projections from supported domains including lessons and horse care.

Announcements are for organization communication. Action Items are for work needing an owner, response, or completion state. Notifications surface relevant ArenaLine activity. Volunteer requirements/logs support service tracking and approval. Committee assignments delegate operational responsibility without granting full Administrator access.

### Finance

Finance is intentionally restricted:

- **Administrator/Treasurer:** internal organization finance.
- **Linked Parent/Guardian:** permitted family-account information.
- **Rider:** no Finance access.
- **Coach alone:** does not automatically grant Finance access.

ArenaLine Finance now combines the established IEA finance workflows with the generic Barn Finance & Business Operations architecture. Authorized users can manage domain-separated receivables, charges, credits, payments and allocations, bank imports/reconciliation, accounting exports, and business reporting. Lesson, boarding/lease, horse-care, show, and program activity connect through explicit finance boundaries rather than parallel ledgers.

### History and Record Book

Use **Competition → Season History** for prior seasons and Season Review. Use **Competition → Record Book** for honors/archive presentation. Preserve historical People/Riders rather than recreating them as current Riders.

## Production installation

### Requirements

- Linux server
- Docker Engine and Docker Compose v2
- Git
- DNS hostname and an existing reverse proxy/web server for public HTTPS access

Supported layout:

```text
/opt/iea-team-portal/
├── app/          # Git checkout
├── .env          # persistent production configuration
├── backups/
└── logs/
```

The `.env` lives outside the Git checkout so updates do not replace production secrets/configuration.

### Install from Git

ArenaLine server Git operations use SSH:

```bash
sudo git clone git@github.com:mcangeli/iea-team-portal.git /opt/iea-team-portal/app
cd /opt/iea-team-portal/app
sudo ./install.sh
```

Populate `/opt/iea-team-portal/.env`. Start from `.env.example` and replace every placeholder secret/password.

Typical production settings include:

```env
COMPOSE_PROJECT_NAME=iea-team-portal
POSTGRES_VOLUME_NAME=iea-team-portal_postgres_data
MEDIA_VOLUME_NAME=iea-team-portal_media_data
PORTAL_ENVIRONMENT=production
APP_PORT=8088
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=iea.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://iea.example.com
POSTGRES_DB=iea_team
POSTGRES_USER=iea_team
POSTGRES_PASSWORD=replace-with-a-strong-password
POSTGRES_HOST=db
POSTGRES_PORT=5432
TIME_ZONE=America/New_York
SECURE_COOKIES=1
SECURE_HSTS_SECONDS=31536000
PORTAL_UPDATE_CHANNEL=stable
```

Before first public use:

```bash
./portalctl preflight
./portalctl up -d --build
./portalctl health
```

## Updating production

Stable production installations follow stable Git release tags.

```bash
cd /opt/iea-team-portal/app
./portalctl git-status
./portalctl update
```

Or install v3.7.2 explicitly:

```bash
./portalctl update v3.7.2
```

`portalctl update` requires a clean Git tree, fetches stable tags, creates a validated database backup, switches to the selected release, rebuilds, runs deployment/schema preflight, starts the release, and performs health checks.

`./portalctl upgrade` does **not** select a newer Git revision. It rebuilds/migrates the revision already checked out and is appropriate for staging/preview workflows after the desired branch commit has already been selected.

The v3.6 migration chain adds account email-verification and MFA state on top of the v3.5 Barn Finance foundation. See `docs/releases/v3.7.0.md` for the current release-specific migration and deployment summary.

## Backups and rollback

`portalctl update` and `portalctl upgrade` create validated PostgreSQL backups. `portalctl rollback-code` can return application code to the previous recorded checkout and then runs deployment health checks.

Code rollback does not automatically reverse an incompatible database migration. Restore the matching database backup when schema/data rollback is required. Uploaded media is separate from PostgreSQL and must have its own backup policy.

See `docs/BACKUP_RESTORE_ROLLBACK.md` and `docs/STAGING.md`.

## Architecture

ArenaLine retains `Team` as the persisted tenant model for compatibility while generic platform code resolves organization context through service boundaries.

Generic platform domains include Core, People, Horses, Operations, Finance, and Communications. IEA-specific competition behavior belongs to `competition_iea`.

The public/external layer is a separate publication boundary. Anonymous routes consume explicit allow-listed publication payloads rather than authenticated internal views.

Person remains the canonical human identity and Horse the canonical equine identity. v3.4 layers the generic lesson hierarchy onto those foundations. Barn enrollment and IEA season/team roster membership remain distinct, and IEA-specific lesson context is layered onto generic series rather than encoded into the generic lesson core.

See `ARCHITECTURE.md`, `docs/PRODUCT_AND_UI_GUIDE.md`, and `docs/releases/v3.7.0.md`.

## Release process

Before any release is promoted to `main`, use `RELEASE_CHECKLIST.md`.

The release is not promotion-ready until code, tests, presentation, privacy/permissions, `VERSION`, README, changelog, roadmap, architecture/supporting documentation, and release tagging plan are consistent.

## Troubleshooting

For deployment problems, capture the failing command plus:

```bash
./portalctl git-status
./portalctl health
./portalctl ps
docker compose logs --tail=200
```

Do not include `.env` secrets or passwords when sharing logs.
