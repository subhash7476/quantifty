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

## Scheduled start and phone approval
Task Scheduler (`\Nifty\Orchestrator` 09:10, `\Nifty\DownloadAll` 20:00) runs both
through `scripts/ops/run_if_session.py`, which skips non-sessions. Re-register with
`scripts/ops/register_scheduled_tasks.ps1`.

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
