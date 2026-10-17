# Developer Guide

**Last verified against the tree:** 2026-10-17

A short map of the repository for someone who has just cloned it. This file used to describe the
pre-migration `D:\BOT\root` tree (`core/runner.py`, `expansion_v3`, `signals.db`); none of that exists
any more, and it was rewritten on 2026-10-17. For depth, follow the pointers below rather than
expecting this page to hold the detail.

**Where to read next**

| Need | Read |
|---|---|
| What the project is, how to run it | [README.md](README.md) |
| Rules and current research status (authoritative, long) | [CLAUDE.md](CLAUDE.md) |
| Current truth in five minutes | [docs/SESSION_BOOTSTRAP.md](docs/SESSION_BOOTSTRAP.md) |
| Architectural principles and invariants | [docs/PLATFORM_CONSTITUTION.md](docs/PLATFORM_CONSTITUTION.md), [docs/ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md) |
| The runtime loop contract | [docs/DRIVER_SPECIFICATION.md](docs/DRIVER_SPECIFICATION.md) |
| Where each DuckDB store lives | [docs/DATA_STORE_MAP.md](docs/DATA_STORE_MAP.md) |
| History | [docs/CHANGELOG_PLATFORM.md](docs/CHANGELOG_PLATFORM.md), [docs/archive/](docs/archive/) |

## What this is

A deterministic trading platform for NSE derivatives: Python, DuckDB as the single source of truth,
Upstox V2 as the broker, a thin Flask UI. It is strategy-agnostic infrastructure — **no strategy is
promoted to production** (see the status sections of `CLAUDE.md`). Strategies in `strategies/` and
`core/strategies/` run in research, replay or PAPER only.

## Architecture in one picture

```
CLI scripts (scripts/)  ->  DuckDB stores (data/)  ->  core logic  ->  app_facade/  ->  flask_app/
```

Runtime flow for a strategy:

```
bars (DuckDB, causal)  ->  LoopDriver (core/runtime/driver.py)
                              |  calls SignalSource.on_bar(bar)         (core/runtime/signal_source.py)
                              v
                          SignalEvent (core/events.py)   -- intent only
                              v
                          ExecutionHandler (core/execution/handler.py)
                              risk -> sizing -> broker
                              v
                          PaperBroker / UpstoxAdapter (core/brokers/)
```

The five principles (full text in `CLAUDE.md`):

1. **Strategies stay dumb** — emit `SignalEvent` only; no broker, sizing or risk logic.
2. **Analytics produce facts** — indicators are computed offline; runtime reads them.
3. **Execution owns reality** — risk, sizing and broker interaction live in `core/execution/`.
4. **The runner is neutral** — `LoopDriver` is the sole, single-threaded orchestrator; live, replay and
   backtest are treated identically.
5. **Audit-first** — every trade must be explainable by exact analytical facts.

## Directory map

| Path | Contents |
|---|---|
| `core/runtime/` | `LoopDriver`, signal-source contracts, conformance harness, telemetry, event journal |
| `core/execution/` | Handler, risk manager, position/order trackers, reconciliation, watchdog; sub-packages `equity/`, `futures/`, `options/`, `portfolio/` |
| `core/brokers/` | `PaperBroker`, `UpstoxAdapter`, canonical-to-Upstox instrument mapping in `mapping/` |
| `core/instruments/`, `core/market/` | Instrument master and resolver; trading calendar, holidays, session schedule |
| `core/data/`, `core/database/` | Data providers and the DuckDB manager, schema, writers |
| `core/analytics/`, `core/risk/` | Options analytics (PCR, GEX, OI, max pain); margin (`NseMarginEngine`, SPAN) |
| `core/options_wall/` | Intraday option-chain scanner and its paper executor (pilot) |
| `core/strategies/` | `carry_strategy.py`, `knowledge_signal_source.py` — emitters only |
| `strategies/nifty_shield_v1/` | The NiftyShield `SignalSource` package (factory `build_signal_source`, `config.py`, `facts.py`, `source.py`, `structures.py`) |
| `flask_app/`, `app_facade/` | Display-only UI (blueprints under `flask_app/blueprints/`) and its bridge to core |
| `scripts/` | CLI entry points: ingestion, runners, research harnesses (one sub-folder per research track) |
| `scripts/ops/` | Operations: `orchestrator.py`, `preflight.py`, `run_if_session.py`, `token_approval.py`, `register_scheduled_tasks.ps1` |
| `governance/` | Pre-registrations and frozen RFA declarations (`governance/rfa/`) |
| `tests/` | One directory per domain (`runtime/`, `execution/`, `options_wall/`, `ops/`, ...) |
| `docs/` | Architecture, runbooks, research reports (`docs/reports/`), strategy datasheets (`docs/strategies/`) |

## Setup and common commands

Python 3.10+; dependencies are in `requirements.txt` and `pyproject.toml`. Secrets and Upstox
credentials come from `.env` (never commit it).

```bash
pip install -r requirements.txt
python -m pytest tests/runtime tests/execution     # a domain at a time; the full suite is large
python scripts/run_flask.py                        # Flask UI (host/port from FLASK_HOST / FLASK_PORT)
python scripts/ops/preflight.py                    # read-only health check of the trading window
python scripts/ops/orchestrator.py                 # one-command PAPER trading-window supervisor
```

The orchestrator, its scheduled starts, the token-approval flow and its failure modes are documented
in `CLAUDE.md` ("Ops") and the runbook `docs/reports/ops_data/OPS_ORCHESTRATOR_RUNBOOK.md`. Strategy
and pilot runbooks: `docs/strategies/nifty_shield_v1/PAPER_WINDOW_RUNBOOK.md` and
`docs/reports/strategies/OPTIONS_WALL_PILOT_RUNBOOK.md`.

## Conventions that bite

- **Read a file before changing it**; prefer editing to creating; no backwards-compatibility shims.
- **Validate with a train/test split and walk-forward.** In-sample numbers mean nothing here, and
  several research windows are sealed — do not read them without the governing protocol.
- **Mutate a source-of-truth store only from committed, re-runnable code**, taking the baseline copy
  first. Many past defects in `CLAUDE.md` ("Known Pitfalls") are silent data-store problems.
- **Filter `is_synthetic = FALSE`** on 1-minute bars from 2026-08-03 onward (Closing Auction Session
  carry-forward bars), and never join the 1-minute store (corporate-action adjusted) to bhavcopy
  prices (as-traded) across a corporate action.
- **Windows:** `taskkill` from Git Bash fails silently — use PowerShell `Stop-Process` and confirm the
  process is gone before restarting a single-writer DuckDB process.
- **Do not leave `F:\Nifty` on a branch other than `main`** if the orchestrator uses that checkout;
  work in a worktree or separate clone.
- Commit messages: `<type>: <description>` with types `feat, fix, refactor, docs, test, chore, perf, ci`.
