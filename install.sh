#!/usr/bin/env bash
set -euo pipefail

DEFAULT_ROOT="/opt/iea-team-portal"
DEFAULT_REPO="https://github.com/mcangeli/iea-team-portal.git"
DEFAULT_REF="${PORTAL_INSTALL_REF:-}"
ROOT_DIR="${PORTAL_ROOT_DIR:-$DEFAULT_ROOT}"
REPOSITORY="${PORTAL_REPOSITORY_URL:-$DEFAULT_REPO}"
APP_DIR="$ROOT_DIR/app"
ENV_FILE="$ROOT_DIR/.env"

usage() {
  cat <<EOF
IEA Team Portal Git installer

Usage:
  sudo ./install.sh [--root PATH] [--repo URL] [--ref TAG_OR_REF]

Defaults:
  root: $DEFAULT_ROOT
  repo: $DEFAULT_REPO
  ref:  latest stable version tag (unless PORTAL_INSTALL_REF is set)

This installer creates the Git-backed application checkout. It does not invent
production secrets. If $ENV_FILE does not exist, copy .env.example there,
edit it, and rerun ./portalctl preflight / ./portalctl upgrade.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ROOT_DIR="$2"; APP_DIR="$ROOT_DIR/app"; ENV_FILE="$ROOT_DIR/.env"; shift 2 ;;
    --repo) REPOSITORY="$2"; shift 2 ;;
    --ref) DEFAULT_REF="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

command -v git >/dev/null 2>&1 || { echo "Git is required." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required." >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is required." >&2; exit 1; }

mkdir -p "$ROOT_DIR" "$ROOT_DIR/backups" "$ROOT_DIR/logs"

if [[ -e "$APP_DIR" && ! -d "$APP_DIR/.git" ]]; then
  echo "$APP_DIR already exists and is not a Git checkout. Refusing to overwrite it." >&2
  exit 1
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "Cloning IEA Team Portal into $APP_DIR..."
  git clone "$REPOSITORY" "$APP_DIR"
else
  echo "Existing Git checkout found at $APP_DIR."
  git -C "$APP_DIR" fetch --tags --prune origin
fi

if [[ -z "$DEFAULT_REF" ]]; then
  DEFAULT_REF="$(git -C "$APP_DIR" tag -l 'v[0-9]*' --sort=-v:refname | awk '!/-(preview|rc|alpha|beta)/ { print; exit }')"
fi
if [[ -z "$DEFAULT_REF" ]]; then
  echo "No stable release tag found. Supply --ref explicitly for a preview/test installation." >&2
  exit 1
fi
git -C "$APP_DIR" rev-parse --verify --quiet "${DEFAULT_REF}^{commit}" >/dev/null || {
  echo "Requested install ref does not exist: $DEFAULT_REF" >&2
  exit 1
}

echo "Checking out $DEFAULT_REF..."
git -C "$APP_DIR" checkout --detach "$DEFAULT_REF"
chmod +x "$APP_DIR/portalctl" "$APP_DIR/install.sh"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$APP_DIR/.env.example" ]]; then
    cp "$APP_DIR/.env.example" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo
    echo "Created $ENV_FILE from .env.example."
    echo "Edit the production values before starting the portal."
  else
    echo "Shared environment file is missing: $ENV_FILE" >&2
    echo "Create it before running portalctl." >&2
  fi
else
  echo "Using existing shared environment: $ENV_FILE"
fi

cat <<EOF

Git-backed installation is ready:
  Application: $APP_DIR
  Installed ref: $DEFAULT_REF
  Environment: $ENV_FILE

After confirming the environment values:
  cd $APP_DIR
  ./portalctl preflight
  ./portalctl upgrade

Future tagged-release updates:
  ./portalctl update

Install a specific release/preview:
  ./portalctl update v2.0.0-preview2
EOF
