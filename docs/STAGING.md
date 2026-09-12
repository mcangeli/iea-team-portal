# ArenaLine Staging / Development Instance

This guide creates a second, isolated ArenaLine installation that can run beside the production IEA Team Portal on the same Docker host.

The staging instance uses its own:

- Git checkout and branch;
- shared `.env` file;
- Docker Compose project name;
- PostgreSQL volume and database credentials;
- media volume;
- loopback gateway port.

Production defaults remain unchanged.

## Recommended layout

```text
/opt/iea-team-portal/
  .env
  app/                       # production checkout, main

/opt/arenaline-staging/
  .env
  app/                       # staging checkout, feature/v2.9.0-road-to-arenaline
```

Recommended staging Docker identity:

```text
COMPOSE_PROJECT_NAME=arenaline-staging
POSTGRES_VOLUME_NAME=arenaline-staging_postgres_data
MEDIA_VOLUME_NAME=arenaline-staging_media_data
APP_PORT=8089
```

Production remains on its existing names and port (normally 8088).

## 1. Clone the staging checkout

```bash
sudo mkdir -p /opt/arenaline-staging
sudo chown "$USER":"$USER" /opt/arenaline-staging
cd /opt/arenaline-staging

git clone https://github.com/mcangeli/iea-team-portal.git app
cd app
git fetch origin
git checkout -b feature/v2.9.0-road-to-arenaline origin/feature/v2.9.0-road-to-arenaline
```

Verify:

```bash
git status
git branch --show-current
```

## 2. Create the staging environment file

```bash
cd /opt/arenaline-staging
cp app/.env.staging.example .env
nano .env
```

Replace at least:

- `DJANGO_SECRET_KEY` with a new staging-only secret;
- `POSTGRES_PASSWORD` with a new staging-only password.

For local SSH-tunnel access, the example values can remain:

```text
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8089
SECURE_COOKIES=0
SECURE_HSTS_SECONDS=0
```

Do not copy the production secret key or production database password into staging.

### Email safety

Keep this blank in staging:

```text
EMAIL_HOST=
```

This prevents a copied production database from sending test announcements, reminders, show updates, or other email to real families.

## 3. Validate Docker isolation before starting anything

From staging:

```bash
cd /opt/arenaline-staging/app
PORTAL_ENV_FILE=/opt/arenaline-staging/.env docker compose --env-file /opt/arenaline-staging/.env config --volumes
PORTAL_ENV_FILE=/opt/arenaline-staging/.env docker compose --env-file /opt/arenaline-staging/.env config --services
```

Expected staging volumes:

```text
arenaline-staging_postgres_data
arenaline-staging_media_data
```

Do not continue if those commands resolve to the production volume names.

## 4. Start only the staging database

```bash
cd /opt/arenaline-staging/app
./portalctl up -d db
./portalctl ps
```

This creates the isolated staging PostgreSQL volume without starting the web application.

## 5. Create a production database snapshot

Run this from the production checkout:

```bash
cd /opt/iea-team-portal/app
mkdir -p /opt/arenaline-staging/import
./portalctl exec -T db sh -c 'pg_dump --no-owner --no-privileges -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  > /opt/arenaline-staging/import/production.sql
```

Verify the dump is non-empty:

```bash
test -s /opt/arenaline-staging/import/production.sql && echo "Database snapshot created"
```

This is a read-only operation against the production database.

## 6. Restore the snapshot into staging

The staging database was created by the Postgres container from staging `.env`. Restore the production schema/data into that isolated database:

```bash
cd /opt/arenaline-staging/app
./portalctl exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  < /opt/arenaline-staging/import/production.sql
```

If staging has already been used and is not empty, recreate only the staging database volume before restoring:

```bash
cd /opt/arenaline-staging/app
./portalctl down

docker volume rm arenaline-staging_postgres_data

./portalctl up -d db
./portalctl exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  < /opt/arenaline-staging/import/production.sql
```

Never remove `iea-team-portal_postgres_data` while creating/resetting staging.

## 7. Copy production media into staging

First make sure the staging media volume exists:

```bash
cd /opt/arenaline-staging/app
./portalctl up -d db

docker volume create arenaline-staging_media_data
```

Then copy files from the production media volume into staging:

```bash
docker run --rm \
  -v iea-team-portal_media_data:/from:ro \
  -v arenaline-staging_media_data:/to \
  alpine sh -c 'cp -a /from/. /to/'
```

The production volume is mounted read-only for this copy.

## 8. Start ArenaLine staging

```bash
cd /opt/arenaline-staging/app
./portalctl preflight
./portalctl up -d --build
./portalctl ps
```

Then run the application checks:

```bash
./portalctl exec web python manage.py check
./portalctl exec web python manage.py showmigrations portal
```

## 9. Access staging privately with SSH

From your workstation:

```bash
ssh -L 8089:127.0.0.1:8089 YOUR_USER@YOUR_SERVER
```

Then browse to:

```text
http://localhost:8089
```

Because the staging gateway is bound to `127.0.0.1`, port 8089 is not directly exposed to the internet.

## 10. Updating the staging feature branch

For now, while v2.9 is under active development, update the checkout directly:

```bash
cd /opt/arenaline-staging/app
git fetch origin
git checkout feature/v2.9.0-road-to-arenaline
git pull --ff-only origin feature/v2.9.0-road-to-arenaline
./portalctl upgrade
```

The v2.9 roadmap includes improving `portalctl` branch/ref handling so explicit feature branches no longer require special deployment handling.

## Safety rules

Before any destructive Docker command, verify which installation directory you are in:

```bash
pwd
```

For staging it should begin with:

```text
/opt/arenaline-staging
```

Useful verification commands:

```bash
docker compose ls
docker volume ls | grep -E 'iea-team-portal|arenaline-staging'
```

Expected coexistence:

```text
Production project:  iea-team-portal
Staging project:     arenaline-staging

Production DB:       iea-team-portal_postgres_data
Staging DB:          arenaline-staging_postgres_data

Production media:    iea-team-portal_media_data
Staging media:       arenaline-staging_media_data

Production gateway:  127.0.0.1:8088
Staging gateway:     127.0.0.1:8089
```

## Refreshing staging later

A future staging refresh should be treated as destructive to staging only:

1. stop staging;
2. replace/recreate the staging PostgreSQL volume;
3. restore a fresh `--no-owner --no-privileges` production dump;
4. optionally replace the staging media volume from the production media volume;
5. confirm `EMAIL_HOST` is still blank;
6. run `portalctl preflight`;
7. start staging.

Never automate a staging refresh in a way that can target a production volume by inference. Production and staging volume names should always be explicit.
