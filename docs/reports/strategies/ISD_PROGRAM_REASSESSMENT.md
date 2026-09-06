# ISD Program Reassessment — the binding constraint has migrated to arithmetic

**Date:** 2026-08-27
**Artifact class:** program-level decision record (terminal for the cash-equity
intraday EOD-flat quadrant).
**Governing artifacts:** `ISD_PHASE0_PRE_REGISTRATION.md` (FROZEN, SHA-16
`f77b163c0df646cf`) · `ISD_BATTERY_TRAIN_REPORT.md` (TRAIN read, 2026-08-26) ·
trial ledger `data/isd/trial_ledger.jsonl` · RFA declarations
`ISD-OPEN-DRIVE_RFA.md` / `ISD-OVERNIGHT-GAP_RFA.md`.
**This memo records a reassessment. It authorizes nothing:** no construct code,
no RFA declaration, no data read. Any successor starts its own RFA +
pre-registration, with the ISD finding as disclosed prior exposure.

---

## 1. The battery outcome (per §9/§10 mapping — closed, correctly)

TRAIN verdict: **FAIL — both families closed.** 474 sessions (2023-01-02 →
2024-11-30), seed 42, prereg SHA-16 `f77b163c0df646cf`.

| Family | Sign | Cells | Family IC | NW t | p (shift null) | Net bp | Why it closed |
|---|---|---|---|---|---|---|---|
| F1 opening-drive | +1 (pinned continuation) | 0/4 qualify | nan | 0.00 | nan | 0.0 | Sign negative on TRAIN (w0945 IC −0.0166, t −2.81); pinned sign closes the family — no sign-flip fishing |
| F4 overnight-gap | −1 (registered once, then frozen) | **4/4 qualify** | **−0.0289** | **−6.09** | **0.0000** | **−3196.2** | IC gates all pass; **net-spread gate fails** (net < 0 at measured τ=2.0) |

Termination mapping applied cleanly: TRAIN fail → family closed, twice →
battery closed. **HOLDOUT never read; PAPER never started; SEALED
2026-01-01 → present untouched; spend floor n≥317 never approached.**
The two RFA declarations (both PROCEED, 0.9938) remain frozen artifacts —
their bands were never the point of failure and are not revised.

## 2. The finding that makes this a reassessment, not a clean close

**F4 measured the strongest cross-sectional effect this repo has ever seen on a
fresh, unread window — and still lost money.** All four cells qualify at the
BH α = 0.0125 (empirical null p = 0.0000, null z ≈ −8.5 on the strongest cell);
family-level IC −0.0289 with NW t −6.09 against the circular-shift null
(p = 0.0000). For scale, the previous fresh-window bests were CB-N50 HOLDOUT
IC +0.029 (NW t 4.4) and Carry HOLDOUT IC +0.046 (t 2.60) — F4 is stronger on
|t| than either, at the same order of effect size.

The battery therefore did not fail for lack of a signal. It failed because the
measured book-level economics cannot carry it. That is the constraint having
migrated a third time: PSB died on fees, C5/C4/F1 died on demonstrability,
and the ISD battery produced a *demonstrated* effect that is *economically
unviable* in its execution vehicle.

## 3. The wall, decomposed (all numbers script-generated)

Per-session cost and gross for the four F4 cells (ledger, final run
2026-08-26T20:28:25; implied cost = gross − net):

| Cell | Gross spread (bp/session) | Implied cost (2·slip + fees) | Net spread |
|---|---:|---:|---:|
| e_open @ 0.2 | +6.02 | 10.59 | −4.57 |
| e_close @ 0.2 | +4.41 | 10.59 | −6.17 |
| e_open @ 0.4 | +4.43 | 12.07 | −7.63 |
| e_close @ 0.4 | +3.18 | 12.07 | −8.88 |
| **Best cell** | **+6.02** | **10.59** | **−4.57** |

Fee-only round-trip cost by ticket size (certified `intraday_fees.py`,
`breakeven_round_trip_bps`, era-accurate schedule):

| Ticket | Fee-only (bp) | Note |
|---|---:|---|
| ₹2,00,000 | 6.00 | 100-name book |
| ₹2,50,000 | 5.53 | 40-name book at ₹2Cr capital (F4 0.2-band ticket) |
| ₹5,00,000 | 4.58 | 20-name book |
| ₹12,50,000 | 4.02 | F4 0.4-band ticket |
| ₹20,00,000 | 3.87 | 10-name book |

Slippage: G6 drift p90 by liquidity decile, 2.35–2.90 bp/side (both sides,
entry at next-bar open, exit at 15:29 close).

**Why the wall is arithmetic, not signal quality:**

- At the battery's own tickets the round-trip cost is 10.6–12.1 bp/session
  against a best gross cell of +6.0. Even if every ISD-style signal in this
  quadrant were as strong as F4, the cost floor sits above the gross ceiling.
- The most optimistic micro-optimization that is still honest — 10-name book
  (fees → 3.87 bp) and decile-10-only names (slippage −0.7 bp round trip) —
  lands at **≈ 8.6 bp/session** against a best-cell gross of **+6.0**.
  The deficit is ~2.5 bp/session under assumptions more generous than anyone
  would defend. Nothing in the measured G6 bands or the fee schedule moves
  that number.
- Slippage is insensitive to ticket size (it is a drift percentile, not
  impact); fees floor at the ₹20 floor per executed order, so the 10-name
  book is the asymptotic best case, not a direction with headroom.

**Conclusion, recorded as a closure rule: cash-equity intraday, EOD-flat is
closed by arithmetic — at any signal strength that can plausibly be defended
in this repo's governance framework.** This closes the *quadrant*, not just
the two families. Any future proposal inside this quadrant must first clear
the cost floor (≥ 8.6 bp/session against any defensible gross) — an
arithmetic argument, not a statistical one.

## 4. What is genuinely untried (survives the cost filter)

### A. Index intraday — Nifty futures (top candidate)

- **Costs drop to ~3–5 bp/trip.** No ₹20 floor dominance at futures lot
  sizes, no delivery STT, tight index spreads. The 10.6 bp/session wall
  becomes a ~3–5 bp/trip lane.
- **Power math works.** At ~2 trades/day, the sealed window
  (2026-01-01 → present) yields n ≈ 600+ trades. `ncp = S·√n` → a
  per-trade Sharpe of ~0.10–0.15 clears 0.80. The RS-MOM wall (Sharpe ≥ 1.3)
  was a *weekly-cadence artifact* — √T_sealed ≈ 1.89 collapsed at n=186;
  daily-cadence n=600+ restores √n ≈ 24.5. The constraint that killed
  RS-MOM does not apply at this cadence.
- **Prior.** The FTMO corpus is the standing falsification (0/41
  time-series intraday patterns on USTEC/gold) — but the in-house
  index-pair work measured NSE index intraday **trending**
  (+1.10/+1.17 slopes) — the one piece of evidence that this quadrant
  differs here. Weak-moderate prior, genuinely unread quadrant, the only
  cost-viable one.
- **Falsifiability.** The FTMO null is directly testable cheaply — the
  first intraday trend probe either reproduces the NSE slope evidence or
  joins the corpus.

### B. Multi-day carry of the ISD signals on SSF

- Gap-fade at T+1..T+5 amortizes the ~10 bp/session cost over days;
  SSF has no delivery STT. The economics direction is right.
- **Two problems, both recorded, neither waived:**
  1. **Persistence is unmeasured.** F4's grid is frozen; this is a new
     construct with its own RFA, its own power arithmetic, and its own
     prior-exposure statement.
  2. **The futures-momentum prior is negative.** F1's CI-includes-zero
     (TRAIN +0.0154 optimistic / −0.0091 pessimistic, 2019–2022 HOLDOUT
     favorable-regime caveat) is the standing read on multi-day SSF
     signals.
- The measurement question — "does the fade survive overnight?" — is the
  cheapest possible next probe, but it can only live inside a new
  construct's discipline, never as a bolt-on read of a closed battery.

### C. Micro-optimizations of the dead construct — no

Quantified in §3: nothing clears the wall, and reopening F4's grid
post-freeze is precisely what the governance forbids. Closed without
further discussion.

## 5. What will not be tried

- **Anything else in cash-equity intraday EOD-flat** — reversal variants,
  more features, finer bands. Closed by the same §3 arithmetic; the
  quadrant is closed, not the parameterization.
- **Delivery-equity multi-day** — the PSB STT wall (0.1%/leg) is ~40× the
  ISD cost problem; documented three times, re-listed for completeness.

## 6. Successor ordering and dependencies

1. **A (index intraday) first.** Cost-viable today, power-clearable at
   realistic trade counts, and its falsification is cheap and direct.
2. **B (SSF multi-day) only if the persistence question is answered
   favorably** inside A's or its own pre-registration. **Pin this
   dependency now:** B is conditional on a persistence measurement; it is
   not authorized by this memo, and a later operator must not treat B as
   "already cleared" by the ISD finding alone.
3. Both successors disclose the ISD finding as prior exposure: F4's −0.029
   IC as the strongest fresh-window effect ever measured here, and the
   §3 cost wall as the reason the cash-equity quadrant is closed.

## 7. Record-keeping

- SEALED 2026-01-01 → present: **untouched**. HOLDOUT 2024-12-01 →
  2025-12-31: **unread**. The F4 construct is dead; its gates and window
  are not inherited by any successor.
- This memo is the canonical prior-exposure anchor for successor
  declarations. Any successor RFA must cite it; the cost table (§3) is
  the arithmetic floor that successor proposals must be measured against
  in their own vehicles.
