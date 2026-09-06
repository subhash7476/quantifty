# Carry Sleeve — Phase 0 Pre-Registration (DRAFT)

**Status:** DRAFT. To be **FROZEN** on operator approval (SHA-256 over the whole file);
bands cannot be revised in response to results once frozen.
**Parent design:** `SIGNAL_ENGINE_DESIGN.md` — this is sleeve #1 (Carry), validated
standalone before it may enter the combined engine.
**Consumes:** no sealed data. This document authorizes the RFA power pre-check and, if it
returns PROCEED, the TRAIN/HOLDOUT empirical protocol. The 2023→present window stays
**sealed and unread** until §9's acceptance rule is met on TRAIN and HOLDOUT.

---

## 1. Hypothesis (falsifiable)

Cross-sectional dispersion in the **residual** single-stock-futures basis — the annualized
future-minus-spot premium after the common financing component and expected dividends are
removed — predicts forward returns. Names with a high residual basis (elevated borrow demand
/ leveraged-long pressure) **underperform** low-residual-basis names on a beta- and
sector-neutralized, net-of-cost basis over the following month.

Sign is declared now and cannot be flipped after seeing results: **short high residual carry,
long low residual carry.** (Economic reading: a rich residual basis signals crowded leveraged
longs / expensive borrow, which mean-reverts.) If realized IC is significant with the
*opposite* sign, the hypothesis is falsified, not re-labelled.

---

## 2. Universe & point-in-time membership

- **Universe:** NSE F&O-eligible single-stock names, **point-in-time** — a name is eligible
  at formation *t* only if it was F&O-listed and liquid at *t*. No survivorship: names added
  and removed on their actual SEBI/NSE eligibility dates.
- **Liquidity screen (pinned):** at each formation, drop any name whose trailing 20-day
  **median futures turnover < ₹5 cr**; positions are additionally **ADV-capped** at
  construction (§6). The long tail of thin SSFs backtests beautifully and cannot be traded —
  the cap is enforced, not advisory.
- **Expected N per formation:** ~120–180 names post-screen. The ingested substrate carries
  **363 stock-futures underlyings** (2016-02-11 → 2026-07-20); post-liquidity-screen N is
  confirmed at build.

---

## 3. Signal construction (exact, pre-registered)

For each name *i* at each daily observation, using the **near-month** future (roll rule §3.4):

1. **Raw basis (annualized):**
   `raw_basis_i = ((F_i − S_i) / S_i) × (365 / days_to_expiry_i)`
   where `F_i` = near-month futures close, `S_i` = spot/underlying close.
2. **Dividend adjustment:** subtract the expected annualized dividend yield accruing before
   expiry from `raw_basis_i` using **announced/ex-date-known** dividends only (no lookahead).
   → `div_adj_basis_i`.
3. **Common-financing removal:** cross-sectionally **demean** `div_adj_basis_i` across the
   eligible universe on each date. The common implied financing rate (MIBOR-like) is shared
   across names and is removed by the demean; the residual is the name-specific
   borrow-demand / sentiment component.
   → `resid_carry_i = div_adj_basis_i − mean_j(div_adj_basis_j)`.
4. **Cross-sectional z-score:** standardize `resid_carry_i` to zero mean / unit SD across the
   universe on each date → `z_carry_i`. Winsorize at ±3 SD (pre-registered) before z-scoring.

### 3.4 Roll rule
Use the near-month contract until **T−3 trading days** before expiry, then roll to the next
month. Signal is recomputed on the post-roll contract. Roll timing is fixed here and not a
tunable.

---

## 4. Neutralization

Before ranking, residualize `z_carry_i` against:
- **Market beta** (trailing 252-day beta to Nifty), and
- **Sector** (NSE sector dummies).

via a single cross-sectional OLS per formation; the **residual** is the tradeable signal
`z_carry_neut_i`. Rationale (`SIGNAL_ENGINE_DESIGN.md` §4): without this, "carry" is a covert
short-high-beta / sector bet and the sleeve is not orthogonal to Trend/Flow/Skew.

---

## 5. Metric — and why rank-IC, not per-trade Sharpe

**Primary metric:** cross-sectional **Spearman rank-IC** of `z_carry_neut` at formation *t*
vs. the forward one-month name return, measured at monthly formations.
**Secondary (reported, not the gate):** net top-minus-bottom quintile spread under §8 fees.

**Why rank-IC (this is the O1 lesson, applied).** The RFA contract v2 permits **independent**
delta (mean-IC) and SD (IC-dispersion) bands *only* for `metric="rank_ic"`, because IC mean
and IC dispersion are separately estimable off a cross-section — the independence is
defensible. For `per_trade_pnl` the same independence is a **crossed-corner artifact**, which
is exactly what withdrew O1 (delta was Sharpe-coupled to SD, and `(delta_hi, sd_lo)` implied a
Sharpe above the declaration's own ceiling). A cross-sectional carry book is natively a
rank-IC construct, so declaring it as `rank_ic` is both the correct model *and* the corner
that is contract-legal rather than smuggled. This sleeve does not repeat O1's error.

---

## 6. Portfolio construction

- **Form:** beta-neutral, sector-neutral, dollar-neutral cross-sectional long/short.
- **Weights:** proportional to `z_carry_neut` (z-weighted), renormalized to fixed gross
  exposure; **ADV-capped per name** (position ≤ **10% of 20-day futures ADV**).
- **Rebalance cadence:** **monthly**, aligned to the roll. (Cadence is fixed at monthly
  because — per `CLAUDE.md` RFA — higher cadence cannot buy statistical power: `ncp = S·√T`,
  cadence cancels. Monthly minimizes turnover/fees at no power cost.)
- **Turnover penalty:** rebalances smaller than **0.25σ** of target weight are suppressed
  (no-trade band).

---

## 7. RFA power pre-check (declared bands — frozen at approval)

`metric = rank_ic`, one-sided test (sign declared in §1), power hurdle **0.80**.

| Quantity | Band | Provenance |
|---|---|---|
| **delta** (mean cross-sectional IC) | **[0.020, 0.045]** | Cross-sectional carry/basis IC in equity & futures literature (Koijen–Moskowitz–Pedersen–Vrugt 2018; Asness–Moskowitz–Pedersen 2013) sits ~0.02–0.05 for a single well-constructed factor; residual-basis in SSF defended at the same range, upper end reflecting India's stronger borrow-demand dispersion. |
| **SD** (IC dispersion across formations) | **[0.10, 0.18]** | Monthly cross-sectional IC dispersion for a large (~150-name) cross-section is dominated by true time-variation, not sampling noise; equity-factor monthly IC SD is ~0.10–0.18. |
| **n*** (formations in the power-projection window) | **= 42** (monthly, sealed 2023-01 → 2026-07) | Fixed by the ingested futures span — see §7.1. |

### 7.1 The honest power picture — standalone vs. combined
`ncp = (delta / SD) · √n*`. At the sealed window (2023→present, **~42 monthly formations**),
clearing power 0.80 (one-sided, α=0.05) needs per-formation IR `delta/SD ≥ ~0.38`:
- **Optimistic corner** `(delta_hi=0.045, SD_lo=0.10)` → IR 0.45 → **clears** → RFA
  **PROCEED**. (Legitimate here, not a crossed corner — see §5.)
- **Central** `(0.030, 0.14)` → IR 0.21 → standalone power ≈ 0.40 → below hurdle.

**The calendar lever is exhausted.** The ingested futures substrate begins **2016-02-11** and
NSE F&O history before that is not obtainable (the SFB-1/F1 lockdown finding). So n* cannot be
raised by pulling more history — 42 is the ceiling. That leaves two honest levers: a genuinely
higher realized IC, and — the design's real answer — **breadth across sleeves.**

**Where the 0.80 hurdle actually binds (design decision).** A single monthly cross-sectional
sleeve at n*=42 cannot be *required* to clear 0.80 standalone — that would kill a genuinely
additive sleeve for the same arithmetic reason PSB-2 C4 and PSB-1 C5 died, and it contradicts
the engine thesis. Per `SIGNAL_ENGINE_DESIGN.md`, demonstrability is manufactured by combining
weakly-correlated sleeves: composite `IR ≈ √(N_signals) × per-sleeve IR` when sleeves are
near-independent. Therefore:
- **The single-sleeve RFA bar is PROCEED** (optimistic corner clears — this is permission to
  build, not clearance).
- **The 0.80 power hurdle binds at the COMBINED-engine level**, where N_signals breadth exists.
- The standalone TRAIN/HOLDOUT read is a **sign + magnitude + fee + persistence** check
  (§9 gates 2, 4, 5), **not** a standalone 0.80 gate.

**Data-reality caveat (do not lose this).** With the full options ingest (in progress),
**three** sleeves become data-feasible (Carry, Trend, Skew); Flow still needs the separate
participant-OI ingest. Composite power at n*=42 (central assumptions): 2 sleeves ≈ 0.6,
3 sleeves ≈ 0.75, 4 sleeves ≈ 0.86. So the engine clears 0.80 at four sleeves (or at three
with upper-band realized IRs). This is the binding constraint on the engine as a whole,
recorded here so the carry read is not mistaken for the finish line.

### 7.2 AC₁ / overlap
Monthly non-overlapping formations → no overlap-induced autocorrelation inflation. AC₁ still
reported at TRAIN; if materially positive, the effective-n haircut is applied before the
power read (Newey–West / AC₁ correction, as in the PSB harness).

---

## 8. Fees & cost model

- **Era-accurate NSE single-stock-futures fee model** — components: brokerage (flat/₹/lot),
  **futures STT (sell-side)**, exchange transaction charge, SEBI turnover fee, GST on
  (brokerage+txn), stamp duty (buy-side). To be implemented as
  `core/execution/futures/futures_fees.py`, mirroring the discipline of
  `core/execution/equity/delivery_fees.py`.
- **Futures STT schedule (sell-side, pinned; confirm each tier against the dated NSE circular
  at build):** 0.0100% through 2023-03-31 · 0.0125% 2023-04-01 → 2024-09-30 · 0.0200% from
  2024-10-01 (Finance Act 2023 +25%; Oct-2024 derivatives-STT revision).
- **Slippage:** κ bp/side pre-registered (e.g. 5 bp), plus the ADV cap as the impact control.
- **Net-of-cost is the acceptance gate** (§9). Note futures fees are materially below
  delivery-equity STT (0.1%/leg) that killed the PSB cash constructs — but this sleeve is
  **not** assumed fee-safe by construction; it must demonstrate net > 0.

---

## 9. Acceptance rule (pre-registered, evaluated before any sealed read)

**Windows (pinned, from the ingested futures span 2016-02-11 → 2026-07-20):**
- **TRAIN:** 2016-03-31 → 2020-12-31 (~58 monthly formations). First formation 2016-03 allows
  20-day futures-ADV warmup; beta warms up off pre-TRAIN history on both legs — the stock leg
  from adjusted spot (`equity_bhavcopy_adjusted`, 2010-01-04+) and the market leg (Nifty 50)
  from the 1d index store (2012-02-21+, gate-verified in `CARRY_G1_R4_VERIFICATION.md`) — so
  beta does not consume futures formations.
- **HOLDOUT:** 2021-01 → 2022-12 (24 monthly).
- **SEALED:** 2023-01-01 → 2026-07-20 (~42 monthly) — **untouched** until gates 1–5 pass.

Ordered gates. Each must pass on the stated window before the next window is touched:

1. **RFA gate** (declared bands, §7): single-sleeve bar is **PROCEED** (optimistic corner).
   ABANDON is dispositive.
2. **TRAIN:** mean rank-IC significant with the **declared sign** (t via AC₁-corrected SE);
   net quintile spread > 0 under §8 fees; realized IC SD inside the declared [0.10, 0.18] band
   (if SD > 0.18 — the C2 wide-SD failure — the sleeve stops here, sealed window preserved).
3. **HOLDOUT:** sign and net-spread persist; **no parameter touched** between TRAIN and HOLDOUT.
4. **Composite power check** (engine level, not standalone): the carry sleeve's TRAIN-estimated
   IR feeds the combined-engine power projection (§7.1); the **0.80 hurdle binds on the
   composite**, not on carry alone.
5. **Only then**, one **SEALED** read (2023→present), reported whatever it shows.

Any gate failure → sleeve does not advance; **no successor is auto-authorized**; sealed window
stays sealed if not yet reached.

---

## 10. Prior-exposure disclosure

Operator's prior reads are in **momentum / delivery** constructs (PSB-1 C1–C5, PSB-2 C2/C4,
SFB-1/F1). **None is a carry/basis construct** — carry has not been screened on this data, so
prior exposure to *this* signal is nil. The general finding that monthly cross-sectional
equity is demonstrability-constrained (RFA retrospective) is methodological, not a peek at
carry's realized numbers, and is already priced into §7.1.

---

## 11. Falsifiable predictions (stated before the run)

1. Residual-carry rank-IC on TRAIN is **negative-signed** (short high carry) and its
   AC₁-corrected t-stat clears the pre-set threshold.
2. The signal is **not** subsumed by beta/sector — IC survives the §4 neutralization (raw-basis
   IC and neutralized IC same sign, neutralized magnitude ≥ 60% of raw).
3. Net quintile spread > 0 under §8 futures fees at monthly turnover.
4. Realized TRAIN IC SD lands inside the declared **[0.10, 0.18]** band (if it exceeds 0.18,
   the C2 wide-SD failure repeats and §9 gate 2 stops the sleeve).

If (1) or (3) fails, Carry is not a viable sleeve and the engine proceeds with Trend as anchor.

---

## 12. Key files (to be created)

| File | Purpose |
|---|---|
| `governance/rfa/declarations/carry.py` | Frozen RFA declaration (bands, n*, sign) |
| `scripts/signal_engine/carry/build_carry.py` | §3 signal construction (basis → residual → z) |
| `scripts/signal_engine/carry/neutralize.py` | §4 beta/sector residualization |
| `scripts/signal_engine/carry/run_train.py` | §9 TRAIN read → `CARRY_TRAIN_REPORT.md` |
| `core/execution/futures/futures_fees.py` | §8 era-accurate SSF fee model |
| `tests/signal_engine/carry/` | signal + neutralization + fee unit tests |
| `docs/reports/CARRY_TRAIN_REPORT.md` | script-generated TRAIN report (no hand-edited numbers) |

---

## 13. Engine viability — empirical, not projected (freeze discipline)

The freeze pins **construction**, not a viability verdict. The composite engine's power is
decided **empirically from realized quantities after TRAIN**, never from a pre-freeze
projection — because the composite `IR ≈ √(Σ IR_i²)` (correlation-adjusted) requires realized
per-sleeve ICs and the realized cross-sleeve correlation matrix, neither of which exists before
a TRAIN read. Projecting it from defended bands is a planning aid, **not a gate**: the RFA code
(`scripts/rfa/gate.py`) enforces no composite gate — it evaluates one declaration at a time
against 0.80 at its optimistic corner. The design-doc figures (2-sleeve ≈ 0.6, 3 ≈ 0.75,
4 ≈ 0.86) are planning arithmetic, superseded by realized numbers.

"Viability stays empirical" is a **discipline, not a licence to build-and-hope.** It is bounded
by four rules, pinned here at freeze:

1. **Per-sleeve RFA PROCEED is a hard pre-build gate.** No sleeve receives a TRAIN read until
   its own frozen declaration clears the optimistic-corner test in `scripts/rfa/gate.py`.
   ABANDON is dispositive.
2. **Freeze pins construction and bands.** Basis formula (§3), neutralization (§4), fee model
   (§8), per-sleeve RFA bands (§7), cadence/caps (§6), and the combination rule (equal
   risk-contribution, `SIGNAL_ENGINE_DESIGN.md` §5) are immutable after freeze. Nothing is
   tunable post-hoc.
3. **The composite faces 0.80 after TRAIN, before any sealed read.** Once ≥2 sleeves have TRAIN
   reads, compute the realized composite IR from realized per-sleeve ICs and the realized
   correlation matrix, and evaluate it against the 0.80 hurdle. This is the engine's go/no-go,
   computed with real inputs at the one point where they exist.
4. **Failure action is pre-committed — no weight-tuning to manufacture 0.80.** If the realized
   composite < 0.80, the engine does **not** advance to the sealed window. The only permitted
   responses are (a) add a separately-defended sleeve that clears its own RFA, or (b) stop.
   Re-weighting the existing sleeves to reach 0.80 is prohibited — it is the post-hoc fitting
   the RFA gate exists to prevent.

**Acknowledged structural risk.** This defers the binding (composite) gate to a construct that
does not yet exist — `CLAUDE.md` records this as the track's largest structural risk, and the
Flow finding (per-name OI without participant attribution → expected ABANDON → a 3-sleeve
engine at ~0.75 central projection) makes it more acute, not less. A 3-sleeve engine whose
viability is settled empirically post-TRAIN is an honest outcome; a fourth sleeve forced in to
rescue a projection is not (rule 4).

---

## 14. Freeze

**SHA-256 (frozen 2026-07-22):** `02f85f5bdecc15fdfe211614f45f31d8d5368309eacbaf42a2339038e85a6b27`

The hash above is computed over this file's content excluding this hash line. Treat §1
(sign), §3 (construction), §4 (neutralization), §6 (cadence/caps), §7 (bands), and §9
(acceptance rule) as immutable. Any change after freeze starts a new pre-registration.
