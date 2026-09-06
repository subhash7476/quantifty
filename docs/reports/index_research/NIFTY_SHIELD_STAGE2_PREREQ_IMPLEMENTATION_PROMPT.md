# NiftyShield — Stage 2 Prerequisite Implementer Prompt (`nifty_shield_v1`)

**For:** DeepSeek V4 (implementer). **Author/reviewer:** Claude (role split — Claude writes the
prompt + reviews; DeepSeek implements). **Status:** **EXECUTABLE — §3 ratified by the operator 2026-08-08** (DS2-1 R-a, DS2-2 in-loop hook,
DS2-3 option (i) `vix_at_checkpoint`, DS2-4 skip+journal). **Do not begin coding before reading the
three docs in §1.** All §3 recommendations are now the ratified decisions.

**Goal:** stand up the one prerequisite that blocks Stage 2 forward PAPER — the DayType **live
13:00 regime fact**, produced from a live bar feed during the session and *readable by the
strategy at 13:00*. This does **not** run the PAPER validation window and grades **no alpha**
(that is E006, out of scope — see §7).

---

## 0. Read this first — the prerequisite is three things, not one

The operator scoped this as "the DayType live 13:00 publisher wired to a live bar feed."
Investigation (transcript 2026-08-08) shows it is **three coupled pieces**, one of which touches
the just-certified strategy:

1. **Producer wiring** — trigger `publish_live()` in the live loop at the 13:00 tick, off the
   live feed, *before* the strategy's `on_bar` runs. The script exists
   (`scripts/daytype/publish_live_fact.py`, committed); it is not wired to the runtime.
2. **Intraday VIX** — `publish_facts.vix_close()` reads the **1d EOD** store
   (`publish_facts.py:126`), which does not exist intraday → `publish_live()` returns *not-ready*
   on VIX **every live session** (`publish_live_fact.py:106-107`) and no live fact ever fires.
   This needs a real ~13:00 India VIX read — and that **changes what the `vix_close` column
   means** (see DS2-3).
3. **Consumer read-timing — a re-certification of `nifty_shield_v1`.** The certified source
   snapshots the *entire* facts table once in `on_start` (`strategies/nifty_shield_v1/source.py:42`,
   `facts.py:23`). Live, `on_start` runs at session start (~09:15) when today's 13:00 fact does
   not exist yet, so `self._facts.get(bar_date)` at the 13:00 bar returns `None` and the session
   is silently skipped (`source.py:61-64`). Fixing this **edits the certified package** (`ebfb7ec`,
   Ledger E005), so it re-opens the CONFORMANT grant. This is not a bug in Stage 1 — Stage 1 was
   certified in REPLAY, where the snapshot is always complete.

## 1. Read first (authoritative — this prompt does not restate them)
1. `docs/reports/DAYTYPE_FACTS_ADOPTION_SPEC.md` — §2 the two publishers, §4 fact schema/provenance,
   §5 Principle-#2 + the **parity claim** ("a live fact is byte-for-byte comparable with an offline
   fact for the same session bars") that DS2-3 puts at risk.
2. `docs/reports/NIFTY_SHIELD_DECOMPOSITION_SPEC.md` — §3 the SignalSource contract, §6 facts, §8
   D1–D5. The read-timing change must not alter §3.2 behavior on the frozen corpus.
3. `docs/strategies/nifty_shield_v1/datasheet.md` — **frozen at E005.** Identity triple, §10
   round-trip convention (load-bearing for §7 sequencing).
4. Contract + runtime code: `core/runtime/signal_source.py`, `core/runtime/conformance.py`,
   `core/runtime/driver.py` (the pre-signal hook at `:666-671`, `on_start` at `:608`, `on_bar`
   dispatch at `:686`), `core/events.py`.
5. Producer code: `scripts/daytype/publish_live_fact.py`, `scripts/daytype/publish_facts.py`,
   `core/state/daytype_engine.py`. Live feed/stores: `core/database/providers/live_market.py`,
   `core/database/ingestors/websocket_ingestor.py`, the live buffer `data/live_buffer/candles_today.duckdb`.

---

## 2. Preconditions (do not start until all hold)
- [x] **Operator has ratified §3** (DS2-1..DS2-4, 2026-08-08). Ratified as recommended.
- [x] **Intraday VIX substrate confirmed present** — `NSE_INDEX|India VIX` now carries **1m**
      intraday bars (verified 2026-08-07 file: 375 bars 09:15–15:29), alongside `NSE_INDEX|Nifty 50`,
      `NSE_INDEX|Nifty Bank`, and ~200 constituents (DeepSeek data refresh, 2026-08-08). The DS2-3
      intraday VIX read has a real source; it is no longer a data-blocked item.
- [ ] Dedicated branch off `main` at or after the E005 merge (`5594470`). `strategy_id` stays
      `nifty_shield_v1` throughout (a re-certification is the *same* strategy at a new `code_ref`,
      **never** a new `strategy_id`, MM12.5 §5.2).
- [ ] The offline facts publisher and the Stage-1 CONFORMANT package are unchanged on `main`.

---

## 3. Decisions (operator ratifies before execution — recommendations given)

Same pattern as the Stage-1 D1–D5 and the DayType DT1–DT5. **All four RATIFIED as recommended
(operator, 2026-08-08)** — the text below keeps the reasoning; the chosen option is marked on each.

### DS2-1 — Consumer read-timing = re-certification (the load-bearing decision) — **RATIFIED (R-a)**
The certified source reads a start-of-run snapshot; live it cannot see today's 13:00 fact.
- **RATIFIED (R-a):** make the reader **lazy / re-queryable** — `on_start` stores the
  `RegimeFactsReader`; at the 13:00 bar the source queries `reader.fact(bar_date)` (per-session
  cached, re-queries the facts DB on a miss). On the frozen corpus every session's fact is already
  present, so this is a **provable no-op offline**.
- **Acceptance gate for R-a (state as a gate, not an assumption):** at the new `code_ref`, the
  frozen-corpus conformance must still pass — **replay-twice byte-identical 16-signal stream**,
  **guard-wrapped suite green**, and **`config_hash` unchanged (`c5b722ff…536c`)**. If all three
  hold, the change is a re-certification of the same identity at a new `code_ref`; if any moves,
  R-a is *not* a no-op — **stop and report**, do not ship.
- **Rejected:** (b) driver re-invokes `on_start` mid-session (lifecycle abuse); (c) driver-owned
  fact injection into the source (over-engineered, breaks the read-only-input boundary).

### DS2-2 — Producer trigger seam — **RATIFIED**
- **RATIFIED:** use the driver's existing **pre-signal per-tick seam** (`driver.py:666-671`).
  It already fires *after clock advance, before signal routing* — the exact ordering the publish
  needs (write the fact, then `on_bar` at `:686` reads it). It currently self-disables after one
  call (`rebalance_done`); the prerequisite needs a **per-session** variant that fires at the 13:00
  tick each session. Reuse-vs-sibling-hook is the implementer's call **subject to review** — the
  requirement is: fires once per session, at/after the 13:00 bar's tick, before `on_bar`,
  in-process. **No external cron/scheduler** — a second process cannot guarantee ordering against
  the loop, which is the whole point.

### DS2-3 — Intraday VIX source + the parity/semantics question — **RATIFIED (i)**
`vix_close()` must read a real ~13:00 India VIX (not the EOD 1d store). But offline rows carry an
**EOD** `vix_close` and live rows would carry a **13:00** value — same column, meaning that
depends on `produced_by`. That breaks the spec §5 parity property.
- **RATIFIED (i):** add a **distinct, nullable field** `vix_at_checkpoint` so the fact's meaning
  never depends on `produced_by`. **Source (verified present):** the India VIX **1m** series
  (`NSE_INDEX|India VIX`), read up to the 13:00 bar exactly as NF/BN are — the last 1m close at or
  before 13:00. The legacy `vix_close` keeps its EOD meaning (do not change it).
- **Interaction with the DS2-1 no-op gate — read carefully, this is the trap.** The re-certified
  source must gate on `vix_at_checkpoint` **when present, else fall back to `vix_close`**
  (`vix = fact.get("vix_at_checkpoint") or fact.get("vix_close")`). Then:
  - The **frozen conformance corpus** (`strategies/nifty_shield_v1/corpus/facts.csv`) is **NOT
    regenerated** — it carries no `vix_at_checkpoint`, so the source falls back to its existing EOD
    `vix_close` and the 16-signal stream stays **byte-identical**. That is what keeps DS2-1 a
    provable no-op.
  - **Live** facts carry `vix_at_checkpoint`, so the live gate uses the true 13:00 VIX.
  - **Consequence to state plainly:** the intraday-VIX gating is a **live-only behavior, never
    exercised in conformance** — it is validated in E006 PAPER, and is explicitly **not** claimed
    equivalent to Stage-1's EOD-VIX gating. Do **not** backfill `vix_at_checkpoint` into the corpus
    to "make it consistent" — that would change the certified stream and break the re-cert.
- **Operator note (behavioral, already acknowledged):** the certified VIX gates
  (`vix_skip_above`/`vix_reduce_above`/`iron_fly_vix_above`) now act on a 13:00 VIX in live rows —
  a semantics change the `config_hash` cannot detect. It is a PAPER observation to record, not a
  config edit.
- *(Rejected (ii): overloading `vix_close` with `produced_by`-dependent meaning.)*
- **Operator note (behavioral, flag even if you pick (i)):** the certified VIX gates
  (`vix_skip_above` 20.0 / `vix_reduce_above` 16.0 / `iron_fly_vix_above` 14.0, datasheet §2) were
  certified against **EOD** VIX. Feeding them a **13:00** VIX changes the gates' effective behavior
  even though the config dict — and thus `config_hash` — is untouched. This is a semantics change
  to a frozen config that the config hash cannot detect; it is a Stage-2 PAPER observation to
  record, not a config edit.

### DS2-4 — "Not ready at 13:00" behavior — **RATIFIED**
Missing/late/thin NF or BN bars, or VIX unavailable → the publisher **writes nothing** and the
source **reads no fact and skips the session** (existing `source.py:61-64` path; do **not** weaken
the F2 NULL-VIX skip). **No improvised retry/backfill** that shifts entry timing. Every skipped
session must be **visible in the PAPER journal** (a skipped-entry line), not silently dropped —
per the CLAUDE.md lesson that a freshness value printed-but-never-asserted is not a control.

---

## 4. Deliverables

**A. Producer wiring (DS2-2).** The per-session pre-signal hook that invokes `publish_live()` at
the 13:00 tick, off the live runtime's feed, before `on_bar`. Single process, deterministic
ordering. If wiring this requires editing `core/runtime/driver.py`, that edit is in-scope **only**
as a clean additive seam and must be flagged for review; the driver is not in the Feature-Frozen
table, but a contract change to it is a review item, not a silent edit.

**B. Intraday VIX (DS2-3).** A new nullable `vix_at_checkpoint` fact field, populated from the
**India VIX 1m** series (`NSE_INDEX|India VIX`, last close ≤ 13:00) — the same read shape already
used for NF/BN, not the 1d EOD store. The live publisher reads today's NF+BN **and** India VIX 1m
from the **live** store (`candles_today.duckdb` / `live_market` provider), never a per-day EOD store
that only exists after close. `RegimeFactsReader` must surface `vix_at_checkpoint` alongside the
existing columns.

**C. Consumer read-timing (DS2-1).** The lazy/re-queryable reader in `facts.py` + its use in
`source.py`, with the VIX gate reading `vix_at_checkpoint or vix_close` (DS2-3). **Do not regenerate
the frozen corpus** (`corpus/facts.csv`) — its absence of `vix_at_checkpoint` is what makes the
fallback path byte-identical. Re-run the **full frozen-corpus conformance** and meet the DS2-1
acceptance gate (replay-twice byte-identical, guard-wrapped green, `config_hash` unchanged).

**D. Parity + determinism.**
- A **live-publish parity test**: a live fact and an offline fact over *identical* session bars are
  byte-identical on all shared columns (regime, confidence, provenance triple); VIX per the DS2-3
  decision.
- The frozen-corpus **replay-twice** and **guard-wrapped** conformance still green at the new
  `code_ref` (the DS2-1 gate) — this is the proof the re-cert is a behavioral no-op offline.

**E. Hand-back (grants nothing).** Record the new `code_ref`. Propose the datasheet `code_ref`
update (identity triple: same `strategy_id`, same `config_hash`, new `code_ref`) for the operator
to apply at the re-grant. **Do not file the ledger entry** — the CONFORMANT re-grant is the
operator's, exactly as E005 was. The implementer proposes with evidence.

## 5. Hard constraints (non-negotiable)
- **Principle #2:** classification runs in the publisher, never in the source. The source stays
  dumb — it reads a fact, it never computes a regime.
- **Do not weaken the F2 NULL-VIX skip.** VIX-less session → no fact → no entry.
- **No live Upstox order placement.** PAPER path only.
- **Do not modify any frozen platform component** (CLAUDE.md Feature-Frozen table). The DayType
  model files, `NseMarginEngine`, and the SPAN stack are untouchable here.
- The read-timing change must be a **provable offline no-op** (DS2-1 gate). A change that moves the
  frozen-corpus signal stream is out of bounds — stop and report.
- **OSC prohibition still stands:** never read the unread index-options window 2016-02-11 →
  2022-12-31. This prerequisite touches live/forward data only.

## 6. Acceptance = Stage 2 unblocked, re-cert ready
1. Live 13:00 fact produced from the live feed, `produced_by=live`, with an intraday VIX per DS2-3,
   written before `on_bar`, and **read by the source at the 13:00 bar** in a live/PAPER dry-run.
2. Live↔offline parity test green (shared columns byte-identical).
3. Re-cert gate met: frozen-corpus conformance L1+L2 green **raw + guard-wrapped**, replay-twice
   byte-identical, `config_hash` unchanged, new `code_ref` recorded.
4. Hand-back package for the operator's CONFORMANT re-grant (§4E). Implementer grants nothing.

## 7. Explicitly out of scope
- **The E006 PAPER validation window itself.** And note the sequencing: **E006 does not begin
  until the re-grant lands.** If the source `code_ref` changes mid-window, the datasheet §10
  round-trip count is being accumulated against two different `code_ref`s, which invalidates the
  window. Sequence is fixed: **re-certify first, then start counting.**
- Alpha, P&L presented as validation, the go-live checklist, LIVE order placement.
- `sweep_filter` — excluded from this identity (assessment §5.4).
