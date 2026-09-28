#!/usr/bin/env bash
set -euo pipefail

app_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd -- "$app_root"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    echo 'Install Docker Engine and the Docker Compose plugin first.' >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo 'Cannot access Docker. Start the Docker service or run: sudo bash Start-App.sh' >&2
    exit 1
fi
if [[ ! -f .env ]]; then
    echo 'Missing .env. Copy .env.example to .env and configure the API key, models and HTTPS origin.' >&2
    echo 'For existing accounts, import the database before first startup; see docs/DEPLOYMENT.md.' >&2
    exit 1
fi

compose=(docker compose --project-directory "$app_root" --env-file "$app_root/.env" -f "$app_root/compose.yaml")
"${compose[@]}" config --quiet
echo 'Building and starting the application in the background...'
if ! "${compose[@]}" up --detach --build --wait --wait-timeout 120 --timeout 420 app; then
    echo 'Startup failed or health check timed out. The container may still exist.' >&2
    echo 'Inspect: sudo docker compose logs --tail=100 app' >&2
    exit 1
fi
echo 'Application is healthy and running in the background.'
echo 'Backend: http://127.0.0.1:8088 (server only). Use your configured HTTPS domain in the browser.'
echo 'Stop: sudo bash Stop-App.sh'
