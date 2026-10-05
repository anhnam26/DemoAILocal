#!/usr/bin/env bash
# Foreground launcher. Use systemd for operation after disconnecting SSH.
set -Eeuo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$ROOT"
fail() { printf 'CyberAnt: %s\n' "$*" >&2; exit 1; }
if [[ "${1:-}" == '--help' ]]; then
    printf '%s\n' 'Usage: bash /absolute/path/start.sh [--host HOST] [--port PORT]' \
        'Host/port follow CLI, environment, then configuration (default loopback:8088).' \
        'For LAN access, configure APP_ENV=lan and your private IP/origin in .env.' \
        'Set CONDA_EXE to your conda executable if it is not on PATH.' \
        'APP_ENV_FILE can point to an external private config file.' \
        'Never installs dependencies or initializes/migrates data.'
    exit 0
fi
CONDA_BIN="${CONDA_EXE:-}"
if [[ -z "$CONDA_BIN" ]]; then CONDA_BIN="$(type -P conda || true)"; fi
if [[ -z "$CONDA_BIN" ]]; then
    for candidate in "$HOME/miniconda3/bin/conda" "$HOME/anaconda3/bin/conda" "$HOME/miniforge3/bin/conda" /opt/conda/bin/conda; do
        if [[ -x "$candidate" ]]; then CONDA_BIN="$candidate"; break; fi
    done
fi
[[ -n "$CONDA_BIN" && -x "$CONDA_BIN" ]] || fail 'Conda not found. Set CONDA_EXE=/absolute/path/to/bin/conda.'
CONDA_BASE="$("$CONDA_BIN" info --base)" || fail 'Cannot determine Conda base directory.'
[[ -r "$CONDA_BASE/etc/profile.d/conda.sh" ]] || fail 'Missing Conda shell initialization file.'
# Conda versions may reference unset variables; restore nounset after activation.
set +u
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV_NAME:-cyberant}" || fail 'Cannot activate Conda environment. Install requirements-lock.txt first.'
set -u
[[ -n "${CONDA_PREFIX:-}" && -x "$CONDA_PREFIX/bin/python" ]] || fail 'Activated environment has no Python executable.'
export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# exec preserves SIGTERM/Ctrl+C and the application's exit status.
exec "$CONDA_PREFIX/bin/python" "$ROOT/main.py" "$@"
