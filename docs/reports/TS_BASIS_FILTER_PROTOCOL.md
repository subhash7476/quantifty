# TS Basis — Directional-Strength Filter Protocol V1 (Pre-Registration)

> **⚠️ CLOSED 2026-08-03 — TS_BASIS_FILTER_PROTOCOL_V1. Status: No filter recommended.**
>
> **Reason:** the proposed admission gates — G1 (VIX-regime), G2 (OI-confirmation), G3 (expiry) —
> do not provide sufficient marginal value to justify inclusion in the construct. Measured on the
> burned 2016–2022 surface (`TS_BASIS_FILTER_SD_PROBE_REPORT.md`, commit `83b3726`), fence-guarded,
> sealed window untouched: **G2 REMOVE** (halves names 179→96, inflates sd_IC +0.0277, negative in
> 0/7 regimes), **G3 REMOVE** (inert — Δsd≈0, Δn_req 0), **G1 regime-dependent** (its only marginal
> credit is COVID-concentrated 82%; §5's "KEEP (mild)" is overridden by §6's NOT-stability-clear —
> the two-stage design working as intended). No tested gate earns its place.
>
> **Scope of this null — precise for the research ledger.** What is closed is *this implementation*
> of the structural-conditioning hypothesis: G1/G2/G3 as these three specific admission rules. The
> probe did **not** test every realization of the §0 hypothesis. The correct claim is **"no tested
> admission gate earns its place,"** NOT "structural conditioning does not work." The broader
> question — whether cross-sectional carry conditions on structural regime at all — remains **open**
> to a genuinely different structural mechanism, which would start its own pre-registration.
>
> **RFA moot** — there is no surviving filtered construct to declare. The construct reduces to plain
> TS Basis Daily (already research-only, 2026-08-01). **The preserved 876-formation sealed window
> (2023-01-01 → 2026-07-24) was never read and remains intact.** The §0 economic hypothesis below
> stays frozen as the record of what V1 claimed. Cost of this closure: ≈ $0 (burned surface only).

**Status:** CLOSED (V1) — no filter recommended. See the banner above, `TS_BASIS_FILTER_SD_PROBE_REPORT.md`, and `TS_BASIS_FILTER_PROTOCOL_REVIEW.md`.
**Branch:** research/strategy-challenge
**Origin:** `docs/reports/STRUCTURAL_ALPHA_DOSSIER.md` (Edges 3, 6, 2) + empirical read from
`TS_BASIS_DAILY_EQUITY_SIGNAL_STRENGTH.md` (past-month direction hit ≈ 54% H=1d, SHORT side weaker).
**Sealed-window rule:** the TS Basis Daily 876-formation sealed window (2023-01-01 → 2026-07-24)
remains PRESERVED. Nothing in this protocol reads it. Filters are selected on TRAIN/HOLDOUT
only; if a filter survives, the sealed window is spent once, one-shot, exactly as
`TS_BASIS_DAILY_SEALED_READ_PROTOCOL.md` requires.

---

## 0. Economic Hypothesis — FROZEN 2026-08-03

**Frozen economic claim (operator, 2026-08-03):**

> Cross-sectional carry is expected to produce *materially stronger* predictive cross-sectional
> rankings when three structural conditions are simultaneously present: (1) a dispersion-friendly
> volatility regime, (2) per-name futures OI confirming the basis signal, and (3) formations free
> from expiry-related mechanical distortions. Outside these conditions, the economic mechanism is
> expected to weaken sufficiently that *excluding* those observations may improve the quality of
> the measured signal.

This is a **graded** conditional-alpha claim, deliberately not an on/off one: the edge is not
asserted to vanish outside the conditions, only to weaken enough that exclusion may raise measured
signal quality. It is falsifiable — it predicts that mean rank-IC on the **admitted** subsample
exceeds mean rank-IC on the **full** sample by enough to survive the formations that admission
removes.

**Metric: `rank_ic`** (operator decision, 2026-08-03). What follows from this metric choice and the
graded claim above:

- All three gates are **admission criteria**, tested as sample-conditioning — not sizing. G1 and G3
  admit/reject at the **formation** level; G2 admits/rejects at the **name** level. All three are
  rank_ic-compatible in this form.
- **G1 is operationalized as a formation-admission gate**, *not* the continuous exposure scalar
  `clip(vix_med/vix, 0.25, 2.0)` (variant A1). A common book-exposure scalar leaves every name's
  rank unchanged and is therefore invisible to `rank_ic` — it is a sizing overlay, **out of scope
  for this construct** (it may be revisited later purely as a drawdown control, judged in
  realized-return space). Only a gate that drops/retains whole formations (the A2 form) expresses
  the hypothesis in IC-measurable terms.
- **The instrument is exclusion, not down-weighting.** Graded down-weighting of a formation is
  itself a sizing scalar and is equally IC-invisible; the hypothesis' own words ("*excluding* those
  observations") commit to hard admission, which is the only rank_ic-expressible form of the claim.
- **Demonstrability cost, carried forward (not a blocker):** every admission gate spends a scarce
  resource — G1/G3 lower **n** (formations), G2 raises **sd_IC** (fewer names per formation ⇒
  noisier per-formation IC). The unfiltered daily construct was already at central power ≈ **0.7472
  at n = 876** (reauthorization §B.3). The graded claim implies a *smaller* filtering benefit than
  an on/off claim would, so the probe must show each gate's IC lift on the retained subsample
  outweighs the n/breadth it costs. **The RFA is declared on the *filtered* n and sd, never the
  base**, and δ is anchored on a HOLDOUT-class read, never the burned sealed +0.077 (C2 lesson).

**Status unchanged:** the protocol remains **DRAFT**. The hypothesis above is frozen; the window
ledger (§3.2) and success metrics (§3.3–§3.4) are **not** — §3.3/§3.4 are still stated in hit-rate
units, and §3.2 contains two stale window rows (monthly SEALED already spent; daily HOLDOUT already
burned as a selection surface). Both are to be corrected, and a `rank_ic` RFA run, before any
confirmatory read. See `TS_BASIS_FILTER_PROTOCOL_REVIEW.md`.

---

## 1. Goal

Improve the **directional strength** of the TS Basis signal (both monthly and daily cadence) by
conditioning *when* and *on which names* the existing signal book is taken. We are NOT adding a
new alpha source. We are adding **filters** to an existing signal to raise per-formation hit rate
and long/short-adjusted return, holding the signal construction frozen.

Empirical baseline being improved (from `TS_BASIS_DAILY_EQUITY_SIGNAL_STRENGTH.md`, 2026-07-06 →
2026-08-03, 190 evaluated picks, entry next-open):

| Metric | Baseline |
|---|---|
| Direction hit H=1d | 54% |
| Direction hit H=5d | 55% |
| L/S-adjusted return H=1d (next-open) | +0.18% |
| LONG hit / SHORT hit H=1d | 55% / 54% |

This is a 30-day sample — a **pre-specification** input, not a TRAIN read. TRAIN remains unread
for filter purposes until Phase 2 below.

## 2. Filter Candidates (pre-specified, in priority order)

### Filter A — VIX Regime Gate (Dossier Edge 3)

**Mechanism:** high-VIX regimes push correlation toward 1; idiosyncratic variation (the basis
signal's raw material) is drowned by systematic risk. Volatility clustering is a stylized fact —
the gate is bet-sizing, not prediction.

**Rule (monthly + daily):**
```
vix_t      = India VIX close on formation date t
vix_med    = rolling 252-session median of India VIX ending at t (min 60 obs)
ratio      = vix_med / vix_t
exposure   = clip(ratio, 0.25, 2.0)
```
Formation is **fully taken** (exposure 1.0) only when `ratio ≥ 0.5` (i.e. VIX not more than
2× its median). Otherwise the book is scaled by `exposure`; at `exposure = 0.25` (VIX ≥ 4× median,
the March-2020 style tail) the formation is effectively flat.

**Variants (tie-break on TRAIN):**
- A1: continuous scaling (above).
- A2: hard gate — skip formation entirely when `vix_t > 1.5 × vix_med`.
- A3: per-side gate — gate the SHORT side (empirically the weaker side) harder than LONG.

**Data:** India VIX, 1d store, 2010–2026 — in repo. No new data.

### Filter B — Per-Name Futures OI Dynamics (Dossier Edge 6)

**Mechanism:** futures open-interest change + price jointly reveal conviction. For a basis-carry
signal, a LONG is more credible when the future's OI is *building* (new longs) and less credible
when OI is *falling* (unwinding). This is directly observable in the repo's `futures_bhavcopy`
(`open_int`, `chg_in_oi` per underlying/expiry/day).

**Rule (per name, per formation):**
```
oi_chg_z   = z-score of (OI_t - OI_{t-1}) / OI_{t-1}  across the eligible universe at t
            (or chg_in_oi / OI when volume is reliable)
confirm    = sign(oi_chg) == sign(signal side)         # OI building in signal direction
```
Only names where `confirm == TRUE` are admitted to the book. If fewer than `n_min` names confirm,
take the top-`n_min` by |z_carry_neut| regardless (liquidity/coverage guard).

**Variants:**
- B1: hard admission filter (`confirm` required).
- B2: weight position size by `|oi_chg_z|` (multiplicative, clipped at [0.25, 2.0]).
- B3: B1 + require the name's OI to be *rising* for LONG / *rising* for SHORT (asymmetric — the
  short side often needs OI proof more than the long side).

**Data:** `futures_bhavcopy` — in repo. No new data.

### Filter C — Expiry-Day / Gamma-Day Skip (Dossier Edge 2, reduced form)

**Mechanism:** on stock-futures monthly expiry days (last Thursday) and index weekly expiry days
(Thursday for Nifty, Wednesday for BankNifty), dealer delta-hedging mechanically distorts stock
price discovery — entries/exits adjacent to these days carry contamination.

**Rule:** skip (or halve) the formation when the **execution date** (`t+1`) is an NSE F&O expiry
day for the relevant segment, or when the formation date `t` is within 1 session before expiry.

**Variants:**
- C1: skip formation when `t+1` is a monthly stock-futures expiry day.
- C2: skip when `t+1` is a Nifty/BankNifty weekly expiry day (index gamma).
- C3: halve exposure rather than skip.

**Data:** expiry calendar derivable from `nse_fo_instruments.duckdb` + `futures_bhavcopy` expiry_dt.
In repo.

### Filter D (deferred) — Cross-sectional Dispersion

Low cross-sectional dispersion → idiosyncratic names dominate → basis works; extreme dispersion →
names move together. Compute dispersion from the eligible universe's 20-day forward-return
cross-sectional SD at `t`; gate on it. Requires no new data, but is **deferred** until A–C are
adjudicated so the multiplicity bill stays small.

## 3. Evaluation Design

### 3.1 Subject being filtered

Both cadences, evaluated separately (monthly book and daily book are different constructs with
different fee profiles — never pool them):

- **TS Basis Daily** — signal book from `ts_facts.duckdb` (`z_carry_neut`, quintile, eligible),
  top-5 per side (the selection `ts_basis_daily_options.py` uses), priced on underlying equity
  spot (NSE_EQ) exactly as `ts_basis_daily_equity_signal_strength.py` does.
- **TS Basis Monthly** — the monthly carry book; same filter rules applied at monthly formations.

### 3.2 Windows (filters are selected and confirmed, never both on the same data)

| Window | Span | Use |
|---|---|---|
| TRAIN | 2016 → 2018 (daily) / 2016 → 2019 (monthly) | Filter selection + variant tie-break. Burned. |
| HOLDOUT | 2019 → 2022 | Single confirm read of the winning filter set. |
| SEALED | 2023-01-01 → 2026-07-24 | One-shot confirm, only if HOLDOUT passes. Never re-run. |

### 3.3 Metrics (identical to the equity signal-strength analysis)

- Direction hit rate at H=1d, H=2d, H=5d (predicted move: LONG→up, SHORT→down).
- Long/short-adjusted return (mean + median) at H=1d, H=2d, H=5d, entry next-open.
- Per-side decomposition (LONG vs SHORT) — the SHORT side is the known weak leg.
- z-rank monotonicity (rank 1 vs rank 5) before and after filtering.
- Exposure/coverage: fraction of formations/names retained by each filter (a filter that takes
  5% of names to lift hit rate 60%→80% is a different animal from one that keeps 90%).

Prices: Upstox NSE_EQ daily candles (active + expired path not needed — equities don't expire).

### 3.4 Success threshold (pre-specified)

A filter "helps" only if it satisfies **all** of:

1. Hit rate H=1d improves by **≥ 4pp** vs the unfiltered baseline on the same window (not vs the
   past-month sample — that is pre-spec only).
2. L/S-adjusted return H=1d improves **and** does not deteriorate at H=5d.
3. Coverage stays **≥ 60%** of original names (a filter that decimates the book is not a filter,
   it is a different strategy).
4. Improvement holds for BOTH sides, or the side it improves does not regress the other.

Filters that fail any criterion on TRAIN are dead; no re-specification from results.

### 3.5 Multiplicity

Three filter families (A, B, C) with 2–3 variants each = ≤ 9 comparisons. Selection is made by
the pre-specified hierarchy (A → B → C) and the 3.4 criteria — NOT by choosing the best-looking
variant post-hoc. If multiple variants of one family pass, take the simplest (A1 over A2/A3,
B1 over B2/B3). HOLDOUT tests the chosen set only (≤ 1 test per family, α = 0.05 no Bonferroni
re-run since TRAIN multiplicity is pre-paid by the hierarchy rule).

## 4. Phase Gates

| Gate | Read | Pass criterion | Fail consequence |
|---|---|---|---|
| P1 Substrate | none | India VIX series contiguous 2016→present; `futures_bhavcopy` OI columns populated ≥ 95% of underlying-days; expiry calendar derivable | Fix data, do not read TRAIN |
| P2 TRAIN | TRAIN only | A family improves hit ≥4pp at H=1d with coverage ≥60%; B same; C same (each independently) | Dead family is dropped, never reopened |
| P3 HOLDOUT | HOLDOUT once | Surviving family set improves hit ≥4pp vs unfiltered HOLDOUT; L/S-adjusted return ≥ 0 | No SEALED read |
| P4 SEALED | SEALED once | Same criteria as P3 | Construct falsified |

If NO family survives P2, the protocol closes with "no filter recommended" — a valid outcome
(PSB-1 precedent).

## 5. What This Is NOT

- NOT a re-open of TS Basis Daily's sealed window for signal *construction* tuning.
- NOT a new alpha source — filters condition an existing signal; the fee wall still applies.
- NOT a C2-style reopen with post-hoc in-sample execution overlays (the guard in CLAUDE.md
  forbids intraday TP/SL brackets tuned on observed excursions).
- NOT an index-timing strategy (per_trade_pnl on indices is dead — dossier Constraint 1).

## 6. Prior Exposure Disclosure

| Read | Relevance |
|---|---|
| `TS_BASIS_DAILY_EQUITY_SIGNAL_STRENGTH.md` (past 30d) | Pre-specification baseline only; not a TRAIN read, no filter choice depended on it |
| PSB-1/PSB-2 fee findings | Confirms monthly+banded is the only fee-survivable equity path |
| Dossier Edge 3/6/2 | Source of the filter mechanisms, stated before any filter data read |

No prior read exists on: India VIX conditioned on the TS Basis book, per-name futures OI dynamics
vs basis-signal forward returns, or expiry-day contamination of the basis signal.

## 7. Deliverables

1. This protocol (frozen — SHA-256 recorded at freeze).
2. `scripts/` analysis harness mirroring `ts_basis_daily_equity_signal_strength.py` but
   parameterised by filter, emitting the §3.3 metric table per filter-variant on TRAIN.
3. `docs/reports/TS_BASIS_FILTER_TRAIN_REPORT.md` (script-generated, no hand-edited numbers).
4. HOLDOUT report, then SEALED report only if gates pass.
