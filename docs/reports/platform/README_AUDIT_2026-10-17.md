# README audit — 2026-10-17

**Scope.** The README on `main` still described the MM11-era platform (June/July 2026): MM11 "in progress", Python 3.10+, `data/market_data/options.duckdb`, `reference/span/`, no orchestrator, NiftyShield, Options-Wall or research record. Its replacement already existed in draft PR #43 (`docs/onboarding-readme`). That README documents files that exist only on that branch (`scripts/bootstrap.py`, the `trading` profile, `docs/guides/`), so it could not be moved to `main` on its own. This audit brings #43 up to date with `main` and re-verifies every claim in its README and guides against the merged code.

**Method.**
1. Merged `origin/main` (16 commits since 2026-10-09) into `docs/onboarding-readme`. One conflict in `scripts/ops/orchestrator.py`: main's `_wire_supervisor` and the PR's `_apply_profile` were both kept.
2. Checked the E008 execution hash on the merged tree: `101bae72…4791`, identical to `main` and to `FROZEN_EXECUTION_HASH`. No hashed file is touched by the PR.
3. Checked the `requirements.txt` pins against the production interpreter (Python 3.13.5): pandas 2.3.3, duckdb 1.4.3, pyarrow 22.0.0, requests 2.32.5, pytz 2025.2, numpy 2.4.4, scipy 1.17.0, scikit-learn 1.8.0, lightgbm 4.7.0. All match.
4. One checker per README section (nine in all) read the code behind each claim, about 314 claims in total. A skeptic then tried to refute each finding. Usage limits cut the skeptic pass short across two runs: 26 verdicts came back on 21 of the 58 findings. 16 findings were upheld in every verdict, 2 were refuted as pedantic, and 3 got split verdicts between runs (the SQLite and platform wording in the Stack line, and the "reference strategies" term); the rest got no verdict. Every finding acted on was re-checked by hand against the code.
5. A second, fresh three-checker pass over the rewritten README found more: L3, L4, Options-Wall ignoring `STOP` (O2), N1, and three live-guide gaps. All were confirmed in code and fixed; F-UPX-3 was confirmed by execution (`hasattr(UpstoxAdapter, "subscribe_fills")` is `False`).
6. `tests/ops`, `tests/database/test_writer_lock.py` and `tests/strategies/test_nifty_shield_v1_expiry.py` on the merged branch: 164 passed.

## Findings that change what a reader would do

*Status after the follow-up PRs merged (2026-10-17): L1, L3 and O2 are fixed on `main`. L4 is fixed for fill recording only: live fills now come from `UpstoxAdapter.poll_fills`. Its other two points still stand. Every order is MARKET, and `process_group_signal` has no production caller, so legs pass the gates one at a time (`LIVE_TRADING.md` gaps 1–2). L2 and N1 are still open. See "Not changed" below.*

| # | Finding | Evidence |
|---|---|---|
| L1 | **The live order path is not finished.** The README said real routing was "a single switch" in `build_runner`. In fact `UpstoxAdapter.place_order` reads `order.signal_id_reference`, which `NormalizedOrder` lacks, so it raises before any HTTP call. It also compares the side enum to `"BUY"`, so every order would go out as SELL. | `core/brokers/upstox_adapter.py:125-130`; recorded as F-UPX-1/2 in `tests/execution/test_g1_characterization.py:8-10, 29-30` |
| L2 | **A failed broker call is reported as placed.** `ExecutionHandler.process_signal` catches a generic broker exception, logs it, and returns the order. Group legs are logged and skipped. | `core/execution/handler.py:897-900, 976-978` |
| L3 | **A live run cannot even be built.** `ExecutionHandler.__init__` calls `broker.subscribe_fills`, which `UpstoxAdapter` lacks. They extend different `BrokerAdapter` bases (F-UPX-3), so `build_runner` raises before returning a driver. The live-rung tests use a mock broker. | `core/execution/handler.py:177`; `core/brokers/base.py` vs `broker_base.py`; `G1_WAVE2A_BROKER_PAYLOAD_REVIEW.md:58` |
| L4 | **Live fills would never be recorded.** `get_order_status` has no caller, and only `PaperBroker` produces fills. Every order is MARKET (`OrderType` has one member). `process_group_signal` has no production caller, so legs pass the gates one at a time. | `core/execution/order_models.py:17-18`; `handler.py:844-869, 906` |
| O1 | **`orchestrator.py stop` is not "stop everything".** It kills only flask, ingestor and session (the children with a pidfile). It leaves both pollers running, force-kills the session, and a running orchestrator respawns what it killed. *Fixed 2026-10-18: `stop` asks a running orchestrator to shut down, and it stops every child it started, the EOD worker and the TS combo book included, as at 15:50. `stop` then stops what is left (adopted children, or everything when no orchestrator was running or it had to be killed), both pollers included, and leaves the EOD worker and the TS combo book running and named. Only a session the running orchestrator started itself finishes cleanly; an adopted session, or one stopped with no orchestrator running or after the kill, is still killed without finalizing.* | `scripts/ops/orchestrator.py` `_cmd_stop` |
| O2 | **The `STOP` file stops NiftyShield, not Options-Wall.** A running NiftyShield session stops opening positions at its next signal, and every orchestrator start is refused until the file is deleted. But nothing in the Options-Wall poller reads `STOP`, so it keeps opening paper flies; the /ops/ kill button only writes the same file. | `core/execution/handler.py:601-609`, `orchestrator.py:224-227`; no `STOP` in `core/options_wall/` |
| N1 | **NiftyShield's order quantity uses the hard-coded lot size**, not the instrument master. After a lot revision it would send non-whole-lot quantities. | `core/execution/options/nifty_shield_handler.py:560, 601` |
| C1 | **Adding 2027 holidays now touches three files and the E008 hash.** Since 2026-10-13 NiftyShield keeps its own holiday copy, which is inside the execution hash. | `strategies/nifty_shield_v1/exchange_holidays.py` docstring; `identity.py` `EXECUTION_GLOBS` |
| C2 | **A missing Muhurat falls back to the CAS schedule (derivatives 09:15–15:40), not 09:15–15:30.** A weekend Muhurat also needs `ADDITIONAL_SESSIONS`, or the scheduled jobs skip it. | `core/market/session_schedule.py:32-37`; `core/market/trading_calendar.py:11, 34` |
| D1 | **The DayType fact path was wrong.** The live session writes `data/nifty_shield/facts.duckdb`; `data/features/day_type/day_type_facts.duckdb` is the offline publisher's default. | `scripts/nifty_shield_paper/session.py:221`; `flask_app/blueprints/nifty_shield.py:251-255` |
| D2 | **Options-Wall snapshots are per-day files** (`wall_chain_snapshots/{date}.duckdb`, 70–90 MB per session since late September), not the legacy single file. | `core/data/options_wall_store.py:36-44` |

## Other corrections

- Options-Wall bypasses `ExecutionHandler`, `LoopDriver` and the trade-intelligence recorder. Its time stop counts calendar days, so a weekend before expiry carries the fly into expiry day. Its pin test is "within 0.5 %", not "on the pin".
- NiftyShield sizes 2 lots (Choppy) or 1 (trend). Margin over 25 % of paper cash only cuts that back or skips the entry. Its weekly expiry moves to the session before a holiday Tuesday.
- The options dashboard shows no max pain and no IV smile. The basket-margin call is in `core/brokers/upstox_margin.py`, not `core/risk/`. Most risk gates are in `handler.py`, not `risk_manager.py`.
- `bootstrap.py seed` fetches SPAN from NSE Clearing's archive, not Upstox. `init` skips the instrument master on non-trading days. The redirect URL is also an `init` prompt.
- `run_if_session.py` copies target output to `data/ops/logs/<target>_<date>.log`. Without `-NiftyProfile trading`, the Windows registration also adds `DownloadAll` and `StraddleCapture`.
- launchd runs a job missed during sleep on the next wake (it is only missed when the Mac is off). The macOS script comment said otherwise and was corrected too.
- The live DayType engine loads only scikit-learn pickles. LightGBM models are research artifacts (requirements comment corrected).
- "Reference strategy" means the heartbeat canary in this repo (ADR-020), so the README now calls NiftyShield and Options-Wall "paper runners".
- PSB-2's casualties were fortnightly and monthly, not weekly. `CLAUDE.md`'s Carry section predates the futures-translation audit, so the README now points at the audit itself.

## Not changed (outside this audit)

- `CLAUDE.md` called Carry production-ready, `DEVELOPER_GUIDE.md` (root) described the pre-migration `D:\BOT\root` tree, and `NIFTY_MIGRATION_REPORT.md` was a June migration note at the root. *Since fixed on `main` by PR #46 (Carry banner, guide rewrite, report moved to `docs/archive/`) and PR #48 (stale Carry and ops paths).*
- L1–L4, O2 (Options-Wall ignores `STOP`) and N1 are code defects, and none of this audit's own commits fixes them. Two follow-up PRs were reviewed adversarially (`PR45_PR47_CODE_REVIEW_2026-10-17.md`), fixed the review's findings, and merged to `main` on 2026-10-17:
  - **#45** (`da4f78d`) fixes O2. The Options-Wall executor refuses new entries while `STOP` exists, and its farm-row badge shows **Kill switch**.
  - **#47** (`7391089`) fixes L1 and L3 (F-UPX-1/2/3) and the fill-recording half of L4 (live fill polling). L4's MARKET-only and non-atomic multi-leg points are unchanged (`LIVE_TRADING.md` gaps 1–2).
  - **Still open:** L2 and N1, both in E008-hashed files, and the gaps #47 lists (partial fills in `trades`, rejects left open in the handler, `fee=0.0`, no order-book re-seeding, `fno_runner` not creating `trades`).
  - **2026-10-18 follow-up (live path, outside the E008 hash):** `fee=0.0`, the missing order-book re-seed and `fno_runner`'s missing `trades` tables are fixed. A doc check against Upstox found that placement used a deprecated V2 endpoint on the wrong host, and that the tag could exceed Upstox's 40-character limit. Both are fixed too. L2 is narrowed: every definite refusal, including any failure before the order is sent, is now counted and returns no order. Only an exception the adapter does not classify, after the request is sent, is still reported as placed.
  - **Docs updated after both merges:** the README, `LIVE_TRADING.md` and `OPTIONS_WALL.md`.
