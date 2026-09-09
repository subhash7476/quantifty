# ISD Phase-0 — Pre-Registration (FROZEN)

**Status:** **FROZEN 2026-08-26** (operator approval after the review/defect-fix
cycle — §14). After freeze, NOTHING in this document may change in response to
any result (spec §7: "final fences pinned in Phase 0, never moved after").
**Date:** 2026-08-26
**Governing artifacts:** spec `2026-08-24-intraday-stocks-discovery-design.md`
(APPROVED) · plan `2026-08-24-isd-phase-1-substrate-certification.md` (PASS) ·
`ISD_PHASE1_SUBSTRATE_CERTIFICATION.md` (all gates PASS) ·
`ISD_PHASE0_CANDIDATE_RANKING.md` v3 + lead review (ACCEPT WITH REVISIONS,
applied) · RFA declarations + gate reports below.

---

## 1. Scope and non-goals

Freezes: fences, universe, substrate, two research families, grids, ledger,
nulls, BH policy, MDE/power, cost application, gates, termination. **Non-goals:
no conditioning covariates in v1 (R9); no beta-residualized variants (tuning
surface); no vendor-archive reads; no indicator zoo; no parameter edits after
freeze.**

## 2. Substrate and universe

- **Substrate: native-only** — the certified 1m equity store, 2023-01-02 →
  2026-08-24, 903 sessions (G1–G6 PASS). Vendor deep archive: certified but
  **excluded by rule** (Q1; unread reserve).
- **Universe: PIT F&O membership** from `data/isd/pit_universe.duckdb` (G5:
  173,900 rows, cross-feed agreement 1.0, unresolved=0) — ~200 names/session,
  entity-resolved via CSMP `symbol_entity_intervals` + ISIN issuer-prefix
  linkage. Membership is per-session; a name enters a formation only if it is
  intraday-present AND PIT-listed on that session. ADV cap per cell (below).
- **As-of date pinned:** 2026-08-24 (last certified session).

## 3. Window fences (frozen)

| Window | Range | Formations |
|---|---|---|
| TRAIN | 2023-01-02 → 2024-11-30 | 474 |
| HOLDOUT | 2024-12-01 → 2025-12-31 | 270 |
| SEALED | 2026-01-01 → spend date | ≥ **317** (spend floor) |

**SEALED spend gates (all three, mechanical, no judgment):**
1. HOLDOUT PASS (§9); 2. Q5 forward-PAPER ≥ 3 months complete (§9.8); 3.
**n_sealed ≥ 317** (projected spend ≈ 2027-03, calendar estimate disclosed).
The sealed read is one-shot, consumes 2026-01-01 → spend date, and retires the
construct on FAIL.

**Power table (script-generated verbatim, `scripts/rfa/power.py`, one-sided α=0.05):**

```
SEALED today   n=159  central:  0.5450
SEALED floor   n=317  pessimistic: 0.4116
SEALED floor   n=317  central:      0.8002
SEALED floor   n=317  optimistic:   0.9938
HOLDOUT        n=270  central:      0.7421
TRAIN          n=474  central:      0.9191
n_req central    (0.028, 0.20, 0.80): 317
n_req optimistic (0.035, 0.15, 0.80): 115
n_req pessimistic(0.020, 0.25, 0.80): 968
```

**Clarification (recorded so it cannot resurface as a discrepancy):** the RFA
gate reports central n_required = 329 — that uses the band midpoint δ = 0.0275
(gate convention). This document's declared central is δ = 0.028 (CB-N50 anchor
rounded down) → floor 317. Both numbers are on the table; the floor is 317 and
the declared central power at the floor is 0.8000.

**Calibration disclosure (R5):** at the floor, pessimistic-corner power is 0.41 —
if truth sits there, a SEALED FAIL happens 59% of the time even though the
effect is real. The read is calibrated to detect the central effect; a FAIL
retires the construct and cannot distinguish "weaker than central" from
"unlucky". Disclosed now.

## 4. Families (both: `rank_ic`, daily cross-section, EOD-flat, dollar-neutral)

### Family 1 — Opening-drive continuation (sign pinned: continuation)
- **Feature:** opening-period return = (window-end bar **close** − 09:15
  auction open)/09:15 open, per stock — the window-end price, not the
  window-start price (the draft's "window open" was an error that made the
  feature identically zero; corrected per operator review).
- **Windows (cells):** {09:15–09:45, 09:15–10:00}.
- **Entry:** the bar OPEN immediately after the window-end bar's close (09:46
  bar open for the 09:15–09:45 cell; 10:01 bar open for the 09:15–10:00 cell)
  — the feature is fully known at entry (no look-ahead). **Exit:** 15:29 bar
  close. **IC label = hold-leg return only** (entry open → 15:29 close) — the
  signal window is excluded from the label by construction (R2: no label
  overlap).
- **Sign:** continuation, pinned by mechanism (intraday momentum, GHLZ 2018;
  NSE auction concentration; in-house index-trend evidence). A negative TRAIN
  read closes the family — no sign-flip fishing.
- **Book:** rank on the feature; long top band / short bottom band (band =
  {20%, 40%} of names); dollar-neutral; EOD flat. **ADV cap:** position size
  per name capped at 10% of its trailing 20-session ADV as of T−1 (certified
  daily store) — no look-ahead into session T's volume.

### Family 4 — Overnight-gap cross-sectional (sign: TRAIN-burned once)
- **Feature:** gap = (09:15 auction open − prev_close)/prev_close, per stock,
  from the certified daily store joined on PIT ISIN keys; **CA ex-dates
  excluded per symbol** (gap across an ex-date is not a tradable signal;
  machinery: certified `corporate_actions` + G5 resolution).
- **Entry cells:** {09:16 bar open, 09:16 bar close} (the auction print at
  09:15 is not reachable in size). **Exit:** 15:29 bar close. **IC label =
  entry price → 15:29 close** — no overlap with the signal (measured at 09:15
  open).
- **Sign protocol:** direction discovered ONCE on TRAIN, then frozen (CARRY
  precedent); the registration (sign + digest) is written to the trial ledger
  BEFORE any HOLDOUT read. Confirmatory tests are one-sided in the registered
  direction; the opposite direction reads as failure. **m = 2 disclosed** (sign
  discovery + family IC gate).
- **Book:** rank on the gap; bands {20%, 40%}; ADV cap as in F1 (trailing
  20-session ADV as of T−1); EOD flat.

**Distinctness:** different information sets (overnight vs intraday flow).
**ρ₁₄ (book-level return correlation): reported at TRAIN, never optimized on**
(R8); composite talk waits until both families have gate results.

## 5. Grids (frozen; 4 cells per family; nothing may be added after first run)

The draft's "exit {none, 0.40}" dimension is dropped: a banded *exit* is a
multi-day-holding concept (PSB); this book is EOD-flat — every position enters
once and dies at 15:29, so the dimension adds path-dependence without a
turnover role. Frozen grids:

| Family | Grid |
|---|---|
| F1 | window {09:15–09:45, 09:15–10:00} × band {20%, 40%} |
| F4 | entry {09:16 open, 09:16 close} × band {20%, 40%} |

**Trial ledger** (`data/isd/trial_ledger.jsonl`, append-only, written before
results are visible per cell): family, cell_id, params, TRAIN IC, NW t,
AC1, cell τ, gross spread, net spread, null z (matched-null distribution),
verdict. **Cell selection:** per-cell BH at α = 0.05/4 = 0.0125; a family
proceeds only if **≥2 of its 4 cells qualify** (the multi-cell robustness the
v2 plateau rule embodied, restated for the 4-cell grid); family book =
equal-weighted mean of the qualifying cells. The ledger must show zero cells
added after the first run.

## 6. Multiplicity / BH policy (declared; R3)

- **Within family:** 4 cells → per-cell α = 0.05/4 = 0.0125 (family-wise BH).
- **TRAIN gate:** ONE family-level test per family (equal-weighted mean of the
  qualifying cells' ICs — ≥2 of 4 cells required, §5 — NW t) at α = 0.05,
  one-sided (F1: positive; F4: registered direction). Cell selection is a
  selection criterion, not a p-value.
- **Cross-family:** the two families are distinct constructs; each carries its
  own gate (no joint α). Family 4's m = 2 disclosed (§4).

## 7. Null constructions (matched, per cell)

1. **Random-entry null:** identical universe/dates/execution; ranks drawn
   i.i.d. per session; 1,000 iterations → IC null distribution per cell.
2. **Circular-shift null:** the signal series shifted by random block offsets
   (month-block) against the return series — preserves cross-sectional
   structure and autocorrelation; 1,000 iterations → family-level null.
Cell verdicts and the family-level t both use these null distributions
(empirical p), not asymptotic t alone (NW t reported alongside).

## 8. Cost model (application points frozen)

- **Fees:** `core/execution/equity/intraday_fees.py` (certified G6) at the
  ₹2Cr canonical capital, era-accurate.
- **Slippage:** entry at next-bar-open pays the measured G6 drift p90 by
  liquidity decile (2.35–2.90 bp/side); exit at 15:29 close pays the same
  band. No own-impact claims (R10 boundary).
- **Turnover:** **measured per cell on TRAIN at the frozen parameters**; the
  net-spread gate applies each cell's measured τ — never an assumed τ (R4).
  τ is re-measured on HOLDOUT at frozen parameters (report only, no edits).
- **Net-spread gate:** the family passes TRAIN only if its plateau book's net
  spread (gross − fees − measured slippage at measured τ) is positive.

## 9. Gates (each one-shot; freeze never revisited)

| Gate | Rule |
|---|---|
| TRAIN | cell ICs (BH α 0.0125, empirical nulls) + ≥2-of-4 qualifying cells + family-level IC test (α 0.05, NW) + net-spread > 0 at measured τ; F4 sign registered to the ledger first |
| HOLDOUT | one test per family (the frozen plateau book, equal-weighted), α 0.05, registered direction; report-only τ |
| Paper (Q5) | ≥ 3 months forward PAPER at the frozen book; **contamination rule: only pre-registered mechanical criteria may act — no parameter edits, no early abort on eyeballed P&L; any discretionary change restarts the paper clock and is logged in the trial ledger** (R6) |
| SEALED | one-shot at all three spend gates (§3), α 0.05, registered direction, net-spread gate; FAIL retires the construct (window spent for this construct only) |

## 10. Termination mapping (spec §9)

RFA ABANDON → family dead (both PROCEEDED, below) · TRAIN fail → family closed ·
HOLDOUT fail → construct retired, SEALED untouched · SEALED fail → construct
dead · two consecutive substrate-grounds closures → written reassessment.

## 11. RFA declarations (frozen at approval; bands never revised in response to results)

| Declaration | Bands | Verdict | SHA-256 (whole file, gate report) | Body SHA |
|---|---|---|---|---|
| ISD-OPEN-DRIVE | δ [0.020, 0.035] · sd [0.15, 0.25] | **PROCEED** (0.9938) | `934c069a395a2a3483fe87f4c02d003ce81b38ae88a9d8d5ec9421d735903edb` | `4ea18ec1…` |
| ISD-OVERNIGHT-GAP | δ [0.020, 0.035] · sd [0.15, 0.25] | **PROCEED** (0.9938) | `e476a03b0d13fb1814cfe246d4c0d17a71f17359fc03f94d157a458724c7862f` | `bbd23642…` |

MDE = 0.028 (central δ at which the floor yields power 0.80). Reports:
`ISD-OPEN-DRIVE_RFA.md`, `ISD-OVERNIGHT-GAP_RFA.md`. PROCEED means "not
provably infeasible" — a floor, not authorization; the gates above are the
authorization chain.

## 12. Prior-exposure disclosures (summary)

Full inventory in both declarations. Highlights: equity 1m store read only by
Phase-1 certification (no signal-level read) · CB-N50 TRAIN+HOLDOUT burned
(daily close-to-close, reversal +0.029, momentum −0.02 — closest anchor, scoped
by horizon/feature family) · index-pair intraday trending (continuation-flavored
index prior) · FTMO time-series intraday null (cross-sectional version untested)
· PSB monthly delivery-equity fee-died; delivery-% READ factor NOT used ·
CARRY/TS-Basis monthly/daily basis over SSF (different feature space) · SEALED
2026-01-01 → spend date genuinely unread.

## 13. Freeze checklist (what is pinned; nothing tunable remains)

Fences + floor □ · substrate native-only □ · universe PIT (G5) □ · two families
with signs/labels/execution □ · grids 4 cells each □ · ledger format □ ·
≥2-of-4 cell selection □ · BH policy □ · nulls □ · cost model + measured-τ □ ·
gates □ · paper contamination rule □ · RFA declarations + SHAs □ ·
prior-exposure record □.

---

## 14. Freeze record

**FROZEN 2026-08-26** — operator approval after the independent review cycle:
all five review defects fixed (power block regenerated verbatim from
`power.py`; F1 feature corrected to window-end close with next-bar-open entry;
exit-band dimension dropped (4-cell grids); ADV cap pinned to trailing
20-session ADV as of T−1; declaration headers corrected and gate reports +
§11 SHAs regenerated: `934c069a…`, `e476a03b…`). Nothing in this document may
change in response to any result from this point; the git commit of this
document set is the seal.
