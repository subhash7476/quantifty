# N50-LS: Nifty 50 Cross-Sectional Long-Short — Pre-Registration

**Status:** DRAFT — pending RFA gate. Not frozen until the RFA declaration
(`governance/rfa/declarations/n50_ls.py`) is written, SHA-pinned, and gated.
**Lineage:** fresh namespace. Combines the validated CB-N50 cross-sectional
ranking with the TS-Basis time-series-basis calculation. **Not** a CB-N50
continuation and **not** a TS-Basis re-authorization (see §6).

---

## 1. Construct

### 1.1 Architecture

```
stock-level combined score → beta-neutral quintile long-short book
       (Nifty 50 constituents)   traded via single-stock futures → book P&L
```

The primary object is a **market-neutral long-short portfolio**. CB-N50
established that the combined feature score ranks Nifty 50 constituents by
next-day return (out-of-sample daily cross-sectional IC **+0.029**, HOLDOUT
2020-2022, NW t=4.35). CB-N50's *index-futures* expression via breadth was
structurally void — a cross-sectionally demeaned signal is market-neutral by
construction and carries no index-direction information (`CB_N50_TRAIN_REVIEW.md`).
The correct tradeable home for a ranking is a **long-short book**, which
*embraces* the market-neutrality instead of fighting it. That is this construct.

### 1.2 Why the CB-N50 + TS-Basis combination is non-redundant

CB-N50 already uses a basis feature, so "add TS-Basis" needs justifying. The two
basis measures are **different decompositions of the same raw quantity**:

| Feature | Question it answers | Axis |
|---|---|---|
| CB-N50 cross-sectional basis | Is this stock's basis rich/cheap **vs. its peers today**? | cross-sectional |
| TS-Basis time-series basis | Is this stock's basis rich/cheap **vs. its own history**? | time-series |

A stock can be cheap vs. peers but rich vs. its own history, or the reverse.
Combined with short-term reversal (a fast, orthogonal effect), the three
features span fast-reversal / cheap-vs-peers / cheap-vs-own-history. This is a
genuine three-way combination, not one factor counted twice.

### 1.3 Signal (frozen — no new degrees of freedom)

Per constituent, per day, the combined score is the **equal-weighted mean of
three cross-sectionally z-scored features**. Signs are **pinned here**, before
any book P&L is computed:

| Feature | Definition | Sign | Source |
|---|---|---|---|
| **Reversal** | `−(close_t / close_{t−1} − 1)`, minus cross-sectional median | **+** | CB-N50 (frozen, verbatim) |
| **Cross-sectional basis** | residual basis `(fut_close/spot_close − 1)` annualised, winsorised ±3σ, minus cross-sectional median | **+** | CB-N50 (frozen, verbatim) |
| **Time-series basis** | this stock's daily basis z-scored vs. its own trailing 252-row basis distribution, winsorised ±3σ | **+** | TS-Basis calc (frozen) |

- Each feature is cross-sectionally z-scored within the daily Nifty 50 panel
  (subtract cross-sectional mean, divide by cross-sectional std), winsorised ±3σ,
  **before** combination.
- Combination weight is fixed **1/3 per feature**. No weight optimisation on any
  window. If a feature is unavailable for a stock on a day (e.g. insufficient
  basis history for TS-basis), that stock is scored on the remaining features
  with equal weights among those available.
- Momentum is **not** included — CB-N50's TRAIN showed daily momentum is
  wrong-signed (short-horizon reversal); it was dropped and is not revived here.

### 1.4 Portfolio construction (frozen)

- **Top quintile long / bottom quintile short** by combined score (≈10 long, 10
  short of ~50), **equal-weight within each leg**.
- **Beta-neutral**: the long and short leg notionals are scaled so the book's
  net Nifty beta ≈ 0 (betas estimated from a trailing 60-day window on the
  *market leg*, i.e. each stock's beta to Nifty). A dollar-neutral-only book
  would carry residual beta that contaminates the Sharpe; since we have
  established the signal has no index-direction content, any beta exposure is
  pure noise and is removed.
- **Daily rebalance**: recompute the target book each day from the post-close
  signal; hold `open(t+1) → open(t+2)`, rolling. No volatility scaling, no Kelly,
  no regime gearing — position sizing is fixed to the beta-neutral equal-weight
  legs.
- **Low-N rule**: if fewer than 30 constituents are scorable on a day, the day is
  skipped (no book), consistent with CB-N50 §3.1.

### 1.5 Execution vehicle (frozen)

**Single-stock futures (SSF, `inst_type='FUTSTK'`)** on the Nifty 50 names — all
50 are liquid F&O underlyings. This is the load-bearing choice: SSF avoids the
**delivery-equity STT wall** (0.1% *per leg*) that killed every prior fast cash
construct (PSB-1/PSB-2). Note the self-reference — one feature is the futures
basis and the vehicle is the future — this is expected for a basis-aware book and
is disclosed, not hidden.

### 1.6 Execution & cost model (frozen)

- **Timing**: signal computed after day-t close; enter at the SSF **open** on t+1,
  exit at the SSF open on t+2. No intraday timing. Target return for any IC
  cross-check is the constituent's SSF open(t+1)→open(t+2) return.
- **Roll**: near-month → next-near-month, 2 trading days before expiry. A
  position held through roll exits the expiring contract at its open and re-enters
  the new contract at its open on the roll date. Roll cost is charged.
- **Costs (era-accurate)**: SSF round-trip — brokerage + STT (0.0125% sell side on
  futures) + exchange txn + SEBI turnover + stamp (buy side) + GST on
  (brokerage+exchange). Slippage κ = 2–3 bps/side at the open auction. Turnover is
  **measured, not assumed** — a daily-rebalanced quintile book has high turnover
  and the net Sharpe must survive it.

---

## 2. RFA gate — RUN FIRST, may ABANDON

**This construct is not authorised to build until it clears the RFA gate. The
gate may return ABANDON, in which case the construct stops here.** This section
specifies the declaration; the frozen numbers live in
`governance/rfa/declarations/n50_ls.py`.

### 2.1 Metric and why it is harder than CB-N50's

| | CB-N50 | N50-LS |
|---|---|---|
| Metric | `rank_ic` | **`per_trade_pnl`** |
| ncp | (δ/sd)·√n, n=887 daily ICs | **S·√T**, T≈3.6 yr |
| Escape hatch | measurement density (887 obs) | **none — cadence cancels** |

CB-N50 cleared its RFA because `rank_ic` gave 887 daily observations. A book's
P&L is a `per_trade_pnl` metric, and per the RFA methodology `ncp = S·√T` with
**cadence cancelling** — trading daily instead of weekly buys *no* power. The only
levers are the annualised Sharpe `S` and the calendar window `T`. `T` is fixed at
the ~3.6-year sealed window (SSF history cannot predate 2016, and TRAIN/HOLDOUT
are prior-exposed — §4). So the gate reduces to: **is a defensible annualised
Sharpe high enough?** This is the RS-MOM wall, and it is why the gate is a genuine
coin-flip rather than a formality.

### 2.2 Sharpe-band derivation (independently defended, not fitted)

For power 0.80 two-sided at α=0.05, `ncp ≈ 2.8`, and with `√T = √3.6 ≈ 1.9` the
construct needs a defensible annualised Sharpe of roughly **≥ 1.47 at the
optimistic corner** to PROCEED.

The band is derived from the HOLDOUT IC via Grinold-Kahn (`IR = IC × √BR`), **not**
from a fresh in-sample book read:

- **Anchor IC**: HOLDOUT +0.029 (the least-contaminated number). *Not* TRAIN
  +0.059 — that is selection-inflated by the lookback/feature-drop choices. Per
  the C2 lesson, the effect size must be defended, not inherited from the largest
  in-sample read; if anything +0.029 is itself optimistic.
- **Breadth bounds**: BR (independent bets/year) is bounded below by treating each
  daily cross-section as one bet (BR≈252 → IR≈0.46) and above by treating each of
  ~40 positions per day as independent (BR≈10⁴ → IR≈2.9). Neither extreme is real;
  sector/factor correlation makes effective breadth far below the upper bound.
- **Literature anchor**: liquid single-name daily cross-sectional L/S (reversal +
  carry/value) realise annualised Sharpe ~0.5–1.5 gross, lower net.

The declaration will freeze an annualised-Sharpe band spanning these
(indicatively ~[0.5, ~1.8]) with `cadence_per_year = 252`. **The gate — not this
prose — decides.** If the optimistic corner cannot reach 0.80 power, ABANDON, and
the sealed window is never touched.

### 2.3 Order of operations (non-negotiable)

1. Write + SHA-freeze `n50_ls.py` declaration.
2. Run `scripts/rfa/run_rfa.py` → PROCEED or ABANDON.
3. **ABANDON → stop.** Record the kill; no build, no data read.
4. **PROCEED → build**, then the phase gates (§5).

---

## 3. Pre-build frozen requirements

None may be revised in response to any result.

- **Universe**: PIT Nifty 50 membership from the certified MCWB substrate
  (`nifty50_pit_membership.json`), **one-month-lagged** per the substrate fix
  (`CB_N50_SUBSTRATE_CERTIFICATION_REVIEW.md`) — the bulletin for month M governs
  month M+1. The same lag applies to the free-float weights used for beta-neutral
  sizing and any weighting.
- **Entity continuity**: returns and basis series must be joined at **entity**
  grain across rename/merger seams (ZOMATO→ETERNAL, TATAMOTORS→TMPV, HDFC→HDFCBANK)
  so no per-stock series is severed at a ticker change. The **TATAMTRDVR DVR
  double-listing** (2016-04→2017-08) must be collapsed into TATAMOTORS — the book
  must not hold the same economic entity twice.
- **Betas**: estimated from a trailing 60-day window using the market leg (each
  stock's return vs. Nifty), finalised after the day-t close.
- **Missing data**: a stock with missing price/basis on a day is excluded from
  that day's cross-section; days with <30 scorable names are skipped.
- **Costs**: era-accurate SSF fee schedule + roll cost + κ slippage, applied
  before any P&L is reported.

---

## 4. Windows & prior exposure

| Window | Dates | Status | Role |
|---|---|---|---|
| TRAIN | 2016-02 – 2019 | **Prior-exposed** (CB-N50 read the ranking here) | Not a gate. Pre-registered book params only; used to *characterise* turnover/cost, never to select. |
| HOLDOUT | 2020 – 2022 | **Prior-exposed** (CB-N50 IC read here) | Not a clean gate. Optional pre-registered book-P&L sanity read, disclosed as contaminated. |
| **SEALED** | **2023 – 2026** | **CLEAN — never read as book P&L by any construct** | **The single one-shot gate.** |

The one honest confirmatory budget is the 2023-2026 SEALED window. Because the
ranking's TRAIN/HOLDOUT are already burned, **all** book construction parameters
are pinned in this pre-registration; nothing is tuned on TRAIN/HOLDOUT. The
SEALED read is one-shot and frozen in `N50_LS_SEALED_SNAPSHOT.json`.

---

## 5. Phases & acceptance gates

| Phase | Gate | Criterion | Failure |
|---|---|---|---|
| RFA | R | Optimistic-corner power ≥ 0.80 on `per_trade_pnl` | ABANDON — stop, no build |
| Build | — | Construction parity: book reproduces from frozen spec deterministically | Fix before proceeding |
| TRAIN (char.) | — | Report net Sharpe, turnover, cost drag, MaxDD (characterisation, **not** a pass/fail gate — prior-exposed) | — |
| HOLDOUT (opt.) | H | Book net-of-cost Sharpe > 0 and directionally sane (disclosed as prior-exposed) | Reconsider before spending SEALED |
| **SEALED** | **S1** | **Book net-of-cost annualised Sharpe > 0 and consistent with the RFA-declared band** | **Construct falsified** |
| SEALED | S2 | MaxDD and turnover within the ranges characterised on TRAIN (no regime blow-up) | Construct falsified |

Promotion to PAPER requires S1+S2 PASS. No promotion happens inside this
pre-registration.

---

## 6. What this is NOT

| Rejected framing | Reason |
|---|---|
| A CB-N50 reopen | CB-N50 is closed; its breadth→futures expression is falsified. This is a new metric (`per_trade_pnl`), new vehicle (SSF book), new gate. |
| A TS-Basis re-authorization | TS-Basis (monthly, SSF ~180) spent its sealed window; that de-authorization is untouched. N50-LS borrows only the *calculation*, on the Nifty 50 universe, with its own clean window. |
| An index-timing bet | The book is market-neutral by construction — the opposite of an index bet. |
| A cadence-for-power play | `ncp = S·√T`; daily rebalance buys no power. Only Sharpe and the fixed window matter. |
| A wider-universe grab | SSF ~180 has a spent/encumbered window; Nifty 50 was chosen precisely for its clean sealed budget. A ~180-name extension is deferred to its own declaration. |

---

## 7. Prior-exposure disclosure

| Read | Universe | Freq | What was seen |
|---|---|---|---|
| CB-N50 TRAIN/HOLDOUT | Nifty 50 | daily | Combined reversal+basis ranking IC (same features, same universe) — TRAIN 2016-19, HOLDOUT 2020-22 |
| TS-Basis (monthly) | ~180 SSF | monthly | Basis-level signal incl. a **spent** sealed read (2026-07-24) |
| TS-Basis Daily | ~180 SSF | daily | Basis-level daily; TRAIN/HOLDOUT selection-burned (research-only) |
| Carry sleeve | ~180 SSF | monthly | Residual-basis IC experience |

**No prior read exists on:** the Nifty 50 long-short **book P&L** on any window,
or the reversal+xs-basis+ts-basis combination as a traded book. The 2023-2026
SEALED book-P&L read is genuinely unspent.

---

## 8. References

- `docs/reports/CB_N50_PRE_REGISTRATION.md` — parent ranking construct
- `docs/reports/CB_N50_TRAIN_REVIEW.md` — why breadth→futures is void; L/S is the home
- `docs/reports/CB_N50_SUBSTRATE_CERTIFICATION_REVIEW.md` — MCWB lag, entity/DVR caveats
- `docs/reports/TS_BASIS_REAUTHORIZATION_ASSESSMENT.md` — TS-Basis status (the calc source)
- `governance/rfa/declarations/cb_n50.py` — rank_ic declaration template
- `scripts/rfa/power.py`, `scripts/rfa/gate.py` — the gate this must clear first
- Grinold & Kahn — fundamental law of active management (IR = IC·√BR)
- Jegadeesh (1990) reversal; Koijen-Moskowitz-Pedersen-Vrugt (2018) carry/basis
