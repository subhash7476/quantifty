# Ops Orchestrator — Runbook

## One-command morning start
    python scripts/ops/orchestrator.py

Brings up (in order) Flask → [browser: Upstox login] → market_ingestor →
chain_poller → PAPER session, ensures the EOD worker, then supervises. Ctrl+C
stops everything it started (the session stops cleanly and finalizes its evidence
package); an already-running EOD worker is left alone.

## Check health without starting anything
    python scripts/ops/preflight.py           # go/no-go, exit 0=GO 1=NO-GO
    python scripts/ops/orchestrator.py status  # per-child liveness + verdict
    python scripts/ops/orchestrator.py start --dry-run   # print the start plan

## Stop from another console
    python scripts/ops/orchestrator.py stop

## Preflight tiers
- BLOCK: Upstox token, STOP file, marks warm (rows>0 + ≥1 ltp>0 + fresh heartbeat),
  live VIX flowing. Pre-open, marks/VIX degrade to "poller/ingestor alive".
- WARN:  SPAN snapshot, instrument-master age, EOD feed freshness, EOD worker alive.

## Notes
- OAuth is interactive; the orchestrator opens the login page and blocks until a
  fresh token lands. It cannot be automated.
- The session is always recorded (never `--no-record`) — F-B1 counts recorded sessions.
- Stale EOD feeds trigger a background `download_all_data` catch-up that never delays
  the live session (the session reads only the live surface).
- If a `STOP` kill-switch file exists, `start` refuses before spawning anything
  (never silently clears a kill switch) — remove it deliberately, then start again.
- The session is stopped cooperatively (SIGBREAK/SIGTERM → `driver.stop()` → clean
  evidence finalize), never hard-killed.
