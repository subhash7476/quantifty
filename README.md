# quantifty — deterministic F&O trading platform for NSE, on Upstox

A Python platform for trading **Indian index derivatives (NSE F&O)** through
**Upstox**. It covers broker login, instrument master, live market data, an
NSE-rules margin engine, a risk-gated execution layer with a paper broker, and
options-structure dashboards. It ships with two **paper-trading reference
strategies** you can run the day you clone it.

**Stack:** Python 3.11+ (tested on 3.13) · DuckDB · Upstox API v2/v3 (REST + WebSocket,
no vendor SDK) · Flask + Tailwind · Windows, macOS, Linux

> **Paper by default. Nothing here is investment advice, and no strategy in this
> repository is validated for real money.** Live order routing exists but is off
> until you write code that asks for it. See [Live trading](#live-trading).

---

## What it does

| Capability | What you get | Where |
|---|---|---|
| **Upstox login** | OAuth browser login, CLI login, or **phone approval** (approve the daily token in the Upstox app or WhatsApp, no browser needed). Tokens expire at 03:30 IST and are refreshed every session | `core/auth/`, `scripts/ops/token_approval.py`, `scripts/auth_upstox_cli.py` |
| **Instrument master** | Daily snapshot of every NSE F&O / EQ / index contract from the Upstox CDN. Resolution is `as_of`-aware, so lot-size revisions resolve correctly | `scripts/fetch_instrument_master.py`, `core/instruments/` |
| **Live market data** | WebSocket feed (protobuf V3) → 1m bars in DuckDB. 5-second option-chain snapshots for Nifty, Bank Nifty and Sensex | `scripts/market_ingestor.py`, `scripts/nifty_shield_paper/chain_poller.py`, `scripts/options_wall_poller.py` |
| **Execution** | One `ExecutionHandler` for paper and live. Multi-leg order groups, position and P&L tracking, broker reconciliation, a restart-safe order store, and a universal fill recorder (`trade_intelligence.duckdb`) | `core/execution/` |
| **Risk** | Drawdown, trade-count and position gates; margin-utilisation cap; greek/delta flatten; stale-feed watchdog; kill switch (latched, auto-released only for a stale-feed trip); a `STOP` file that blocks starts | `core/execution/risk_manager.py`, `watchdog.py` |
| **Margin** | `NseMarginEngine`: SPAN (NSE v4.00 XML) + ELM + spread credits, from public NSE Clearing rules. Upstox basket-margin API for option structures | `core/risk/` |
| **Trade intelligence** | Options dashboard (PCR, net GEX, OI build-up, max pain, IV smile). Options-Wall board (gamma walls, pin, HHI, dealer hedge ladder, OI since open, ranked "farm list"). Per-trade evidence reports | `flask_app/`, `core/analytics/` |
| **Regime engine** | DayType: intraday Bull / Bear / Choppy classification at 10:00 / 11:00 / 13:00 from partial-session features. Trained models ship in the repo | `core/state/daytype_engine.py`, [guide](docs/guides/DAYTYPE_ENGINE.md) |
| **Ops** | One-command supervisor for the trading day: instrument master → dashboard → token gate → feeds → warm-up gate → session → 15:50 self-stop. Read-only preflight. NSE-holiday-aware scheduling on Windows and macOS. Telegram alerts | `scripts/ops/` |
| **Deterministic runtime** | Single-threaded `LoopDriver`: the same code runs live and replay, and every session writes a replayable evidence package | `core/runtime/`, `docs/DRIVER_SPECIFICATION.md` |

### The two paper runners

| | **NiftyShield** | **Options-Wall** |
|---|---|---|
| Underlying | Nifty 50 weekly options | Nifty, Bank Nifty, Sensex |
| When | once a session, entry 13:00–13:30, flat by 15:35 | any time 09:30–15:00; **holds overnight** until the session before expiry |
| Signal | DayType regime at 13:00 + India VIX percentile | positive dealer gamma, spot on the pin strike, ATM IV ≥ realized + 2 vol pts |
| Structure | bull put / bear call spread, iron fly, **or a short straddle / strangle (undefined risk)** | ATM iron fly, wings ±1.5 % |
| Exits | ±1σ P&L bracket, delta flatten, 15:35 | TP 25 % of credit, SL 50 % of max loss, time stop |
| Sizing | Upstox basket margin, ≤ 25 % of capital | 1 lot |
| How it works | [docs/guides/NIFTY_SHIELD.md](docs/guides/NIFTY_SHIELD.md) | [docs/guides/OPTIONS_WALL.md](docs/guides/OPTIONS_WALL.md) |

Both are **paper only**. NiftyShield is in a frozen forward paper window that exists
to find out whether it works. Options-Wall is a pilot.

---

## Quick start (Upstox)

**You need:**
- an Upstox account with F&O enabled;
- Python 3.11+ (3.13 tested). numpy 2.4, scipy 1.17 and scikit-learn 1.8 do not
  support 3.10;
- about 1 GB of disk to start. The trading stack does **not** need NSE bhavcopy
  history. The Options-Wall stores then grow by about 50–60 MB per session
  (see [Maintenance](#maintenance));
- a machine whose clock is on IST (Asia/Kolkata), or adjust the scheduled times.

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

It asks for your Upstox API key/secret and a dashboard username/password, then writes:
- `.env` with a fresh `SECRET_KEY`, `NIFTY_PROFILE=trading` and a generated phone-approval secret;
- `config/credentials.json`;
- the dashboard user in `data/config/config.db`;
- the `data/` tree and its empty stores;
- today's instrument master (`data/instruments/nse_fo_instruments.duckdb`).

It is safe to re-run: existing files are left alone.

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

This takes a few minutes and uses only Upstox, never NSE bhavcopy:
- ~3.5 years of Nifty / Bank Nifty / India VIX **daily** candles, which feed NiftyShield's VIX-percentile gate;
- the last ~10 days of index **1m** candles, which feed Options-Wall's realized vol;
- today's SPAN file.

Re-running fetches only what's missing. In the trading profile, the orchestrator
re-runs it every morning.

> Skip this step and nothing errors, but NiftyShield trades a short straddle on
> every Choppy day (its VIX gate has no history) and Options-Wall never enters
> (it has no realized vol).

### 6. Run a trading day

```bash
python scripts/ops/orchestrator.py
```

Start it before 09:15 IST. It:
1. refreshes the instrument master;
2. starts the dashboard;
3. waits for a valid token (phone approval, else the browser login);
4. starts the market feed and chain pollers;
5. parks until the derivatives market opens and the feeds are warm;
6. passes preflight;
7. runs the NiftyShield session and the Options-Wall poller;
8. stops itself at **15:50** (Ctrl+C stops it sooner).

| Check | Command / URL |
|---|---|
| Health (token, STOP file, marks, VIX, SPAN, master) | `python scripts/ops/preflight.py`. It reads `NIFTY_PROFILE`; the trading profile skips the `eod_feeds` and `eod_worker` checks, which track the bhavcopy research feeds |
| What would start | `python scripts/ops/orchestrator.py start --dry-run` |
| Dashboard | `http://127.0.0.1:5000/`: **/nifty-shield/**, **/options/**, **/options/wall/**, **/ops/** |
| Stop everything now | Ctrl+C in the orchestrator window, or `python scripts/ops/orchestrator.py stop` |
| Block the next start | create an empty file named `STOP` in the repo root |

`NIFTY_PROFILE=trading` (set in `.env` by step 3, or `--profile trading`) runs only
the trading stack. The default `full` profile is the repository owner's research
stack: it also starts a futures paper book and an EOD bhavcopy build worker that
need multi-GB NSE history you won't have.

---

## Automate it

The scheduler only has to start the orchestrator each weekday morning.
`scripts/ops/run_if_session.py` skips NSE holidays and weekends and logs to
`data/ops/scheduled_runs.log`. The orchestrator stops itself at 15:50.

**Windows (Task Scheduler)**, from the repo root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/ops/register_scheduled_tasks.ps1 -NiftyProfile trading -Python "$PWD\.venv\Scripts\python.exe"
```

This registers `\Nifty\Orchestrator` at 09:10 daily (interactive logon, no time limit).

**macOS (launchd):**

```bash
bash scripts/ops/register_scheduled_tasks_macos.sh
```

This registers `com.nifty.orchestrator` for Mon–Fri 09:10 *local time*. It uses
`.venv/bin/python` if present (override with `PYTHON=…`) and wraps the run in
`caffeinate` so the Mac stays awake while trading. launchd skips runs while the Mac
is asleep, so schedule a wake:

```bash
sudo pmset repeat wakeorpoweron MTWRF 09:05:00
```

Remove it with `bash scripts/ops/register_scheduled_tasks_macos.sh --remove`. The
macOS path is written against the orchestrator's POSIX code paths and has not yet
been run on a real Mac. Please report anything that breaks.

**Linux:** a cron line works the same way:
`10 9 * * 1-5 cd /path/to/quantifty && .venv/bin/python scripts/ops/run_if_session.py orchestrator`.

### Phone approval (optional, recommended for automation)

A scheduled 09:10 start needs a token, and a browser login needs you at the keyboard.
With phone approval, Upstox sends an approval request to your phone instead:

1. Install ngrok (`winget install ngrok.ngrok` / `brew install ngrok`), create a free
   account, run `ngrok config add-authtoken <token>`, and claim your free **static domain**.
2. In `.env`, set `UPSTOX_NOTIFY_DOMAIN=<your-domain>.ngrok-free.app`
   (`UPSTOX_NOTIFY_SECRET` was generated by `bootstrap.py init`).
3. In the Upstox developer console, set the app's **Notifier URL** to
   `https://<domain>/upstox/notify/<UPSTOX_NOTIFY_SECRET>`.

Then at 09:10 you tap **Approve** in the Upstox app or WhatsApp. If no token arrives
within 10 minutes the browser login opens as a fallback. Full detail:
[OPS_ORCHESTRATOR_RUNBOOK.md](docs/reports/ops_data/OPS_ORCHESTRATOR_RUNBOOK.md).

### Telegram alerts (optional)

Set `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` in `.env` to get alerts on token
requests, failed scheduled runs and start-up problems. Without them, alerts are
logged and skipped.

---

## Live trading

The platform separates **data mode** (`Mode.LIVE` / `REPLAY`) from **order mode**
(`ExecutionMode.PAPER` / `LIVE`). Both runners are live-data + paper-orders.
Real order routing is a single switch in `scripts/fno_runner.py::build_runner`
(`execution_mode=ExecutionMode.LIVE, broker=UpstoxAdapter(...)`). It refuses to start
without a valid token, SPAN file or instrument-master coverage, and it reconciles
against your real Upstox positions.

The two reference strategies **cannot** be switched to live. Before you write a
live entry script of your own, read **[docs/guides/LIVE_TRADING.md](docs/guides/LIVE_TRADING.md)**.
It covers:
- **Upstox requires a registered static IP for order APIs from 1 April 2026**
  (SEBI retail-algo framework). Paper trading is unaffected.
- **Multi-leg orders are sent leg by leg as MARKET orders and are not atomic.** A
  rejected wing can leave a naked short.
- A pre-live checklist.

---

## Before you rely on it

- **Holiday calendar runs out on 2026-12-31.** From 2027-01-01 every scheduled run
  exits with code 2 until the 2027 NSE holidays are added to
  `core/market/nse_holidays.py` and `core/market/trading_calendar.py`. Add them in
  December.
- **Special sessions** (Diwali Muhurat) must be added to `SPECIAL_SESSIONS` in
  `core/market/session_schedule.py` before they happen, or the day is treated as 09:15–15:30.
- **Lot sizes and expiry weekdays change.** NiftyShield's lot size (65) and Tuesday
  expiry are in `strategies/nifty_shield_v1/`. The instrument master is the source
  of truth.
- **The DayType label is a full-session prior, not an afternoon forecast.**
  See the [DayType guide](docs/guides/DAYTYPE_ENGINE.md).
- **`seed` verifies its result.** It exits non-zero if India VIX history is below
  189 sessions or any index has fewer than 5 sessions of 1m bars. Treat a failure as
  "the strategies will not behave as documented".

### Maintenance

| What | Why | How |
|---|---|---|
| Options-Wall raw snapshots | `data/options/wall_chain_snapshots/{date}.duckdb` + `wall_scan_results.duckdb` grow ~50–60 MB per session | archive or delete old per-day snapshot files; compact with `python scripts/ops/compact_duckdb_stores.py` (report) / `--apply` while the stack is **stopped** |
| VIX history | NiftyShield's percentile window | refreshed by `bootstrap.py seed` (every morning under the trading profile) |
| Instrument master | lot sizes, expiries | refreshed by the orchestrator each morning (it appends one snapshot per day) |

---

## Architecture

```
CLI scripts → DuckDB → core logic → facade → Flask UI
SignalSource ──SignalEvent──▶ ExecutionHandler (risk · sizing · margin) ──▶ PaperBroker | UpstoxAdapter
```

1. **Strategies stay dumb.** They emit `SignalEvent` only: no broker, sizing or risk logic.
2. **Analytics produce facts.** Indicators are computed and stored. Runtime is read-only.
3. **Execution owns reality.** Risk, sizing and broker interaction live only in `core/execution/`.
4. **The runner is neutral.** One single-threaded loop; live and replay data treated identically.
5. **Audit first.** Every trade is explainable from recorded facts: journal, evidence package, replay.

Governance: [PLATFORM_CONSTITUTION.md](docs/PLATFORM_CONSTITUTION.md) ·
decisions: [ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md) ·
driver contract: [DRIVER_SPECIFICATION.md](docs/DRIVER_SPECIFICATION.md) ·
state: [PROJECT_STATE.md](docs/PROJECT_STATE.md) · conventions: [CLAUDE.md](CLAUDE.md).

### Key directories

| Path | Purpose |
|---|---|
| `core/auth/`, `core/brokers/` | Upstox credentials, token, adapters (Upstox, Paper), instrument mapping |
| `core/instruments/` | canonical instrument model, resolver, master readiness |
| `core/execution/` | handler, risk, order groups, positions, reconciliation, NiftyShield execution |
| `core/risk/` | SPAN parser/calculator, ELM, `NseMarginEngine` |
| `core/analytics/`, `core/options_wall/` | options analytics, wall metrics, chain scanner, paper fly executor |
| `core/state/` | DayType regime engine |
| `core/runtime/` | `LoopDriver`, journal, telemetry, signal-source contract |
| `strategies/nifty_shield_v1/` | NiftyShield signal source (frozen) |
| `flask_app/`, `app_facade/` | dashboard (display only) and its facades |
| `scripts/ops/` | orchestrator, preflight, scheduling, phone approval |
| `scripts/bootstrap.py` | first-run setup + daily seed |
| `models/daytype/` | trained DayType models (committed) |
| `docs/guides/` | how the strategies, DayType and live switch work |

### Data layout (created at runtime, git-ignored)

| Path | Written by |
|---|---|
| `data/instruments/nse_fo_instruments.duckdb` | instrument master refresh |
| `data/live_buffer/candles_today.duckdb` | market ingestor (today's 1m bars) |
| `data/market_data/{nse,bse}/candles/{1m,1d}/{date}.duckdb` | `bootstrap.py seed` (one file per session) |
| `data/options/chain_cache.duckdb` | NiftyShield chain poller (marks) |
| `data/options/wall_chain_snapshots.duckdb`, `wall_scan_results.duckdb` | Options-Wall poller |
| `data/features/day_type/day_type_facts.duckdb` | 13:00 DayType fact publisher |
| `data/nifty_shield/` | NiftyShield ledger, journal, VIX history, per-session evidence |
| `data/span/` | NSE SPAN archive |
| `data/config/config.db` | dashboard users |
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
`requirements.txt` are the versions the production machine runs. The DayType
models are pickles, so `scikit-learn` / `lightgbm` versions are part of the model
contract.

## The research record

Most of `scripts/` and `docs/reports/` is a research programme: pre-registered
screens with train / holdout / sealed windows, and a power-feasibility gate (RFA)
that must pass before any construct code is written. Its results are recorded
whichever way they come out, and most constructs **failed**. Some examples:
- delivery-equity STT made weekly cash-equity signals uninvestable (PSB-1, PSB-2);
- monthly cross-sectional effects were too small to demonstrate in the years of data that exist (SFB-1, RFA);
- several index constructs died on statistical power.

One construct (Carry, residual basis on stock futures) passed its sealed read. A
later audit found it is a **spot** effect, though: futures convergence eats the
spread, so as a futures trade it does not survive. It needs NSE bhavcopy history and
has no live deployment. The details are in `CLAUDE.md` and `docs/reports/`.
This history is why the reference strategies here are labelled paper-only.
