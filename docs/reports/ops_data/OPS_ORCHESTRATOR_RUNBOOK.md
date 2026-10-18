# Ops Orchestrator — Runbook

## One-command morning start
    python scripts/ops/orchestrator.py

Brings up (in order) Flask → [browser: Upstox login] → market_ingestor →
chain_poller → PAPER session, ensures the EOD worker, then supervises until
15:50 on the day it started, when it stops everything cleanly on its own (before
2026-10-07 only Ctrl+C ended it, and a missed Ctrl+C made the next 09:10 scheduled
start a refused second instance). Ctrl+C stops it sooner and stops everything it started (the session stops cleanly and finalizes its evidence
package); an already-running EOD worker is left alone.

## Check health without starting anything
    python scripts/ops/preflight.py           # go/no-go, exit 0=GO 1=NO-GO
    python scripts/ops/orchestrator.py status  # per-child liveness + verdict
    python scripts/ops/orchestrator.py start --dry-run   # print the start plan

## Stop from another console
    python scripts/ops/orchestrator.py stop

If an orchestrator is running, `stop` writes `data/ops/stop_request` and waits up to
120 s for it to exit. The orchestrator notices the request within one supervise tick
(5 s). During its start sequence it notices at its next wait: every 2 s in the token
wait and the warm-up, every 30 s while parked before the open. It then shuts down the
way it does at 15:50: it stops every child it started, the session first, then the
rest, the EOD worker and the TS combo book included. A stop during the token wait also
sends the "Upstox token not received" Telegram alert, because the wait ended without
a token.

Only a session this orchestrator started itself finishes cleanly, because the clean
stop is a CTRL_BREAK that only reaches a process in the same console. A session it
adopted from an earlier run is killed without finalizing, and so is a session `stop`
reaches itself (no orchestrator running, or after the kill below).

If the orchestrator is still running after 120 s (hung, or busy in a step that never
waits), `stop` kills it, but only while `data/ops/orchestrator.pid` still names the
pid it asked. A scheduled run killed this way leaves a START line with no END line in
`data/ops/scheduled_runs.log`, sends no Telegram alert, and the scheduled task
records exit 1. A new orchestrator that started during the wait is left alone, with
its children, and `stop` exits 1; run `stop` again to stop it. If the killed
orchestrator is still alive a few seconds later, `stop` prints a warning, stops
nothing else, leaves the request in place and exits 1; end it by hand, then run
`stop` again.

Then `stop` stops what is left: children the orchestrator adopted rather than
started, or every child when no orchestrator was running or it was killed. That
covers the dashboard, market feed, session and both pollers. A session reached here
gets the group signal first. If the signal cannot be sent, the session is killed at
once; if it is sent but the session does not exit, `stop` waits up to 90 s before
killing it, so a whole `stop` can take about 3.5 minutes. The market feed is found
through the pid in `logs/market_ingestor_status.json` while that pid is alive and its
heartbeat fresh and its process predates the last status write, otherwise through
its pidfile. The pollers are ended with TerminateProcess, so their SIGTERM handlers
do not run; whoever stops a natively locked child (`stop`, the 15:50 stop, Ctrl+C)
removes its lock file once its process has exited. It leaves the EOD worker and the
TS combo book running, since either may be mid-write, and names them ("left running:
..."). Any child it tried to stop that is still alive afterwards is named on a "still
running after stop: ..." line, and `stop` exits 1.

Before 2026-10-18, `stop` killed only the dashboard, feed and session (the session
without its clean finish), left the pollers running, and a running orchestrator
respawned what it had killed.

## Preflight tiers
- BLOCK: Upstox token, STOP file, marks warm (rows>0 + ≥1 ltp>0 + fresh heartbeat),
  live VIX flowing. Pre-open, marks/VIX degrade to "poller/ingestor alive".
- WARN:  SPAN snapshot, instrument-master age, EOD feed freshness, EOD worker alive.

## Scheduled start and phone approval
Task Scheduler (`\Nifty\Orchestrator` 09:10, `\Nifty\DownloadAll` 22:00) runs both
through `scripts/ops/run_if_session.py`, which skips non-sessions. Re-register with
`scripts/ops/register_scheduled_tasks.ps1`. The 22:00 run downloads and builds; the
orchestrator's once-a-day morning catch-up runs `download_all_data.py --download-only`
(the builds ran out of memory beside the live stack on 2026-09-29).

**Logs.** `data/ops/scheduled_runs.log` holds one START/END/SKIP line per run (the START
line names the run log). The target's own stdout/stderr — `print`, `logging`, a traceback —
is teed into `data/ops/logs/<target>_<YYYY-MM-DD>.log`, appended across same-day restarts,
and the non-zero-exit Telegram alert names both files. It covers the orchestrator process
only: children it spawns (flask, ingestor, poller, session, …) write to their own logs.
Files are not pruned.

When the token is stale the orchestrator uses Upstox's **Access Token Request** flow
(`scripts/ops/token_approval.py`): it starts a one-route listener on 127.0.0.1:5055,
opens the ngrok tunnel, proves the public URL reaches the listener, and only then asks
Upstox for a token. You get an Approve prompt in the Upstox app and on WhatsApp, and a
Telegram ping. On Approve, Upstox POSTs the token to the webhook, which checks the
client_id, proves the token against the profile API, and saves it to
`config/credentials.json`. The tunnel is torn down as soon as the wait ends. The browser
login still opens as a fallback. The wait lasts up to 3 h (`TOKEN_TIMEOUT_S`); a timeout sends a
Telegram alert and abandons the start.

One-time setup (operator):
1. Install the real ngrok agent (`winget install ngrok.ngrok`), create a free ngrok
   account, run `ngrok config add-authtoken <token>`, and claim the free static domain
   (dashboard → Domains).
2. In `.env`, set `UPSTOX_NOTIFY_DOMAIN=<domain>` (and `NGROK_PATH` if ngrok is not on
   PATH). `UPSTOX_NOTIFY_SECRET` is already generated. Phone approval is off until both are set.
3. In the Upstox developer console, set the app's **Notifier URL** to
   `https://<domain>/upstox/notify/<UPSTOX_NOTIFY_SECRET>`.

Tokens expire at **03:30** after issue (`credentials.is_token_expired`), so one approval
is needed each trading morning; a token cannot be pre-approved the night before.

## Notes
- OAuth is interactive; the orchestrator opens the login page and blocks until a
  fresh token lands. Phone approval (above) replaces it when you are away from the PC.
- The session is always recorded (never `--no-record`) — F-B1 counts recorded sessions.
- Stale EOD feeds trigger a background `download_all_data` catch-up that never delays
  the live session (the session reads only the live surface).
- If a `STOP` kill-switch file exists, `start` refuses before spawning anything
  (never silently clears a kill switch) — remove it deliberately, then start again.
- The session is stopped cooperatively (SIGBREAK/SIGTERM → `driver.stop()` → clean
  evidence finalize), never hard-killed.
