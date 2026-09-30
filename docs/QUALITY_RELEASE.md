# Quality release — 2026-09-30

> Historical release report. The automated tests and offline evaluation tools were subsequently removed at the owner's request. Test counts below are historical results, not post-cleanup validation.

## Behavior and compatibility

- Citation failure never replaces a generated answer with source excerpts. No automatic retry or model substitution. Citation IDs are validated, not factual entailment.
- Each new saved answer has app/prompt versions, prompt hash, effective query, retrieved/sent chunk IDs and body hashes, input/output budgets, actual reported usage, finish reason, citation error category and token-usage record linkage. No rejected output or internal reasoning is retained. Provider failures continue to use the quota ledger; they do not create a successful chat.
- Generic retrieval downweights vendor-specific titles. A VLAN foundation article is editorial guidance marked `draft_engineer_review`; RFC 5517 supports the basic broadcast-domain definition, not certification of the operational checklist. Human technical review and a fresh live-model evaluation remain necessary.
- Numbered model slots sort numerically, ignore empty values and deduplicate model IDs. Conflicting numbered aliases are excluded and reported to admin. For compatibility, `OPENROUTER_MODEL` still overrides `MODEL`, with an explicit warning. OS environment overrides `.env`; changes to a parent process environment require restart. No discovery operation changes grants, quotas or account selection.
- Chat refreshes the permitted catalog every 30 seconds and on window focus. Admin refresh preserves checked permissions, including removed-model warnings.

## Feedback and privacy

- `/api/feedback` accepts an owned chat ID, rating, reason and comment only; snapshots come from saved server data, not a submitted answer. Identical submissions are idempotent; changes and admin reviews are recorded.
- Admin-only `/api/admin/feedback` lists/paginates/filters reports; detail includes question, displayed answer, account, IDs, timestamps, model, usage/cost, sources and diagnostics when available. Missing historical metadata is explicit.
- Migration keeps original legacy feedback and chats untouched. Recoverable legacy entries are grouped by chat and retain their rating history; orphan legacy rows remain in the original table. Migration runs once and cannot resurrect purged reports.
- Reports, snapshots and change history are deleted with their conversation. This preserves existing deletion expectations. Admin can also purge one report without deleting chat or quota usage. No new post-conversation retention or automatic time-based purge was introduced without an agreed policy. Existing backups have a separate operator-managed lifetime.
- Revoked, expired or changed sources hide the snapshot answer/source details on reads, consistent with conversation history. Physical backup deletion remains an operator responsibility.
- Free-text feedback is escaped; local CSS/JS only; CSP remains unchanged and reduced motion is supported.

## Deployment

Use the same Python environment as the current server. Tests set `APP_DATA_DIR` to temporary directories. Do not import `app` against the live database merely to inspect configuration: startup performs migrations, corpus synchronization and usage crash recovery.

Before deploying, quiesce requests and take a SQLite backup using the SQLite backup API (not just copy the main file while WAL is active). Verify the process identity/project root before stopping it. Startup synchronizes the canonical corpus while preserving retired states; saved historical answers are not rewritten. Verify `/api/health` reports `2026.09.30-quality-1` / `scope-2` after restart. Check the public tunnel target separately; a local process match does not prove the tunnel serves this process.

No paid model evaluation is included in offline tests. A passing suite is not an answer-accuracy certification.

Offline retrieval re-evaluation on the existing 108 cases: 104/104 scored cases retrieve and retain the expected source IDs; 4 unscored negatives remain excluded. This is a known test set, not a fresh holdout or live-answer accuracy result. The canonical corpus contains 1,200 documents; curation reruns preserve its hash.

The SQLite connection context now closes its handle after commit/rollback; this fixes Windows temporary-database cleanup locks rather than hiding cleanup errors.

Final validation: **74 passed**, 2 warnings, exit code 0 (136.50 seconds), including Chromium and the no-auto-grant regression. Python AST parsing, all JavaScript syntax checks and `git diff --check` passed. No live AI requests were made. Final test log: `D:\Temp\anhna\cline\proceed-while-running-1790753198248-rhw437r.log`.

Deployment completed locally on port 8088. Health returned app `2026.09.30-quality-1`, prompt `scope-2`. Pre-deployment backup: `D:\TestSystem\data\backups\deploy-quality-20260930-142634.sqlite3` (integrity `ok`). Post-start SQLite integrity is `ok`: 1,200 documents, 3 users, 8 chats, 2 original feedback rows, 25 completed usage records, 1 migrated quality report. Users, chats, original feedback and usage compare exactly to the pre-deployment snapshot; retired-source states are preserved. No Cloudflare process/service was found during inspection; the public tunnel target is not verified.
