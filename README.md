# IEA Team Portal

**Current version: v2.0.0 Release Candidate 2**

IEA Team Portal is a private, self-hosted operations system for an Interscholastic Equestrian Association team. It brings riders and families, seasons, classes, shows, points and qualification, lessons, calendars, communications, volunteers, show-day operations, history, and team finance into one portal.

> Private team software. This project is not an official IEA website or IEA product.

For version-by-version changes, see `RELEASE_NOTES.md`. For the v2 code organization, see `ARCHITECTURE.md`.

## Roles and dashboards

| Role / assignment | Primary use |
| --- | --- |
| Administrator | Full team administration; can review every operational dashboard |
| Coach | Roster, classes, shows, results, qualification, lessons, availability and team operations |
| Parent/Guardian | Linked riders, family-visible schedules, actions, volunteer activity and permitted family finance |
| Rider | Own rider/team information; staff strategy and private information remain restricted |
| Futures / Upper Team Parent | Squad-scoped coordination dashboard |
| Show Lead | Assigned-show operations, planning, volunteers and Show Day |
| Secretary / Points Secretary | Standings, missing results and qualification review |
| Treasurer | Finance operations without requiring Administrator access |

Administrators can open all role workspaces. Coaches receive the Coach workspace by role and only receive Team Parent, Show Lead, or Points Secretary dashboards when explicitly assigned that responsibility.

## Recommended first-time setup

1. Install the portal and configure the persistent `.env`.
2. Sign in as Administrator.
3. Open **Manage → Branding** and configure the Program, Futures, and Upper imagery.
4. Open **Manage → Season setup** and create/activate the current season.
5. Create the season's Futures and Upper classes.
6. Add Riders and assign season, team level, home barn, and classes.
7. Add/link Parents and Guardians.
8. Open **Manage → Users** and create logins linked to the appropriate Rider or Parent record.
9. Assign committee responsibilities such as Team Parent, Treasurer, and Secretary/Points Secretary.
10. Add Shows, show classes, availability, entries, and Show Lead assignments.
11. Add Lessons, Calendar events, announcements, volunteer requirements, and Action Items.
12. If using Finance, configure its accounts/categories/rates before entering family activity.
13. Add prior-season information through the historical-data tools when desired.

## Using the portal

### Dashboard

The main Dashboard is the season overview.

- **Coach:** roster health, qualification, availability, assigned Action Items, volunteer approvals, lessons, and shows.
- **Team Parent:** squad coordination, availability, volunteers, and planning.
- **Show Lead:** **Open Show Day**, **Planning & Volunteers**, and **Prize List / Schedule** for assigned shows.
- **Secretary / Points:** missing results, standings, qualification, and result review.

### My Account

Every signed-in user can open **My Team → My Account** to review their login information.

Users can:
- update first name, last name, and email address;
- change their own password;
- manage email-notification preferences.

Username, portal role, team assignment, and Rider/Parent links remain administrator-managed.

### Riders, seasons, and families

A **Rider** is a permanent person record. A **Season Membership** places that rider on a specific season's Futures or Upper roster and stores season-specific classes, home barn, and notes.

Do not delete a rider simply because they graduate or leave the team. Use the rider lifecycle controls so historical results and relationships remain intact.

Parent/Guardian records are separate from Riders and one parent may be linked to multiple riders. User accounts are then linked to the appropriate Rider or Parent/Guardian record.

A linked Parent/Guardian can open the permitted **Family Account** directly from **My Team** or from that Rider's profile. Rider accounts do not receive Finance access.

### Shows and Show Day

Create the Show first, then configure its classes/schedule, rider availability, and entries. Results are recorded against the appropriate rider and class.

A show can include availability, entries, points-rider designation, results, Show Lead assignment, planning/checklists, volunteers, Show Week communication, Show Day status, Prize List/Schedule, and show finance where enabled.

**Points-rider designation is staff strategy and is intentionally hidden from Rider and Parent accounts.**

Show Day is designed for phone use at the ring. Coaches and authorized Show Leads should use it for rider status/check-in, schedule context, open operational items, and show-day updates.

### Points and qualification

Rider points are tracked **per class**. The standard individual qualification threshold represented by the portal is **18 points in a class**.

Team points use the coach-designated points rider for each eligible class/show. Walk/Trot classes **H8 and H14 do not count toward team points**.

Use **Competition → Standings** for individual progress and team scoring. Postseason records support Regionals, Zones, and Nationals, including individual and team results.

### Calendar, communication, lessons, and volunteers

Calendar supports Month and Agenda views, event-type filtering, RSVP-enabled events, and Futures/Upper filtering where the source record carries a squad.

Announcements are for team communication. Action Items are for work needing an owner, response, or completion state. Notifications surface relevant portal activity.

Lessons support groups, scheduled lessons, and rider attendance. Volunteer requirements/logs support service tracking and approval. Committee assignments delegate operational responsibility without granting full Administrator access.

### Finance

Finance is intentionally restricted:

- **Administrator/Treasurer:** internal team finance.
- **Linked Parent/Guardian:** permitted family-account information.
- **Rider:** no Finance access.
- **Coach alone:** does not automatically grant Finance access.

Finance includes family charges/credits/payments, dues and service credits, assistance, budgets, reimbursements, show funding/allocation, fundraising, and reporting.

### History and Record Book

Use **Competition → Season history** for prior seasons and Season Review. Use **Competition → Record book** for the team's honors/archive presentation. Preserve historical Riders rather than recreating them as current Riders.

## Branding and appearance

Under **Manage → Branding**, configure three optional photographic identities:

- **Program hero** — overall Dashboard/sign-in image.
- **Futures Team hero** — used in Futures-specific family and Team Parent contexts.
- **Upper Team hero** — used in Upper-specific family and Team Parent contexts.

Each image has its own top/center/bottom crop preference. If a squad image is not configured, the Program hero is used as the fallback. A family spanning both squads uses the Program hero rather than arbitrarily selecting one squad.

A landscape photo around 16:9 or slightly wider works best.

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

```bash
sudo git clone https://github.com/mcangeli/iea-team-portal.git /opt/iea-team-portal/app
cd /opt/iea-team-portal/app
sudo ./install.sh
```

Populate `/opt/iea-team-portal/.env`. Typical production settings include:

```env
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

The application normally listens on `127.0.0.1:8088`.

## Reverse proxy and HTTPS

Your existing web server should accept HTTPS traffic for the portal hostname and proxy it to:

```text
http://127.0.0.1:8088
```

Before configuring the proxy:

1. Point DNS for the portal hostname to the server.
2. Set `DJANGO_ALLOWED_HOSTS` to that hostname.
3. Set `DJANGO_CSRF_TRUSTED_ORIGINS` to the full `https://` origin.
4. Keep `APP_PORT=8088` unless another local service already uses it.
5. Configure a TLS certificate.

### Nginx

```nginx
server {
    listen 80;
    server_name iea.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name iea.example.com;

    ssl_certificate /etc/letsencrypt/live/iea.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/iea.example.com/privkey.pem;
    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### Apache

Enable `proxy`, `proxy_http`, `ssl`, and `headers`:

```apache
<VirtualHost *:80>
    ServerName iea.example.com
    Redirect permanent / https://iea.example.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName iea.example.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/iea.example.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/iea.example.com/privkey.pem

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8088/
    ProxyPassReverse / http://127.0.0.1:8088/
    RequestHeader set X-Forwarded-Proto "https"
</VirtualHost>
```

### Caddy

```caddy
iea.example.com {
    reverse_proxy 127.0.0.1:8088
}
```

Caddy normally obtains and renews HTTPS certificates automatically.

You do **not** need to replace an existing web server. Add a separate virtual host/site for the portal hostname and leave other sites on ports 80/443 in place.

Verify with:

```bash
curl -I http://127.0.0.1:8088
curl -I https://iea.example.com
```

If login POSTs return a CSRF error, verify `DJANGO_CSRF_TRUSTED_ORIGINS` and that the proxy sends `X-Forwarded-Proto: https`.

Do not expose PostgreSQL or internal Docker services publicly.

## Updating

Check the checkout:

```bash
cd /opt/iea-team-portal/app
./portalctl git-status
```

Install RC2:

```bash
./portalctl update v2.0.0-rc2
```

For the stable channel after final release:

```bash
./portalctl update
```

The updater requires a clean Git tree, creates a pre-update PostgreSQL backup, fetches the selected ref, performs preflight/schema checks, applies migrations, rebuilds, and restarts the application.

Verify:

```bash
./portalctl ps
./portalctl git-status
```

## Backups and rollback

`portalctl update` creates a database backup before changing the application. `portalctl rollback-code` can return application code to the previous recorded checkout.

Code rollback does **not** automatically reverse an incompatible database migration. If the database must also be rolled back, restore the matching pre-update database backup.

Useful commands:

```bash
./portalctl git-status
./portalctl update
./portalctl update <ref>
./portalctl rollback-code
./portalctl ps
```

## v2 architecture

The former monolithic `portal/views.py` is now a compatibility/re-export layer. Active implementations live under `portal/view_modules/`. Specialized v2 URL/model modules isolate lifecycle, Calendar, account, and branding additions. See `ARCHITECTURE.md`.

## Release Candidate 2

RC2 is the final v2.0 review candidate. It freezes the feature and visual scope established in RC1.

RC2 includes:
- corrected role-dashboard permissions and consistent role-dashboard spacing;
- Coach-assigned Action Items on the Coach dashboard;
- Parent Family Account access from the Rider profile;
- user self-service **My Account**;
- Program, Futures, and Upper hero photography;
- complete reverse-proxy/HTTPS guidance.

Latest migration:

```text
0032_v200_squad_hero_images.py
```

No additional feature work is planned before final `v2.0.0` unless RC2 exposes a release-blocking issue.

## Troubleshooting

For deployment problems, capture the failing command plus:

```bash
./portalctl git-status
./portalctl ps
docker compose logs --tail=200
```

Do not include `.env` secrets or passwords when sharing logs.
