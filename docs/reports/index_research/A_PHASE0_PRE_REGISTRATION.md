# A Phase-0 — Pre-Registration (FROZEN)

**Status:** **FROZEN 2026-08-27** (operator approval). After freeze, NOTHING
in this document may change in response to any result.
**Date:** 2026-08-27
**Governing artifacts:** `A_CONSTRUCT_DEFINITION.md` (design + decisions
D1–D6) · `A_INDEX_INTRADAY_PRIOR_EXPOSURE_AUDIT.md` (exposure boundary) ·
`A_INDEX_SLICE_CERTIFICATION.md` (**FAIL-with-register** — defect register and
availability absorbed per D2–D6; see §2) · `A_COST_SUBSTRATE_MEASUREMENTS.md`
(cost lanes) · RFA declaration `a_index_intraday.py` (FROZEN, whole-file
SHA-256 `221c6ca9…`, **PROCEED** 0.8720) · `ISD_PHASE0_PRE_REGISTRATION.md`
(machinery template: nulls, ledger, gates — adapted here to a single-name
time series).

---

## 1. Scope and non-goals

Freezes: fences, universe, construct (signal/entry/exit/position/roll/return),
grid, ledger, nulls, BH policy, power/floor, cost application, gates,
termination. **Non-goals: no thresholds or filters of any kind (every
tradeable session trades; any filter is a new construct); no overnight
holding (B's question); no gap signal (F4 territory, different information
set); no conditioning covariates; no parameter edits after freeze.**

## 2. Substrate and universe

- **Instrument:** `NSE_INDEX|Nifty 50` 1m bars, per-date files
  `data/market_data/nse/candles/1m/{YYYY-MM-DD}.duckdb`, 2012-01-02 →
  2026-08-21 (3,574 Nifty-bearing files; 3,508 full 375-bar sessions).
- **Execution vehicle (proxy):** Nifty futures (FUTIDX) via the cash-index
  series; basis treatment per D5 (mean-only, dispersion disclosed). Roll
  calendar: volume-dominance, 131 dates 2016-02-24 → 2026-10-26 (2016+);
  pre-2016 the near-month is unverifiable — cash proxy with the 2016+ basis
  figures as the disclosed assumption (§7).
- **Certification status: FAIL-with-register** (`A_INDEX_SLICE_CERTIFICATION
  .md`), absorbed as follows — nothing below is designed around; each class
  is excluded mechanically or absorbed with a measured distribution:
  - Permanent holes excluded: 2018-05 (22 sessions, absent from the vendor
    CSV itself), 2023-02-01→03-01 (20, vendor/native transition), recent lag
    (2026-08-24..26, live catch-up), 12 out-of-shape specials (Diwali
    Muhurat evening sessions — outside the session shape by construction).
  - Session-validity rule (mechanical skip, counted in the ledger): first
    bar date-stamped with the session, entry bar present (bar index 31/46),
    exit bar present (15:14 label). This excludes the 66 partials, the 45
    era-bound sessions, and the 3 native first-bar defects (2025-02-01,
    2026-02-25, 2026-03-02).
  - Absorbed with measured distributions: vendor-era boundary fidelity
    (opening print vs auction: med 3.2 bp / p99 25 / max 74 bp — the D3
    opening-print base); era label offset (~1 min, bar-count semantics);
    exit at 15:14 (D6) is an interior continuous print in all eras.
- **Eras (structural, certified):** vendor 2012-01-02 → 2023-01-31; native
  2023-03-01 → 2026-08-02; CAS 2026-08-03 → present (index 15:29 bar is the
  closing-auction print; the 15:14 exit is the last continuous print and the
  auction window is untraded by construction — D6).

## 3. Window fences (frozen; counts measured 2026-08-27)

| Window | Span | Tradeable sessions (cell 1) |
|---|---|---|
| TRAIN | 2012-01-02 → 2018-12-31 | **1,699** |
| HOLDOUT | 2019-01-01 → 2022-12-31 | **988** |
| SEALED | 2023-01-01 → spend date | 873 today; floor **1,270** |

**SEALED spend gates (all three, mechanical, no judgment):**
1. HOLDOUT PASS (§9); 2. forward PAPER ≥ 3 months complete at the frozen
   book (§9); 3. **n_sealed ≥ 1,270** (the central-band power floor —
   `ncp = 1.075·√(n/237) = 2.49` at n=1,270, i.e. power 0.80 at the central
   point of the declared band; calendar estimate ~2028-05 at 237/yr,
   disclosed). The sealed read is one-shot, consumes 2023-01-01 → spend
   date, and retires the construct on FAIL.

**Power table (script-generated verbatim, `scripts/rfa/power.py`, one-sided α=0.05):**

```
SEALED today   n=873   optimistic (S 1.45): 0.8720
SEALED floor   n=1270  central (S 1.075):   0.8002
SEALED floor   n=1270  optimistic (S 1.45): 0.9564
SEALED floor   n=1270  pessimistic (S 0.70): 0.4899
HOLDOUT        n=988   central (S 1.075):   0.7083
TRAIN          n=1699  central (S 1.075):   0.8911
n_req optimistic (1.45): 699 · central (1.075): 1270 · pessimistic (0.70): 2992
```

**Calibration disclosure (mirror of ISD R5):** at the floor, pessimistic-corner
power is 0.47 — if truth sits at the pessimistic point, a SEALED FAIL happens
~53% of the time even though the effect is real. The read is calibrated to
detect the central effect; a FAIL retires the construct and cannot distinguish
"weaker than central" from "unlucky". Disclosed now.

## 4. Construct (frozen — verbatim from the definition doc, D1–D6)

- **Signal:** opening-period return = (window-end bar close − opening print)
  / opening print, per session. Opening print = first bar open (D3).
  Bar-count window from the opening print: cell 1 = bars 0..30 (native
  labels 09:15–09:45); cell 2 = bars 0..45 (native labels 09:15–10:00).
- **Sign:** +1 continuation, pinned by mechanism (D1). Negative TRAIN closes
  the family — no sign-flip fishing.
- **Entry:** bar 31 / 46 open (the bar after the window-end bar). Fully
  known at entry; no look-ahead.
- **Exit:** the 15:14 bar close, EOD-flat (D6 — last continuous print in
  all three eras; the CAS auction window is untraded).
- **Position:** +1 if feature > 0, −1 if feature < 0, 0 if == 0; constant
  canonical notional ₹20,000,000; one position per session.
- **Roll:** contract selected at session open per the volume-dominance roll
  calendar (known at entry; flat overnight → 0 roll legs).
- **Per-trade return:** `r_t = sign · (exit_close − entry_open)/entry_open
  − costs_t`, in bp of notional, one observation per tradeable session.
  **Return series = {r_t}, net of all costs.**

## 5. Grid (frozen; 2 cells; nothing added after the first run)

| Cell | Window (bars from opening print) | Entry bar | Native labels |
|---|---|---|---|
| w30 | 0..30 | 31 | 09:15–09:45 → 09:46 |
| w45 | 0..45 | 46 | 09:15–10:00 → 10:01 |

**Trial ledger** (`data/a_index_intraday/trial_ledger.jsonl`, append-only,
written before results are visible per cell): cell_id, params, TRAIN mean net
bp, NW t, AC1, cell τ (n/a — fixed 1 trade/session), empirical p (both
nulls), net-spread verdict. The ledger must show zero cells added after the
first run.

## 6. Multiplicity / BH policy (declared)

- **Within family:** 2 cells → per-cell α = 0.05/2 = 0.025.
- **TRAIN gate:** ONE family-level test (equal-weighted mean of the
  qualifying cells' net per-trade returns — ≥1 of 2 cells required, §5) at
  α = 0.05, one-sided positive (D1: the sign is pinned, so there is no
  direction-discovery multiplicity; m = 2 cells, not 3). Cell selection is a
  selection criterion, not a p-value.
- **No cross-construct joint α:** A is its own construct (m = 2 disclosed).

## 7. Null constructions (matched, per cell — single-name adaptation of ISD §7)

1. **Sign-permutation null:** per session, the signal's sign is flipped with
   p = 0.5 (preserves the return-magnitude structure exactly; destroys the
   sign association). 1,000 iterations → null distribution of the mean net
   bp per trade per cell.
2. **Block-shift null:** the signal series is shifted by random block
   offsets (month blocks) against the return series — preserves
   autocorrelation structure. 1,000 iterations → family-level null.
Cell verdicts and the family-level test use these empirical nulls
(empirical p), NW t reported alongside.

## 8. Cost model (application points frozen)

- **Fees:** `core/execution/futures/futures_fees.py` (13 tests green;
  era-accurate schedules) at the canonical ₹2Cr notional — **3.81 bp round
  trip** (post-2024 era; era-accurate per date).
- **Slippage:** entry at bar 31/46 open pays the measured entry-bar drift
  p90 by era and cell (vendor/native: 0.66–0.78 bp/side); exit at the 15:14
  close pays the same band (ISD convention). Measured, never assumed.
- **Basis (D5):** mean component only (~0.4 bp/trade, direction-consistent
  carry) is subtracted; the dispersion (19.2 bp full-day within-contract
  p90) is a disclosed power property, not a cost.
- **Roll:** 0 legs (flat overnight); no roll charge.
- **Net-spread gate:** the family passes TRAIN only if the frozen book's
  mean net bp per trade is **positive** (the F4 killer, carried verbatim).

## 9. Gates (each one-shot; freeze never revisited)

| Gate | Rule |
|---|---|
| TRAIN | ≥1 of 2 cells qualify (BH α 0.025, empirical nulls) + family-level one-sided test (α 0.05, NW t) + net-spread > 0 |
| HOLDOUT | one test on the frozen family book (equal-weighted qualifying cells), α 0.05, positive direction |
| Paper (Q5) | ≥ 3 months forward PAPER at the frozen book; **contamination rule: only pre-registered mechanical criteria may act — no parameter edits, no early abort on eyeballed P&L; any discretionary change restarts the paper clock and is logged in the trial ledger** |
| SEALED | one-shot at all three spend gates (§3), α 0.05, positive direction, net-spread gate; FAIL retires the construct (window spent for this construct only) |

## 10. Termination mapping

TRAIN fail → construct closed (sign pinned: a negative family test is a
falsification, not a re-sign; a ≤0 net spread is the economics verdict) ·
HOLDOUT fail → construct retired, SEALED untouched · SEALED fail → construct
dead · two consecutive substrate-grounds closures → written reassessment.

## 11. RFA declaration (frozen at approval; never revised)

| Declaration | Bands | Verdict | Whole-file SHA-256 | Body SHA-256 (excl. header) |
|---|---|---|---|---|
| `a_index_intraday.py` | S_ann [0.70, 1.45] @ cadence 237 | **PROCEED** (0.8720) | `221c6ca97108fee6a9ee0e357a982a4cee1c3f3879e1f38c0523513ad6342d8b` | `c99012b044720cea03afc35a0080695d6a7a88866ae2acea2624e8786e4b1728` |

Report: `docs/reports/A-INDEX-INTRADAY_RFA.md`. PROCEED is a floor, not
authorization — the gates above are the authorization chain.

## 12. Prior-exposure disclosures (summary; full: `A_INDEX_INTRADAY_PRIOR_EXPOSURE_AUDIT.md`)

(a) index 1m 2012–2025 read structurally by the DayType regime pipeline
(regime classification target; feature space overlaps, target does not);
(b) index 1m 2023–2026 read by the pair-ratio analysis (mean reversion
falsified; trending slopes +1.10/+1.17 — direction-favorable, disclosed);
(c) ISD F1/F4 equity TRAIN reads (F1 continuation negative; F4 fade strongest
ever, cost-killed) — different instrument/level; (d) FTMO 0/41 corpus — the
standing out-of-repo falsification; (e) no trading-rule evaluation of index
1m exists on any window; (f) substrate certification FAIL-with-register,
absorbed per §2; (g) SEALED 2023-01-01 → spend date has no construct-level
read; pair exposure (b) is for the ratio hypothesis only.

## 13. Freeze checklist (what is pinned; nothing tunable remains)

Fences + floor □ · substrate + certification register □ · eras (vendor /
native / CAS) + 15:14 exit (D6) □ · signal/entry/exit/position/roll/returns
□ · 2-cell grid □ · ledger format □ · ≥1-of-2 cell selection □ · BH policy
(m=2) □ · nulls (sign-permutation + block-shift) □ · cost model + lanes □ ·
basis mean-only (D5) □ · gates + paper contamination rule □ · RFA
declaration + SHAs □ · prior-exposure record □.

---

## 14. Freeze record

**FROZEN 2026-08-27** — operator approval. The RFA band [0.70, 1.45] was
ratified 2026-08-27 (declaration SHA `221c6ca9…`); the exit was re-pinned to
15:14 (D6) on the same day in response to the CAS register (A6) — the last
structural decision before freeze. Nothing in this document may change in
response to any result from this point; the git commit of this document set
is the seal. TRAIN is the next gate (§9), runnable only at the frozen
parameters.
