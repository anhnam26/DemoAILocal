# Historical report. Do not use as current deployment instructions.

# Linux/LAN release — 2026-09-30

## Run and configuration

- `start.sh` loads Conda, activates `cyberant`, changes to the source directory and execs Python with `0.0.0.0:8088`. Use `bash /absolute/source/path/start.sh`; options appended by the operator override those defaults. `.env` is required. A missing Conda installation/environment is an error, never an automatic installation or fallback to system Python.
- `APP_ENV=lan` is explicit HTTP LAN mode: origins restricted to private/loopback IPs or localhost; cookies remain HttpOnly/SameSite, but not Secure because the requested deployment uses HTTP. HTTPS production keeps Secure cookies and requires HTTPS origins. Invalid mode, credentials, wildcard, query/fragment/path and invalid ports fail validation. Firewall restrictions remain necessary: an origin allowlist is not a network firewall.
- LAN and production bootstrap a single admin with an explicitly configured 14–128 character password, ignore development seed files, and do not create plaintext password files. Existing database accounts and selections remain unchanged.
- `main.py` checks required imports/configuration before database startup, binds the port before importing the app, runs one worker and allows graceful shutdown. Never run two instances against the same SQLite database, even on different ports.
- systemd reads the project `.env` rather than forcing production mode. Its Python path must point at the real server Conda environment. Script invocation is foreground; use systemd to survive an SSH disconnect.

## Web fixes

- Clipboard copy attempts the secure API, then a legacy copy operation for HTTP LAN, then selects the visible answer and explains manual copy. No successful-copy message is shown when all automatic attempts fail.
- Network failures, non-JSON proxy/Host/Origin errors and session expiry have explicit handling without automatic retry. Logout failures are caught. IME composition does not submit a chat, and mobile answer scrolling honors reduced motion.
- Docker context includes the feedback module; an import-closure regression checks all local runtime modules are included. Docker remains optional, not required by the Conda deployment.

## Data and source maintenance

Keep `.env`, database and backups outside any destructive source synchronization. Prefer an absolute `APP_DATA_DIR` owned by the service user for future installations. Do not change this path on an existing deployment without migrating a consistent snapshot: a wrong path can look like a fresh install.

Before updating: stop intake, allow requests to finish, take a SQLite API backup and a protected copy of `.env`; stop the service, update source/dependencies deliberately, then start and check health/login/history/permissions/usage. Keep the matching previous source and database snapshot for rollback. Never restore an older database while the new service is running. Provider usage since a backup needs reconciliation after rollback.

Cleanup removes the obsolete root `Run.txt` after merging its useful instructions into README/DEPLOYMENT, and removes regenerable root Python/pytest caches after testing. Windows launcher scripts remain because they are still used on the development machine. No secrets, databases or backups are deleted.

Production transfer should exclude `.git`, `.vscode`, Python/test caches, Windows PID/log files, virtual environments and `data/initial-accounts.json`. Transfer a SQLite snapshot separately, not the live WAL database. Following the subsequent cleanup request, tests and offline evaluation/curation tools have been removed. Runtime lockfiles, knowledge synchronization and operational tools remain.

## Post-cleanup verification

Removed 24 files: 15 test modules, conftest, development requirements, 3 offline curation/evaluation scripts, evaluation cases and 3 generated JSON reports. Kept all 12 runtime Python modules and the unchanged 1,200-document corpus. Updated active instructions to remove commands for deleted tools.

After deletion, Python syntax/import-reference checks, JavaScript/Bash syntax and diff checks passed. A real server on an isolated temporary database passed startup, UI/assets, login/logout, knowledge, model/usage/admin, local zero-provider-call chat, history, feedback, deletion and backup checks. The first run passed functional checks and backup integrity but hit a Windows temporary-file cleanup lock. The temporary directory was removed and a second run completed successfully, including process shutdown and directory removal. No test script was saved in the source tree, and no live database/configuration or service was changed. This smoke check is not a rerun of the deleted full test suite.

## Historical validation results (before test removal)

The automated test suite and offline evaluation assets were subsequently removed at the owner's request. The results below describe the earlier release validation, not a suite still present or rerun after cleanup.

- Final complete suite: **101 passed**, including Chromium and backup/restore (200.27 seconds, exit 0). Log: `D:\Temp\anhna\cline\proceed-while-running-1790754958498-m4rnfp7.log`.
- Follow-up LAN/launcher suite: 20 passed, including the additional backup/restore business-record regression and LF requirement (41.74 seconds).
- Python parsing, JavaScript syntax, Bash syntax and `git diff --check` passed.
- Two warnings come from the existing Starlette test client's deprecated httpx integration and AnyIO alias. No new dependency or untested major upgrade was introduced to suppress them.
- No paid model calls, live database migrations, `.env` changes or service restart were performed in this Linux preparation round. The final run includes the added backup/restore test.

## Validation boundaries

The working machine is Windows; WSL is unavailable. Bash launcher tests use Git Bash with a fake Conda installation (including paths with spaces, failure paths and exit status). They do not certify activation on a real Linux Conda installation. Python entrypoint tests start a real isolated server, exercise duplicate-port rejection and restart persistence without provider calls. Linux/systemd/firewall and the actual LAN address must still be checked on the destination server.
