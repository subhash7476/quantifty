# PTMS — P3 Hypothesis Family Catalogue (design only)

**Date:** 2026-09-12 · **Authority:** operator ruling PTMS-2026-09-12 ("GO for
family-catalogue/design work only").
**This document generates no features, declares no RFA, scans no candidates, selects no
parameters, and implements nothing.** No market data was read to produce it. Availability
below is derived **entirely from the exposure register**, per the §6 gate.

---

## 0. Availability summary — read this first

The §6 gate says: *do not assume a candidate is testable merely because the data exists.*
Applied to all seven families, **before** any construct work:

| Family | Surface | Readable fresh window | Verdict |
|---|---|---|---|
| **A — Time-only** | index 1m | none at signal level | **BUDGET-BLOCKED** |
| **B — Price × elapsed time** | index 1m | none at signal level | **BUDGET-BLOCKED** |
| **C — Gann geometry (single-index `per_trade_pnl`)** | index 1m / 1d | none at signal level | **BUDGET-BLOCKED** |
| **D — Temporal symmetry / cycles** | index 1m / 1d | none at signal level | **BUDGET-BLOCKED** |
| **E — Nifty/Bank cross-market** | index 1m pair | none — I-3 spent the ratio directly | **BUDGET-BLOCKED** |
| **F — Stock-level cross-sectional price-time** | breadth 1m 2023-01-02→ | **n/a — substrate, not budget** | **SUBSTRATE-BLOCKED (permanent)** — C2-A1: `pit_membership` is circular and may not be repaired from the same candle panel. Removed from the executable list; not to be rescued without an independently sourced and certified PIT universe |
| **G — EOD derivatives / market state** | options + futures EOD | **partial** — index options 2023→2026-07-17 not signal-read by a market-state family | **CONDITIONAL** |

**The headline is uncomfortable and should not be softened: five of seven families, including
Gann, have no legitimately fresh confirmatory window on the surface their hypothesis lives
on — and after C2, Family F is removed outright as SUBSTRATE-BLOCKED, leaving G as the sole
family not blocked on either budget or substrate.** This is the arithmetic consequence of C2 (the index 1m store is spent at signal level
in both eras) plus the fact that futures history cannot predate 2016 and intraday breadth
cannot predate 2023.

Three honest responses exist, and the choice is the operator's:

1. **Accept the blocks.** Run only G (F is now substrate-blocked, not conditional). Document A–E as budget-blocked — a valid P3
   outcome under the §6 gate, and cheaper than discovering it after building.
2. **Forward-paper as the confirmatory window.** A construct frozen today, run forward on
   genuinely unseen data, manufactures a fresh window at the cost of calendar time. This is
   the *only* mechanism that creates new budget. It is how TS Basis's de-authorization was
   said to be resolvable.
3. **Re-scope to a surface with unspent budget.** The VIX assets (exposure level NONE,
   2010/2015 → 2025) are the largest genuinely unread surface in the repo — but they are
   certification-blocked, and a *volatility-state* hypothesis is not the same hypothesis as
   any of A–E.

Nothing below is a recommendation to build. Each entry is a specification in the form the
next gate needs.

---

## 1. Required fields

Per ruling §3, every candidate specifies: **units · origin rule · normalization ·
event/signal · label · null · eligibility · multiplicity contribution.** Catalogue frozen at
seven families; **no expansion after seeing results.**

---

## Family A — Time-only

| Field | Specification |
|---|---|
| **Hypothesis** | The conditional distribution of forward index return depends on position within the session, independent of price history |
| **Units** | Signal: session-phase index (dimensionless, 1…375 bars or a coarser partition declared in advance). Label: log return, decimal |
| **Origin rule** | Session open, from `trading_calendar` + `session_schedule.py`. Deterministic, no choice |
| **Normalization** | None on the signal (it is a clock). Label standardized by trailing realized vol over a declared lookback ending strictly before the signal bar |
| **Event / signal** | Bar index *b* within the session |
| **Label** | Forward return from the bar **after** *b* to a declared horizon; never overlapping the signal bar |
| **Null** | Circular-shift null on the outcome series (ISD's machinery), preserving autocorrelation; plus a uniform-across-phases null |
| **Eligibility** | Full sessions only; `is_synthetic = FALSE`; era-consistent under the C1 rule; special sessions (Muhurat, Saturday specials) excluded and enumerated |
| **Multiplicity** | *m* = (number of phase partitions) × (number of horizons). Both pinned pre-read |
| **Availability** | **BUDGET-BLOCKED.** Index 1m 2012–2022 spent (I-1 feature, I-4/5 and I-7/8 signal); 2023→ spent at signal (I-3) |

## Family B — Price × elapsed time

| Field | Specification |
|---|---|
| **Hypothesis** | For an origin *O*, the joint behaviour of displacement ΔP and elapsed time ΔT carries information about forward return beyond ΔP alone |
| **Units** | ΔP in log-return (dimensionless) or index points (declared, not both). ΔT in bars. **The ratio ΔP/ΔT has units only once both are pinned** |
| **Origin rule** | Deterministic function of strictly prior data. Candidate set enumerated pre-read (session open; prior-session close; most recent *k*-bar swing under a fixed rule). **The number of candidate origin rules counts toward *m*** |
| **Normalization** | The load-bearing choice. Price scaled by trailing realized vol or by ATR over a declared lookback; time in bars. Fixed before evaluation; **the admissible set is the multiplicity surface** |
| **Event / signal** | A function of (ΔP, ΔT) declared in closed form — not a grid search |
| **Label** | Forward return from the bar after the signal bar to a declared horizon |
| **Null** | Circular-shift; plus a ΔP-only control model — B must beat *price alone*, not zero |
| **Eligibility** | As A, plus a minimum ΔT so the ratio is defined |
| **Multiplicity** | *m* = origins × normalizations × horizons |
| **Availability** | **BUDGET-BLOCKED** (as A) |

## Family C — Gann geometry · **single-index `per_trade_pnl`**

| Field | Specification |
|---|---|
| **Hypothesis** | A price-time geometric relationship on a single index predicts the direction of its subsequent move. **Tested as the claim is actually made** — per ruling §7, no cross-sectional rank-IC manufactured by applying an index rule to the equity universe |
| **Units** | A geometric ray requires an explicit **price-per-bar scale** *s*. A "1×1" is *s* units of price per bar. `s` must be declared as a formula (e.g. a multiple of trailing ATR per bar), never read off a chart |
| **Origin rule** | As B: deterministic, enumerated, counted |
| **Normalization** | *s* itself. The admissible set of *s*-definitions **is** the multiplicity surface, jointly with the ray set |
| **Event / signal** | Price crossing, touching, or holding a ray {1×1, 2×1, 1×2, 3×1, 1×3} from origin *O* under scale *s*; or a price-time intersection. Sign pinned by mechanism pre-read; a wrong-sign TRAIN closes the family — no sign-flip fishing |
| **Label** | Per-trade net P&L over a declared holding rule, era-accurate costs |
| **Null** | Random-origin null (same ray set, origins drawn from the eligible set); plus circular-shift |
| **Eligibility** | As A; rays requiring bars beyond the session excluded |
| **Multiplicity** | *m* = rays (5) × scale definitions (*k*) × origin rules (*j*) = 5·*k*·*j*. **Pinned before the read; this is where a geometry family degenerates into a fishing machine if left open** |
| **Availability** | **BUDGET-BLOCKED.** No fresh signal-level window on index 1m or 1d. **Prior power constraint, recorded and independent of budget:** `per_trade_pnl` on a single index time series obeys `ncp = S·√T`, and RS-MOM measured √T_sealed ≈ 1.89 on a comparable window, which implies Sharpe ≥ ~1.3 for power 0.80. Cadence cancels, so finer bars do not relieve it. **This is a prior constraint on the achievable band, not an RFA disposition.** C's disposition is determined only after its eligible window and effect-size band are frozen |

## Family D — Temporal symmetry / cycles

| Field | Specification |
|---|---|
| **Hypothesis** | Recurring temporal structure (fixed-period or symmetry about a pivot) carries forward-return information |
| **Units** | Period in bars or sessions; amplitude in normalized return |
| **Origin rule** | Pivot identified by a causal rule — **`result.iloc[i + period]` assignment, never a centered window** (standing repo rule) |
| **Normalization** | Amplitude by trailing realized vol |
| **Event / signal** | Phase within the declared period, or distance from the symmetry point |
| **Label** | Forward return beginning after the signal bar |
| **Null** | **Essential here:** a matched-spectrum surrogate (phase-randomized series preserving the power spectrum). A cycle family without a spectral null will find cycles in noise |
| **Eligibility** | As A; periods bounded below by sampling and above by window/4 |
| **Multiplicity** | *m* = candidate periods × pivot rules. **Do not assume cycles exist because a method claims they do** |
| **Availability** | **BUDGET-BLOCKED** (as A) |

## Family E — Nifty / Bank cross-market structure

| Field | Specification |
|---|---|
| **Hypothesis** | Information in index A at time *t* predicts index B's forward behaviour **beyond what B's own history already supplies** |
| **Units** | Log-return spread or residual, dimensionless |
| **Origin rule** | Session open |
| **Normalization** | Beta-adjusted residual of B on A, beta estimated causally on strictly prior data |
| **Event / signal** | A→B lead-lag statistic, or a residual divergence |
| **Label** | B's forward return after the signal bar |
| **Null** | **Nested control is mandatory**: a B-only model. E is accepted only on incremental information over B-alone — the charter's §11 framing |
| **Eligibility** | Both indices present, full session, era-consistent under C1. **In 2022 files VIX is on the modern grid while the index pair is on the old one (V1) — an unguarded join is silently offset one minute** |
| **Multiplicity** | *m* = lags × horizons × residual definitions |
| **Availability** | **BUDGET-BLOCKED.** I-3 spent the pair directly at signal level (27 mean-reversion parameter combos, 2023→2026); the pair's intraday-trending byproduct is already a *read* result, not a fresh hypothesis |

## Family F — Stock-level cross-sectional price-time

| Field | Specification |
|---|---|
| **Hypothesis** | A price-time construct predicts the **cross-section of stock returns**. Must be a genuine stock-level hypothesis — per the CB-N50 constraint, using ~190 names to manufacture a rank-IC for an index rule is invalid |
| **Units** | Cross-sectional rank (dimensionless); label log return |
| **Origin rule** | Per name, deterministic; identical rule across names |
| **Normalization** | Cross-sectional z or rank; beta and sector neutralization if the claim is idiosyncratic |
| **Event / signal** | Per-name price-time statistic, ranked across the eligible universe on each formation date |
| **Label** | Forward return, entry strictly after the signal window closes (ISD R2 pin) |
| **Null** | Circular-shift on the formation axis; plus a same-universe random-rank null |
| **Eligibility** | `pit_membership` (`intraday_present`, `fno_member`), **not the file's symbol set**; `is_synthetic = FALSE`; CA ex-dates excluded |
| **Multiplicity** | *m* = constructs × normalizations × horizons, BH-corrected (ISD's 4 cells at α = 0.0125 is the in-repo precedent) |
| **Availability** | **CONDITIONAL.** Breadth 1m starts 2023-01-02 (~900 sessions). ISD spent 2023-01-02 → 2024-11-30; E-3/E-6 touch later dates. A candidate window exists but must be **negotiated against the register, not assumed**. Effect-size band must anchor on CB-N50's **HOLDOUT +0.029**, never its TRAIN +0.059 |

## Family G — EOD derivatives / market state

| Field | Specification |
|---|---|
| **Hypothesis** | Derivatives positioning (OI, OI change, term structure) carries forward-return information **beyond price** |
| **Units** | OI in contracts; normalized to a dimensionless ratio or z-score |
| **Origin rule** | Formation = a declared session's close |
| **Normalization** | Relative to a trailing baseline over a declared lookback |
| **Event / signal** | Positioning statistic at formation |
| **Label** | Forward return over a declared horizon |
| **Null** | **Nested price-only control is mandatory** — `price` vs `price + derivatives` |
| **Eligibility** | `fo_eligible_intervals`; **index options stall at 2026-07-17** while stock options run to present — do not join naively across that boundary |
| **Multiplicity** | *m* = statistics × lookbacks × horizons |
| **Availability** | **CONDITIONAL.** Futures EOD sealed windows are spent (Carry PASS, TS Basis de-authorized, IVOL FAIL). Index options 2023 → 2026-07-17 has no recorded signal-level read by a *market-state* family; O-1 spent stock options 2023–2026. A window may exist; it must be established against the register |

---

## 1b. Status of the availability column (operator ruling, P2/P3 review)

The verdicts above are **provisional pending P2**. The ruling requires that, after
certification, certified surfaces be reconciled against the exposure register and the
eligible window derived **separately for each family** — availability must never be inferred
from physical data coverage. Until that reconciliation exists, every "BUDGET-BLOCKED" and
"CONDITIONAL" above is a register-derived expectation, not a certified determination.

**No RFA is authorized for any family.** Where a prior power constraint is recorded (Family
C), it constrains the defensible effect-size band; it is **not** a disposition. Dispositions
follow the frozen window and band, never precede them.

## 2. What P3 needs next

1. **Operator choice among the three responses in §0** — accept the blocks, open a
   forward-paper window, or re-scope. Five of seven families cannot proceed otherwise, and
   no amount of construct design changes that.
2. **P2 must close first regardless.** Even F and G need C1 (clock), C2 (PIT), C3
   (tradeability) before a formation date means anything.
3. **No RFA may be drafted yet** — ruling §6. `n_available` for every family above is a
   function of the P0 register *and* the P2 eligible-window determination, and the second
   does not exist yet.
