# quantifty — deterministic F&O trading platform for NSE, on Upstox

A Python platform for trading **Indian index derivatives** (NSE F&O, plus BSE Sensex
options) through **Upstox**. It covers broker login, instrument master, live market
data, an NSE-rules margin engine, a risk-gated execution layer with a paper broker,
and options-structure dashboards. It ships with two **paper-trading strategies**,
NiftyShield and Options-Wall, that you can run the day you clone it. (They are not
the `reference_strategies/` folder, which holds the heartbeat canary and fault
fixtures that test the platform itself.)

**Stack:** Python 3.11+ (tested on 3.13) · DuckDB (market data, chains, analytics) and
SQLite (orders, trade ledger, dashboard users) · Upstox API v2/v3 (REST + WebSocket,
no vendor SDK) · Flask + Tailwind · runs daily on Windows; the macOS and Linux code
paths exist but have not been run on a real machine yet

> **Paper by default. Nothing here is investment advice, and no strategy in this
> repository is validated for real money.** A live order path through Upstox exists,
> but nothing uses it unless you write the entry script yourself. It has never placed
> a real order, and its trade ledger has known gaps. See [Live trading](#live-trading).

---

## What it does

| Capability | What you get | Where |
|---|---|---|
| **Upstox login** | OAuth browser login, CLI login, or **phone approval** (approve the daily token in the Upstox app or WhatsApp, no browser needed). Tokens expire at 03:30 IST. Each morning the orchestrator's token gate asks for a new one: phone approval first, the browser login after 10 minutes | `core/auth/` (token store), `flask_app/blueprints/ops/routes.py` (browser login), `scripts/ops/token_approval.py`, `scripts/auth_upstox_cli.py` |
| **Instrument master** | Daily snapshot of every NSE F&O / EQ / index, BSE F&O / index (Sensex) and MCX F&O contract from the Upstox CDN. Resolution is `as_of`-aware, so lot-size revisions resolve correctly | `scripts/fetch_instrument_master.py`, `core/instruments/` |
| **Live market data** | WebSocket feed (protobuf V3) → 1m bars in DuckDB. 5-second option-chain snapshots for Nifty, Bank Nifty and Sensex | `scripts/market_ingestor.py`, `scripts/nifty_shield_paper/chain_poller.py`, `scripts/options_wall_poller.py` |
| **Execution** | One `ExecutionHandler` for paper and live, used by NiftyShield (Options-Wall has its own paper executor). Multi-leg order groups, position and P&L tracking, broker reconciliation at startup, a restart-safe SQLite order store, and a fill recorder (`trade_intelligence.duckdb`) on every `ExecutionHandler` fill | `core/execution/` |
| **Risk** | Drawdown, trade-count and position gates; margin-utilisation cap; greek limits that block new entries (NiftyShield also flattens on a portfolio-delta breach); stale-feed watchdog; kill switch (latched; auto-released only for a stale-feed trip or, in a live run, a fill-poll outage); a `STOP` file that blocks new entries in NiftyShield and Options-Wall and refuses every orchestrator start | `core/execution/handler.py`, `risk_manager.py`, `watchdog.py`, `options/nifty_shield_exit.py` (delta flatten), `core/options_wall/paper_executor.py` (Options-Wall STOP), `scripts/ops/orchestrator.py` (STOP refusal at start) |
| **Margin** | `NseMarginEngine`: SPAN (NSE v4.00 XML) + ELM + spread credits, from public NSE Clearing rules. Upstox basket-margin API for option structures | `core/risk/` (`NseMarginEngine`), `core/brokers/upstox_margin.py` (basket margin) |
| **Trade intelligence** | Options dashboard (PCR, net GEX, key levels, OI distribution, gamma by strike, option chain with OI change and IV). Options-Wall board (gamma walls, pin, HHI, dealer hedge ladder, OI since open, ranked "farm list"). Per-trade evidence reports | `flask_app/`, `core/analytics/`, `core/options_wall/` |
| **Regime engine** | DayType: intraday Bull / Bear / Choppy classification at 10:00 / 11:00 / 13:00 from partial-session features. Trained models ship in the repo | `core/state/daytype_engine.py`, [guide](docs/guides/DAYTYPE_ENGINE.md) |
| **Ops** | One-command supervisor for the trading day: instrument master → dashboard → token gate → feeds → warm-up gate → session → 15:50 self-stop. Read-only preflight. NSE-holiday-aware scheduling on Windows and macOS. Telegram alerts | `scripts/ops/` |
| **Deterministic runtime** | Single-threaded `LoopDriver`: the same code runs live and replay. NiftyShield's session runner records each session as a replayable evidence package | `core/runtime/`, `scripts/nifty_shield_paper/recorder.py`, `docs/DRIVER_SPECIFICATION.md` |

### The two paper runners

| | **NiftyShield** | **Options-Wall** |
|---|---|---|
| Underlying | Nifty 50 weekly options (Tuesday expiry, or the session before when Tuesday is a holiday) | Nifty, Bank Nifty, Sensex |
| When | once a session, entry 13:00–13:30, flat by 15:35 | any time 09:30–15:00 on the nearest expiry; can **hold overnight**, and is closed at 15:35 on the last regular session before expiry (the Friday for a Monday expiry; a session earlier when that day is a holiday or a special session such as Muhurat) |
| Signal | DayType regime at 13:00 + India VIX percentile | positive dealer gamma, spot within 0.5 % of the pin (the strike with the most call + put gamma), ATM IV ≥ realized + 2 vol pts |
| Structure | bull put / bear call spread, iron fly, **or a short straddle / strangle (undefined risk)** | ATM iron fly, wings ±1.5 % |
| Exits | ±1σ P&L bracket, delta flatten, 15:35 | TP 25 % of credit, SL 50 % of max loss, time stop |
| Sizing | 2 lots in Choppy, 1 in a trend; cut back, or skipped, if the Upstox basket margin is over 25 % of paper cash | 1 lot |
| Code | `strategies/nifty_shield_v1/`, `core/execution/options/nifty_shield_*.py` | `core/options_wall/` |
| How it works | [docs/guides/NIFTY_SHIELD.md](docs/guides/NIFTY_SHIELD.md) | [docs/guides/OPTIONS_WALL.md](docs/guides/OPTIONS_WALL.md) |

Both are **paper only**. NiftyShield is in a frozen forward paper window (restarted
2026-10-14) that exists to find out whether it works. Options-Wall is a pilot.

---

## Quick start (Upstox)

**You need:**
- an Upstox account with F&O enabled;
- Python 3.11+ (3.13 tested). numpy 2.4, scipy 1.17 and scikit-learn 1.8 do not
  support 3.10;
- about 1 GB of disk to start. The trading stack does **not** need NSE bhavcopy
  history. After that, Options-Wall writes a 70–90 MB snapshot file per session, and
  its scan-results store and the instrument master keep growing
  (see [Maintenance](#maintenance));
- a machine whose clock is set to IST (Asia/Kolkata). Moving only the scheduled
  times is not enough: the 15:50 self-stop and the 03:30 token expiry read the local
  clock.

### 1. Create an Upstox developer app

At [account.upstox.com/developer/apps](https://account.upstox.com/developer/apps),
create an app and set its **Redirect URL** to:

```
http://127.0.0.1:5000/ops/callback/upstox
```

Note the **API key** and **API secret**. Upstox allows **one active API app per
user**: creating a new one deletes your older ones.

### 2. Clone and install

```bash
git clone https://github.com/subhash7476/quantifty.git
```

```bash
cd quantifty
```

```bash
python -m venv .venv
```

Activate it: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate`
(macOS/Linux). Then:

```bash
pip install -r requirements.txt
```

### 3. Initialise (no token needed)

```bash
python scripts/bootstrap.py init
```

It asks for your Upstox API key/secret, the redirect URL (press Enter to keep
`http://127.0.0.1:5000/ops/callback/upstox`, which must match step 1), and a
dashboard username (default `admin`) and password. Then it writes:
- `.env` with a fresh `SECRET_KEY`, `NIFTY_PROFILE=trading` and a generated phone-approval secret;
- `config/credentials.json`;
- the dashboard user in `data/config/config.db`;
- the `data/` folders and an empty VIX-history store. The other stores are created by their writers on first run;
- today's instrument master (`data/instruments/nse_fo_instruments.duckdb`), on a
  trading day only. On a weekend or NSE holiday init skips it (and still prints
  `instrument master: ok`); the orchestrator fetches it on the next session morning.

It is safe to re-run: existing files are left alone. Forgot the dashboard
password? `python scripts/bootstrap.py init --user <your username> --password <new>`
resets it and leaves `.env` and `config/credentials.json` alone.

### 4. Log in to Upstox once

```bash
python scripts/auth_upstox_cli.py
```

Open the printed URL and log in. The browser then lands on
`127.0.0.1:5000/ops/callback/upstox?code=…`, which won't load yet. That's fine:
copy the `code` value from the address bar and run
`python scripts/auth_upstox_cli.py <code>`. The token is saved to
`config/credentials.json`. (Alternatively, start the orchestrator in step 6 and
it opens the login page for you.)

### 5. Seed the history the runners read

```bash
python scripts/bootstrap.py seed
```

The first run takes about a minute. The candles come from Upstox (about 880 daily
files, one per session) and the SPAN file from NSE Clearing's public archive. It
never downloads NSE bhavcopy. It ends with `verified: N VIX sessions` and exits
non-zero if the history came up short:
- ~3.5 years of Nifty / Bank Nifty / India VIX **daily** candles, which feed NiftyShield's VIX-percentile gate;
- the last ~10 days of index **1m** candles, which feed Options-Wall's realized vol;
- the latest NSE SPAN file. Before 08:30 IST that is the previous session's; later
  in the day it asks for today's end-of-day file, which is usually not out yet. A
  miss only prints `SPAN: unavailable (warning only)`.

Re-running fetches only what's missing. In the trading profile, the orchestrator
re-runs it every morning.

> Skip this step and nothing errors, but until the history exists NiftyShield trades
> a short straddle on every Choppy day (its VIX gate has no history) and Options-Wall
> never enters (it has no realized vol). The trading-profile orchestrator runs the
> seed in the background once the feeds are warm, so skipping it matters until that
> run finishes, or if you start the runners some other way.

### 6. Run a trading day

```bash
python scripts/ops/orchestrator.py
```

Start it before 09:15 IST. It:
1. refuses to start if a `STOP` file exists, then refreshes the instrument master;
2. starts the dashboard;
3. waits for a valid token (phone approval, else the browser login);
4. starts the market feed and the NiftyShield chain poller;
5. parks until the derivatives market opens and the feeds are warm, then starts the
   once-a-day background catch-up (`bootstrap.py seed` in the trading profile);
6. passes preflight;
7. runs the NiftyShield session and the Options-Wall poller;
8. stops itself at **15:50** by the computer's clock (Ctrl+C stops it sooner).

| Check | Command / URL |
|---|---|
| Health (token, STOP file, marks, VIX, SPAN, master) | `python scripts/ops/preflight.py`. It reads `NIFTY_PROFILE`; the trading profile skips the `eod_feeds` and `eod_worker` checks, which track the bhavcopy research feeds |
| What would start | `python scripts/ops/orchestrator.py start --dry-run` |
| Dashboard | `http://127.0.0.1:5000/`: **/nifty-shield/**, **/options/**, **/options/wall/**, **/ops/**. Until the first session runs, NiftyShield and Options-Wall show empty-state panels. **/ts-basis-daily/** is a research page: in the trading profile its signal panels stay at "Loading…" and its API returns 404 "Facts DB not found", because nothing builds those facts without NSE bhavcopy |
| Stop everything now | Ctrl+C in the orchestrator window, or `python scripts/ops/orchestrator.py stop` from any console. `stop` asks a running orchestrator to shut down and waits up to two minutes. The orchestrator stops every child it started, the EOD worker and the TS combo book included, as it does at 15:50. `stop` then stops what is left: children the orchestrator adopted from an earlier run, or everything when no orchestrator was running or it had to be killed after the wait. That includes both pollers but not the EOD worker or the TS combo book, which may be mid-write; `stop` names them. Only a session the running orchestrator started itself finishes cleanly. An adopted session, or one stopped with no orchestrator running or after the kill, is killed without finalizing |
| Kill switch | Create an empty file named `STOP` in the repo root, or use the kill button on **/ops/**. A running NiftyShield session stops opening new positions at its next signal (exits still go through) and stays stopped until it restarts. The Options-Wall paper executor also refuses new flies while the file exists (TP, SL, time stop and manual close still run), its farm list shows **Kill switch** wherever it would otherwise show **Tradeable**, and resumes entering as soon as the file is deleted. Every orchestrator start is refused until you delete the file |

`NIFTY_PROFILE=trading` (set in `.env` by step 3, or `--profile trading`) runs only
the trading stack. The default `full` profile is the repository owner's research
stack. It also starts a futures paper book and an EOD bhavcopy build worker that
need multi-GB NSE history you won't have. Its morning catch-up runs
`download_all_data.py --download-only` instead of `bootstrap.py seed`, and on a fresh
clone that starts downloading the NSE bhavcopy archives from scratch.

---

## Automate it

The scheduler only has to start the orchestrator each weekday morning.
`scripts/ops/run_if_session.py` skips days that are not NSE sessions (weekends,
holidays and special closures). It writes one START/SKIP/END line per run to
`data/ops/scheduled_runs.log` and copies the orchestrator's own output to
`data/ops/logs/orchestrator_<date>.log`. The orchestrator stops itself at 15:50.

**Windows (Task Scheduler)**, from the repo root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/ops/register_scheduled_tasks.ps1 -NiftyProfile trading -Python "$PWD\.venv\Scripts\python.exe"
```

With `-NiftyProfile trading` this registers only `\Nifty\Orchestrator`, at 09:10 daily
(interactive logon, no time limit). Keep both flags. Without them the script uses the
repository owner's defaults (the `full` profile and `C:\Program Files\Python313\python.exe`)
and also registers `\Nifty\DownloadAll` (22:00) and `\Nifty\StraddleCapture` (15:15),
which belong to the research stack.

**macOS (launchd):**

```bash
bash scripts/ops/register_scheduled_tasks_macos.sh
```

This registers `com.nifty.orchestrator` for Mon–Fri 09:10 *local time*. It uses
`.venv/bin/python` if present (override with `PYTHON=…`) and wraps the run in
`caffeinate` so the Mac stays awake while trading. If the Mac is asleep at 09:10,
launchd starts the job when it next wakes, which can be well after the open, and a
Mac that is off misses it. So schedule a wake:

```bash
sudo pmset repeat wakeorpoweron MTWRF 09:05:00
```

Remove it with `bash scripts/ops/register_scheduled_tasks_macos.sh --remove`. The
macOS path is written against the orchestrator's POSIX code paths and has not yet
been run on a real Mac. Please report anything that breaks.

**Linux:** a cron line such as
`10 9 * * 1-5 cd /path/to/quantifty && .venv/bin/python scripts/ops/run_if_session.py orchestrator`
starts it. cron has no desktop session, so the browser-login fallback cannot open.
Set up phone approval (below), with `NGROK_PATH=/full/path/to/ngrok` in `.env` because
cron's PATH is minimal, or open `http://127.0.0.1:5000/ops/login/upstox` yourself.
Like the macOS path, this has not been run on a real machine.

### Phone approval (optional, recommended for automation)

A scheduled 09:10 start needs a token, and a browser login needs you at the keyboard.
With phone approval, Upstox sends an approval request to your phone instead:

1. Install ngrok (`winget install ngrok.ngrok` / `brew install ngrok`), create a free
   account, run `ngrok config add-authtoken <token>`, and claim your free **static domain**.
2. In `.env`, set `UPSTOX_NOTIFY_DOMAIN` to that domain as a bare host with no
   `https://` (for example `my-name.ngrok-free.app`), and `NGROK_PATH` if `ngrok` is
   not on your PATH. `UPSTOX_NOTIFY_SECRET` was generated by `bootstrap.py init`.
3. In the Upstox developer console, set the app's **Notifier URL** to
   `https://<domain>/upstox/notify/<UPSTOX_NOTIFY_SECRET>`.

Then at 09:10 you tap **Approve** in the Upstox app or WhatsApp. If no token arrives
within 10 minutes the browser login opens as a fallback. Full detail:
[OPS_ORCHESTRATOR_RUNBOOK.md](docs/reports/ops_data/OPS_ORCHESTRATOR_RUNBOOK.md).

### Telegram alerts (optional)

Set `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` in `.env` to get alerts:
- when a phone-approval request goes out or fails;
- when no token arrives within 3 hours and the start is abandoned;
- when a scheduled run exits non-zero;
- from the trading session: kill switch on/off, stale data feed, refused start.

Without phone approval, nothing is sent at 09:10 when the token is needed. Without
the two variables, alerts are logged and skipped.

---

## Live trading

The platform separates **data mode** (`Mode.LIVE` / `REPLAY`) from **order mode**
(`ExecutionMode.PAPER` / `LIVE`). NiftyShield runs `Mode.LIVE` + `ExecutionMode.PAPER`.
Options-Wall reads live Upstox chains and simulates its trades in its own paper
executor, outside the execution layer, so it has no order mode at all.

The live switch is in `scripts/fno_runner.py::build_runner`
(`execution_mode=ExecutionMode.LIVE, broker=UpstoxAdapter(...)`). Since 2026-10-17
(PR #47) it builds a working driver. `UpstoxAdapter` accepts the handler's orders and
places them as MARKET orders, and `LoopDriver` polls Upstox for fills on every loop
iteration (`UpstoxAdapter.poll_fills`). **It has never placed a real order**: no funded
account exists, and every test stubs the HTTP layer. Orders go to Upstox's V3
place-order endpoint on `api-hft.upstox.com`. Live fills carry the handler's fee
estimate. After a restart, orders still open from earlier that day are found in the
Upstox order book and polled once before the startup reconcile, so a fill that landed
during the restart is booked. Any order that can't be found is named in a critical alert.
Known gaps remain:
- a partially filled order keeps only its first chunk in the `trades` table, and a
  partially filled exit is recorded there as a new entry, leaving the real entry row open;
- an order Upstox rejects or cancels stays open in the handler;
- an unexpected error from the adapter is still reported as a placed order. Refusals
  are typed, so the handler counts them and returns no order.

A placement's outcome can be unknown: a timeout, a dropped connection, a 5xx, or a reply
with no readable result or order id. That order is never resent. Each later fill poll
looks it up in the Upstox order book by its tag; once it is found there, its fills are
recorded. Until then every poll fails, and after three consecutive failing polls the
kill switch latches until a restart. New entries stop, but exits still go out.
The live guide lists every open item.

As written, `build_runner` with `ExecutionMode.LIVE` refuses to start without a valid
Upstox token. Only if `symbols` contains F&O keys (`NSE_FO|…` or `MCX_FO|…`) does it also refuse without
today's SPAN file and instrument-master coverage of the `underlyings` you pass. At
startup it reconciles the restored ledger against your Upstox positions and refuses to
start on a mismatch; it does not re-check during the session. That check compares
positions only. So it also alerts when the restored ledger holds an order from today that
is not recorded as filled, because nothing polls an order placed before a restart.
None of this has run against a real account yet.

NiftyShield and Options-Wall **cannot** be switched to live. Before you write a
live entry script of your own, read **[docs/guides/LIVE_TRADING.md](docs/guides/LIVE_TRADING.md)**.
It covers:
- **Upstox requires a registered static IP for order APIs from 1 April 2026**
  (SEBI retail-algo framework). Paper trading is unaffected.
- **Multi-leg orders are sent leg by leg as MARKET orders and are not atomic.** A
  rejected wing can leave a naked short.
- What the live path still lacks: the ledger gaps, fees, and Upstox endpoints that
  have not been checked.
- A pre-live checklist.

---

## Before you rely on it

- **The holiday calendar runs out on 2026-12-31.** From 2027-01-01 every scheduled
  run exits with code 2 and sends an alert until 2027 is added:
  - the 2027 NSE holidays go into `core/market/nse_holidays.py` and into NiftyShield's
    copy in `strategies/nifty_shield_v1/exchange_holidays.py` (a test fails if the two differ);
  - in `core/market/trading_calendar.py`, move `COVERAGE_LAST` to 2027-12-31 and add
    that year's special closures and weekend sessions;
  - editing NiftyShield's copy changes its execution hash, so re-pin
    `FROZEN_EXECUTION_HASH` and `WINDOW_START` in `scripts/nifty_shield_paper/identity.py`.

  Do this in December.
- **Special sessions** (Diwali Muhurat) must be added before they happen. Put the
  hours in `SPECIAL_SESSIONS` in `core/market/session_schedule.py`; otherwise the day
  gets the normal schedule (derivatives 09:15–15:40). If the session falls on a
  weekend, also add the date to `ADDITIONAL_SESSIONS` in
  `core/market/trading_calendar.py`; otherwise it is not a session at all and the
  scheduled jobs skip it.
- **Lot sizes and expiry weekdays change, and NiftyShield hard-codes both.** The lot
  size (65) is in `strategies/nifty_shield_v1/config.py` and again in
  `core/execution/options/nifty_shield_gates.py`. The risk declaration, the size gate,
  the basket-margin sizing and the order quantity itself (lots × 65) all use that
  number, so after a lot-size revision NiftyShield sends quantities that are not a
  whole number of lots. The expiry is computed as Tuesday, or the session before when
  Tuesday is a holiday (`INDEX_EXPIRY_WEEKDAY` in `structures.py`). When NSE changes
  the lot size, edit both lot-size files; when it changes the expiry weekday, edit
  `structures.py`. Either way, re-pin the execution hash.
- **The DayType label is a full-session prior, not an afternoon forecast.**
  See the [DayType guide](docs/guides/DAYTYPE_ENGINE.md).
- **`seed` verifies its result.** It exits non-zero if India VIX history is below
  189 sessions or any index has fewer than 5 sessions of 1m bars. Treat a failure as
  "the strategies will not behave as documented".

### Maintenance

| What | Why | How |
|---|---|---|
| Options-Wall stores | `data/options/wall_chain_snapshots/{date}.duckdb` takes about 70–90 MB per session; `wall_scan_results.duckdb` is a single file that keeps growing (about 450 MB after 30 sessions) | archive or delete old per-day snapshot files. With the stack **stopped**, `python scripts/ops/compact_duckdb_stores.py` reports what compaction would reclaim and `--apply` compacts. `--apply` keeps each original as `*.pre_compact_<ts>.duckdb`, so space comes back only when you delete those or add `--discard-baseline` |
| VIX history | NiftyShield's percentile window | refreshed by `bootstrap.py seed` (every morning under the trading profile) |
| Instrument master | lot sizes, expiries | refreshed by the orchestrator each morning. It appends one snapshot per trading day, so the file grows |

---

## Architecture

```
CLI scripts → DuckDB → core logic → facade → Flask UI
SignalSource ──SignalEvent──▶ ExecutionHandler (risk · sizing · margin) ──▶ PaperBroker | UpstoxAdapter
```

1. **Strategies stay dumb.** They emit `SignalEvent` only: no broker, sizing or risk logic.
2. **Analytics produce facts.** Strategies read stored facts and never compute
   indicators. NiftyShield's 13:00 DayType fact is published by a driver hook inside
   the session, just before the strategy reads it.
3. **Execution owns reality.** Risk, sizing and broker interaction live only in `core/execution/`.
4. **The runner is neutral.** One single-threaded loop; live and replay data treated identically.
5. **Audit first.** Every trade is explainable from recorded facts: journal, evidence package, replay.

NiftyShield runs on this path. The Options-Wall pilot is a separate poller with its
own paper executor (`core/options_wall/`): it does not go through `LoopDriver`,
`ExecutionHandler` or `PaperBroker`, and it sizes and exits its flies itself.

These five are the working rules from [CLAUDE.md](CLAUDE.md). The platform's founding
principles (ledger is truth, execution before alpha, determinism, risk before
trading, no trading on stale data) are in
[PLATFORM_CONSTITUTION.md](docs/PLATFORM_CONSTITUTION.md) ·
decisions: [ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md) ·
driver contract: [DRIVER_SPECIFICATION.md](docs/DRIVER_SPECIFICATION.md) ·
history: [CHANGELOG_PLATFORM.md](docs/CHANGELOG_PLATFORM.md).

### Key directories

| Path | Purpose |
|---|---|
| `core/auth/`, `core/brokers/` | Upstox credentials, token, adapters (Upstox, Paper), basket margin, instrument mapping |
| `core/instruments/` | canonical instrument model, resolver, master readiness |
| `core/execution/` | handler, risk, order groups, positions, reconciliation, NiftyShield execution |
| `core/risk/` | SPAN parser/calculator, ELM, `NseMarginEngine` |
| `core/analytics/`, `core/options_wall/` | options analytics, wall metrics, chain scanner, paper fly executor |
| `core/state/` | DayType regime engine |
| `core/runtime/` | `LoopDriver`, journal, telemetry, signal-source contract |
| `core/market/` | NSE holidays, trading calendar, session schedule |
| `strategies/nifty_shield_v1/` | NiftyShield signal source (frozen) |
| `flask_app/`, `app_facade/` | dashboard and its facades. No computation, but it can write the `STOP` file, queue an Options-Wall manual close, and save the Upstox login |
| `scripts/ops/` | orchestrator, preflight, scheduling, phone approval |
| `scripts/bootstrap.py` | first-run setup + daily seed |
| `models/daytype/` | trained DayType models (committed) |
| `docs/guides/` | how the strategies, DayType and live switch work |

### Data layout (created at runtime, git-ignored)

| Path | Written by |
|---|---|
| `data/instruments/nse_fo_instruments.duckdb` | instrument master refresh |
| `data/live_buffer/candles_today.duckdb` | market ingestor (today's 1m bars) |
| `data/market_data/nse/candles/{1m,1d}/{date}.duckdb`, `data/market_data/bse/candles/1m/{date}.duckdb` | `bootstrap.py seed` (one file per session; Sensex is 1m only) |
| `data/options/chain_cache.duckdb` | NiftyShield chain poller (marks) |
| `data/options/wall_chain_snapshots/{date}.duckdb` (one file per session), `data/options/wall_scan_results.duckdb` | Options-Wall poller |
| `data/nifty_shield/` | NiftyShield session: trade ledger, journal, execution store, 13:00 DayType facts (`facts.duckdb`), per-session evidence. `vix_history.duckdb` here is written by `bootstrap.py seed` |
| `data/signal_engine/trade_intelligence/trade_intelligence.duckdb` | `ExecutionHandler` fill recorder (every paper fill) |
| `data/span/` | NSE SPAN archive |
| `data/config/config.db` | dashboard users |
| `data/ops/` | orchestrator PID files, `scheduled_runs.log`, per-run logs under `data/ops/logs/` |
| `logs/` | runtime journals, metrics, service logs |

---

## Development

```bash
pip install -r requirements-dev.txt
```

```bash
python -m pytest tests -q
```

`requirements-dev.txt` pulls in `requirements-research.txt` (statsmodels,
matplotlib, …), because `tests/` also covers the research scripts. The pins in
`requirements.txt` are the versions the production machine runs. The live DayType
models are scikit-learn pickles, so the scikit-learn version is part of the model
contract (the engine warns on a mismatch). The LightGBM models in `models/daytype/`
are research artifacts that the live engine does not load.

## The research record

Most of `scripts/` and `docs/reports/` is a research programme: pre-registered
screens with train / holdout / sealed windows, and a power-feasibility gate (RFA)
that must pass before any construct code is written. Its results are recorded
whichever way they come out, and most constructs **failed**. Some examples:
- delivery-equity STT made sub-monthly (weekly and fortnightly) cash-equity signals uninvestable (PSB-1, PSB-2);
- monthly cross-sectional effects were too small to demonstrate in the years of data that exist (SFB-1, RFA);
- several index constructs died on statistical power.

One construct (Carry, residual basis on stock futures) passed its sealed read. A
later audit found it is a **spot** effect, though: futures convergence eats the
spread, so as a futures trade it does not survive. It needs NSE bhavcopy history and
has no live deployment. The audit is
`docs/reports/carry/CARRY_FUTURES_TRANSLATION_REVIEW.md`, and
`docs/reports/external/RESEARCH_CLOSURE_LEDGER_2026-09-29.md` lists every construct's
outcome. This history is why NiftyShield and Options-Wall are labelled paper-only.
