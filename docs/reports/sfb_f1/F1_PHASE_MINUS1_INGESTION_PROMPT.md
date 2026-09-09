# F1 / SFB-1 — Phase −1 Implementer Prompt: Futures Substrate Ingestion & Certification

**For:** the implementer (DeepSeek V4), per the standing role split — *implementer builds from this written prompt; Claude writes the prompt and reviews; the operator decides.*
**Governing pre-registration:** `docs/reports/F1_PHASE_0_PRE_REGISTRATION.md` (DRAFT stub, §6 substrate gate).
**Authorization:** operator authorized forward motion 2026-07-18. This is a **Phase −1** step — it sits *outside and before* the SFB-1 battery, so it does not violate operator decision **D4** ("no new ingestion *inside* a battery"). D4 is lifted **for this pre-battery ingestion step only**.
**Sequencing:** Phase −1 (this) → protocol freeze (`F1_PROTOCOL.md`) → Phase 1 harness → candidate score. **No freeze, no scoring, no signal, and no sealed read happen here.**

---

## §0 Why this precedes the freeze

The F1 protocol cannot be frozen until the data's *structure* is known, because two pinned defaults are structure-dependent:
- the **volume/OI-confirmed roll trigger** requires OI history to exist in NSE's archive (calendar-roll is the declared fallback if it does not);
- the **F&O-eligible universe** requires a usable historical eligibility source.

Reading these structural facts is **not** reading path/return data — it reads column presence and date coverage only. That distinction is what makes Phase −1 legitimate before a pre-registration freeze. Nothing in this step computes a forward return, an excursion, or a candidate score.

---

## §1 Objective

Build and **certify** a research substrate for single-stock futures, to the same evidentiary standard as the PSB `equity_bhavcopy_adjusted` substrate (contract-shaped certification, zero structural filters, disposition register the only exclusion path). Three data assets + one cost model + one certification suite.

---

## §2 Prohibitions (hard)

- **No candidate scoring, no signal, no factor, no bracket logic.** Nothing lands in `core/strategies/`.
- **No forward-return / excursion / path computation** on any window. Certification reads structure (columns, grain, seams, dates) only.
- **No sealed-window path read.** The 2023→present window may be *ingested and structurally certified*, but every scoring-facing loader built later must assert `MAX(date)` fences (CSMP convention). Phase −1 itself computes no returns on any window.
- **Copy-first discipline** — validate-then-apply; never mutate a raw store in place (PSB `repair_*` convention).
- **Deterministic** — same inputs → byte-identical outputs; no wall-clock, no network nondeterminism baked into stored artifacts.

---

## §3 Research-first (mandatory before writing ingestion code)

Per repo development-workflow §0: confirm the **exact current NSE historical F&O source and format before writing a parser.** Known moving part: NSE migrated F&O bhavcopy from the legacy `fo<DDMMYYYY>bhav.csv.zip` format to the **UDiFF** (`BhavCopy_NSE_FO_0_0_0_<YYYYMMDD>_F_0000.csv.zip`) format in mid-2024, so a 2012→present series **spans two formats** and the parser must handle both. Verify against NSE's live archive / a maintained vendor library (GitHub search first, vendor docs second) rather than assuming a schema. Record the confirmed source + format boundary in the certification report.

---

## §4 Deliverables

### D1 — Raw ingestion
- Ingest NSE F&O bhavcopy (stock-futures rows: instrument `FUTSTK`, plus index futures `FUTIDX` for NIFTY/BANKNIFTY context) into a raw DuckDB store under `data/market_data/` (mirror the `bhavcopy_raw` layout).
- Grain: one row per `(underlying_symbol, expiry_date, trade_date)`. Preserve **all** expiries per underlying per day (near / next / far) — the roll builder needs them. Preserve OHLC, settle price, contracts/volume, and **OI** if present.
- No adjustment, no filtering at this layer — raw is raw.

### D2 — Continuous roll-adjusted series (`stock_futures_continuous`)
- For each underlying, build a **near-month continuous series** with a pinned, deterministic roll rule:
  - **Roll trigger (default):** roll near→next on the first session next-month traded-volume (or OI, if present) exceeds near-month, **capped at expiry-day close** (never hold past expiry). If neither volume nor OI history is usable, fall back to **calendar roll at T−1 before expiry** and record the fallback in the certification report.
  - **Back-adjustment:** **ratio (proportional)** — on each roll date, scale the entire pre-roll history by `next_price / near_price` at the roll boundary so the splice introduces no artificial gap. Ratio (not difference) because F1's brackets are ATR-relative (§5 of the pre-registration).
- Emit `(symbol, trade_date, adj_open, adj_high, adj_low, adj_close, roll_flag)`; `roll_flag` marks splice dates for the certification seam test.

### D3 — Point-in-time F&O-eligible universe (`fo_eligible_intervals`)
- Time-varying set of underlyings with liquid single-stock futures, as `(symbol, valid_from, valid_to)` half-open intervals (mirror `symbol_entity_intervals`).
- Source: NSE's historical F&O securities list / eligibility notices. Membership at any formation date = the interval covering that date. **No lookahead** — a name's eligibility on date *t* uses only information available at *t*.

### D4 — Era-accurate futures fee model (`core/execution/futures/futures_fees.py`)
- Analogue of `core/execution/equity/delivery_fees.py`. **Pin a model, not the ~6–8 bps constant.** Include, per era: futures STT (**sell-side only**, derivatives rate), exchange transaction charges, SEBI turnover fee, GST, stamp duty (buy-side, post-2020 uniform regime), and clearing. Rate-schedule boundaries per known regulatory-change dates. Expose `futures_fees(side, notional, trade_date).total`.
- **Slippage/impact is separate** (a harness concern, not this module) — but leave a documented seam for a concentration-aware κ so §7 of the pre-registration can plug in.

### D5 — Certification suite (`scripts/sfb/certify_futures_substrate.py`) — contract-shaped, unfiltered
One contract, arms that each return **0 undocumented violations** (disposition register the only exclusion), mirroring the PSB four-arm discipline but futures-appropriate:
- **Arm F-A — Roll-seam continuity.** Ratio-adjusted series has no fabricated jump at any `roll_flag` date beyond a declared tolerance; adjacent-day adjusted return at a splice equals the true near→next economic return, not the raw contract gap.
- **Arm F-B — Contract-grain integrity.** `(underlying, expiry, trade_date)` unique in raw; near-month selection in D2 is monotonic in expiry and never selects an expired contract.
- **Arm F-C — No-lookahead roll.** Every roll decision uses only data available at/before the roll date (no future volume/OI leak).
- **Arm F-D — PIT universe correctness.** `fo_eligible_intervals` reproduces the historical eligible set at spot-checked dates; no member is active before its inclusion notice or after its exclusion.
- **Arm F-E — Fee-era boundaries.** `futures_fees` returns the correct rate on each side of every pinned regulatory-change date.
- **Structural guard:** arms run with **zero filters** — the whole panel, entity grain — so a defect cannot hide behind a `WHERE`.

### D6 — Certification report (`docs/reports/F1_SUBSTRATE_CERTIFICATION.md`)
Script-generated. Row counts, date coverage per underlying, format-boundary date, roll-rule actually used (default vs. calendar fallback) per name, and every arm's pass/violation count. No hand-edited numbers.

---

## §5 Falsifiable pre-run predictions (state before running each arm)
Per repo testing discipline (a falsifiable prediction stated before the run):
- Arm F-A: adjusted return at every `roll_flag` splice is within tolerance of the economic roll return — predict **0** seams exceeding tolerance in a clean build.
- Arm F-C: predict **0** roll decisions referencing future data.
- If any arm fails, **stop** — the substrate is not certified, and no freeze/scoring proceeds. A failing arm is a substrate defect to repair (copy-first), not a threshold to relax.

---

## §6 Acceptance / stop rules
- Substrate is **certified** iff D5 arms all return 0 undocumented violations and D6 is generated from the scripts.
- Only a certified substrate unblocks the protocol freeze (`F1_PROTOCOL.md`).
- Tests: `tests/sfb/` — arm unit tests + fee-model era unit tests, green before certification is claimed.

## §7 What Claude reviews (not implements)
Lead review of: the roll-rule determinism, Arm F-A tolerance justification (a loose tolerance can launder a real seam), the no-lookahead proof in Arm F-C, the fee-model era boundaries against source, and the PIT universe's lookahead safety. ACCEPT / findings, same as the PSB lead-review lineage.

---

## §8 Provisional design pins carried to freeze (recorded, not yet frozen)
These path-independent §11 items are **provisionally** pinned now and become immutable at `F1_PROTOCOL.md` freeze (post-certification); the operator may amend any before the first candidate result exists, per the PSB §9 "immutable only after a result exists" convention:
- Factor: **12-1 cross-sectional momentum** (reversal is the declared single alternative). Concentration **N ≤ 10, equal-weight**.
- Windows: **TRAIN 2012–2018 / HOLDOUT 2019–2022 / SEALED 2023→present.**
- Brackets: **ATR-scaled `(k_sl, k_tp, n)`**, grid pinned at freeze, selected on TRAIN only.

Structure-dependent items (roll trigger feasibility, exact eligible-universe source) are resolved by this Phase −1 and pinned at freeze with the certified facts in hand.
