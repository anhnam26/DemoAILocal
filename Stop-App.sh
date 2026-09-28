#!/usr/bin/env bash
set -euo pipefail

app_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd -- "$app_root"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    echo 'Install Docker Engine and the Docker Compose plugin first.' >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo 'Cannot access Docker. Check the Docker service or run: sudo bash Stop-App.sh' >&2
    exit 1
fi
if [[ ! -f .env ]]; then
    echo 'Missing .env: restore the deployment configuration before stopping this Compose project.' >&2
    exit 1
fi

compose=(docker compose --project-directory "$app_root" --env-file "$app_root/.env" -f "$app_root/compose.yaml")
echo 'Stopping the application; allowing active requests to finish (up to 420 seconds)...'
"${compose[@]}" stop --timeout 420 app
echo 'Application stopped. Database volume and accounts are preserved.'
