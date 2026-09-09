# MASTER_MATERIALIZATION_READINESS.md

**Type:** Readiness review — **no code changes; survey + verdict only.**
**Date:** 2026-06-08
**Phase:** inserted between 4C.5/G1 (wiring review done) and 4C.6–4C.8.
**Purpose:** answer one question the wiring review deferred — *how does the Instrument Master become a reliable, materialized production dependency?* The canonical layer (`InstrumentResolver`, `CanonicalInstrument`, `UpstoxMapping`) and the ingest script all exist and are green; the **master DB does not exist on disk**. This review scopes what materialization actually requires before 4C.7 ships resolved broker identity to live orders.
**Basis:** direct read of `scripts/fetch_instrument_master.py`, `core/instruments/resolver.py`, `core/instruments/instrument_db.py`, `core/data/options_provider.py`, `flask_app/blueprints/ops/routes.py`, `tests/instruments/test_resolver.py`, and `PHASE_4C_IMPLEMENTATION_PLAN.md` §6.1/§7.

---

## Verdict

**The architecture is materialization-ready; the *data* is not, and one historical-correctness gap cannot be closed by simply running the script.**

- Running `scripts/fetch_instrument_master.py` once materializes a *forward-only* snapshot series sufficient for **live** trading and **future** backtests.
- It is **not** sufficient for **historical** `as_of` correctness (e.g. the 2024 SEBI 50→75 lot revision the resolver was built to handle): the live source serves only today's master, so pre-capture dates degrade to the earliest snapshot with a logged warning.
- **Go for 4C.6** (dormant code; land on fixtures). **Conditional-go for 4C.7** — only after the DB is materialized *and* the second reader below is reconciled.

Two findings the 4C.5 wiring review did not surface (it grepped the `InstrumentMaster` class, not the DB **file**) lead this report.

---

## Finding 1 — The snapshot series is forward-only; historical `as_of` is correct-but-unfed

The resolver's point-in-time contract (`resolver.py:139-152`, `_pick_effective`) picks the snapshot with the greatest `snapshot_date <= as_of`, else the earliest snapshot **with a loud warning**. The schema (`fetch_instrument_master.py:51-66`, PK `(instrument_key, snapshot_date)`) accumulates one snapshot per daily run.

But the ingest fetches **only the current** master — `INSTRUMENTS_URL` is the single live `complete.json.gz` (`fetch_instrument_master.py:39,140`); there is **no dated/historical endpoint** in the code. Therefore the snapshot series accrues **forward only, from first capture**. A 2024 backtest (`as_of=2024-03-01`) against a DB first materialized in mid-2026 has no eligible snapshot → `_pick_effective` returns the earliest captured snapshot and warns (`resolver.py:147-151`). The lot_size it returns is *today's* (75), not the historically-correct one (50).

This is **observable, not silent** (Constitution §6 / ADR-004 honored), and the mechanism is correct — it is simply **unfed** for pre-capture dates. The test suite proves the mechanism by hand-writing two dated snapshots (`test_resolver.py:49-55`); production has no equivalent source.

**Open question this review surfaces (the real Q6 deliverable):** *Is there any source — Upstox archive, an internally retained history, or a manual SEBI-boundary backfill — from which pre-capture snapshots can be seeded?* If not, historical `as_of` correctness is bounded by capture-start date, and that bound must be documented as a known limitation of every backtest run before then.

## Finding 2 — There is a second, snapshot-blind reader of the master file (live code)

The wiring review concluded `InstrumentMaster`/`instrument_db.py` has **zero importers** — true for the *class*. But the DB **file** has a second live reader: `core/data/options_provider.py` opens `data/instruments/nse_fo_instruments.duckdb` directly by raw SQL (`options_provider.py:27,520-528,572-608,615-632`) for `get_weekly_expiry`, strikes, lot_size, and expiry lists — powering the live `/options/` dashboard.

These queries carry **no `snapshot_date` filter**. While the DB holds a single snapshot this is harmless. Once daily snapshots accumulate (the whole point of the schema), `SELECT DISTINCT expiry … WHERE name=?` spans all snapshots, and `get_lot_size … LIMIT 1` (`options_provider.py:607-608`) returns an **arbitrary snapshot's** lot — the exact snapshot-blindness flagged for the deprecated `InstrumentMaster` (`PHASE_4C_IMPLEMENTATION_PLAN.md` §6.1), but in **live** code. Materializing the master *activates* this latent bug.

**Implication:** materialization is not purely additive. Before/with 4C.7, `options_provider`'s reads must either filter to the latest `snapshot_date` or route through `InstrumentResolver`. This belongs on the 4C.7 precondition list alongside Gate G1.

---

## The seven readiness questions

**Q1 — Where is the source data obtained?**
A public Upstox CDN asset: `https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz` (`fetch_instrument_master.py:39`). **No auth** — plain `requests.get` (`:140`). The docstring's "Run once after OAuth login" (`:9`) is misleading: the fetch needs no token. (Consequence: CI and offline replay *can* fetch it directly if desired — see Q5/Q7.)

**Q2 — How often is it refreshed?**
Only when triggered — there is no scheduler in the repo. The sole trigger is the OAuth callback (`ops/routes.py:179-185`): on a fresh token it calls `refresh()`, commented "once per OAuth, not per restart." Whether this is *effectively daily* depends on Upstox token lifetime — **confirm operationally**: if access tokens expire daily (~03:30 IST, forcing re-login every trading day), the piggyback is reasonable and the script docstring's "each morning" holds. If tokens persist longer, the master can silently age. No repo code encodes the lifetime, so this is an operational fact to verify, not assert.

**Q3 — What happens if refresh fails?**
- Network/HTTP: `raise_for_status()` (`:141`) → exception caught at the ops route, flashed as a warning (`routes.py:184-185`); the OAuth flow still succeeds. No retry.
- Empty parse: `refresh()` logs an error and returns 0 **without writing** (`:182-183`) — the prior DB is preserved.
- Partial write: `write_snapshot` does `DELETE … WHERE snapshot_date=?` then `INSERT` as two auto-committed DuckDB statements (`:169-171`). A crash between them leaves *that* day's snapshot empty; **self-heals on the next run** (re-DELETE+INSERT). Low-probability, worth a single-statement transaction wrap if it ever bites.
- **Net:** failures are non-fatal and non-silent, but **nothing alerts** — a stale/absent master only shows up as resolver fallback warnings in logs.

**Q4 — Startup dependency or optional dependency?**
**Optional everywhere today.** Both readers degrade observably when the file is absent: the resolver logs once and returns `None` (`resolver.py:47-51`, never silently wrong); `options_provider` falls back to *calculated* expiries (`options_provider.py:535-541`); the selector falls back to `INDEX_LOT_SIZES` (per wiring review §1). So the master is a **soft** dependency now. **4C.7 changes this** — once orders ship resolved `instrument_key`, an absent master means an unroutable F&O order. Materialization must become a **hard startup precondition before 4C.7** (fail fast at boot if `is_loaded()` is false on a live F&O path), not a soft fallback.

**Q5 — How does replay work without internet?**
Cleanly. Fetch (script/ops route) and read (resolver) are fully separated: the resolver only ever opens the local DB `read_only=True` (`resolver.py:133`) and never reaches the network. Replay/backtest is offline **provided the DB was materialized beforehand**. The only caveat is Finding 1 — offline replay of *pre-capture* dates resolves against the earliest snapshot with a warning.

**Q6 — How does backtesting pin historical snapshots?**
By `as_of` → `_pick_effective` (`resolver.py:139-152`), and backtest call sites must pass an explicit `as_of` (plan §2 G1 evidence; constructor supports a fixed `as_of`, `resolver.py:42`). The *mechanism* is sound and tested. The *data* is the gap — see **Finding 1**: pinning is only truthful for dates on/after capture-start. Until a backfill source is found, every backtest before capture-start silently uses present-day contract attributes (with a log warning). This must be a documented limitation.

**Q7 — How does CI create test fixtures?**
Well — and this is the pattern to keep. `test_resolver.py:17,47` builds the fixture master through the **real ingest pipeline** (`parse_instruments` + `write_snapshot`) from hand-written raw dicts into a `tmp_path` DuckDB — **no network, no committed binary fixture**, and it exercises the real parser/schema. Gap: there is **no contract test** pinning the *live source* shape (field names like `strike_price` vs `strike`, `expiry` ms-vs-string at `:71-83,110-111`). A sampled-payload schema test would catch an upstream Upstox format change that the synthetic fixtures cannot.

---

## What materialization gates (sequencing)

| Slice | Gated by materialized DB? | Why |
|---|---|---|
| **4C.6** (greeks `asset_class` dispatch) | **No, for landing; yes, for live effect.** | Legacy `Instrument` exposes `.type` (`InstrumentType`), **not** `.asset_class` (`instrument_base.py:12-16`). The new dispatch target only flows when canonical flows (4C.7). 4C.6 can land DB-absent, fixture-tested, but is **dormant** until materialization. |
| **4C.7** (order seam → resolved `instrument_key`/product) | **Yes — hard precondition.** | The live behavior change. Requires: (a) DB materialized, (b) Gate G1 "No", (c) Finding 2 reconciled (options_provider snapshot-aware), (d) Q4 flipped to fail-fast. |
| **4C.8** (recon canonical↔canonical) | **Yes** (operationally dead today; additive). | Matches on resolved canonical ids — needs the master present to resolve broker positions. |

---

## Decisions (ratified 2026-06-08)

The owner reviewed this report and locked the following. Recorded here and in `PHASE_4C_IMPLEMENTATION_PLAN.md` §6.1 so they are not relitigated.

1. **Proceed to 4C.6** — greeks `asset_class` dispatch lands now (DB-absent, fixture-tested, dormant until canonical flows). Not gated by materialization.
2. **Finding 2 is a HARD BLOCKER for 4C.7** — `options_provider`'s snapshot-blind reads of the master file must be made snapshot-aware (filter to latest `snapshot_date`, or route through `InstrumentResolver`) *before* daily snapshots accumulate. 4C.7 does not start until this is closed.
3. **Historical backfill is a DOCUMENTED LIMITATION** (Finding 1 / Q6) — the live source has no dated endpoint, so the snapshot series is forward-only from first capture. Pre-capture `as_of` resolution returns the earliest snapshot with a logged warning. This is accepted, not solved; every backtest before capture-start carries this caveat. Reopen only if a backfill source surfaces.
4. **4C.7 precondition: materialized master + a staleness policy** — before the order seam ships resolved `instrument_key`, the master must (a) exist on disk and (b) have a defined refresh cadence + staleness alert (Q2/Q4); the soft fallback flips to fail-fast on the live F&O path.

**Net governance framing:** identity/resolver/mapping are done; the remaining risk is **instrument-data trust** (refresh cadence, snapshot hygiene, source-contract stability), not architecture. Decision 4's staleness policy and the Q7 source-contract test are the concrete next data-governance items, owned by the 4C.7 precondition work.
