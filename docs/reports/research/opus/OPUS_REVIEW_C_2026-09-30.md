# Opus Review C — closure review of VWAP-XREV-1 (M1c × M5c)

Reviewer: Claude Opus (independent subagent). Read-only w.r.t. both repos; recomputed from the saved CSVs and
events tables. Report reproduced verbatim (formatting normalised only). Prompt: "Does the evidence justify
closing this construct, keeping it open, or treating it as an empirically positive but incomplete finding?
Identify exactly what the evidence establishes and what it does not establish." Reviewed object: the assembled
report (before this section existed), the frozen protocol, results tables, research log and the closure ledger.

---

## Opus Review C: closure review of VWAP-XREV-1 (M1c × M5c)

**Verdict: close the construct.** It is not "positive but incomplete". The pre-registered confirmation
criterion was tested and failed. None of the corrections below blocks closure, but correction 1 (a factual
error) must be fixed before the report is marked final.

**Checks run (read-only):** recomputed from `primary_*_cells.csv`, `primary_*_excess_cells.csv`,
`primary_HOLDOUT_costs.csv` and `events_robust_dedup_all.parquet`. The rank-1 bars of `dedup_all` reproduce the
primary event means exactly, so the two event files are consistent.

### 1. What the evidence establishes, and what it does not

**Established (pre-specified):**
- The out-of-sample test failed. 0 of the 3 VAL-confirmed cells were HOLDOUT-confirmed, and up/h5 reversed sign.
- The strongest replication statement, which the report did not lead with: in all three confirmed cells the
  HOLDOUT 95% CI upper bound is below the VAL point estimate, so HOLDOUT excludes the VAL effect size
  (up/h5 +0.4 vs +4.6; down/h10 +6.9 vs +11.1; down/h30 +11.5 vs +18.7).
- Market-relative (R_ex), like with like: HOLDOUT session-weighted CI upper bounds (+5.3 at h10, +8.0 at h30)
  are below the TRAIN session R_ex (+6.2, +8.6); HOLDOUT event-weighted cluster CI upper bounds (+1.5, +3.7) are
  below the TRAIN event R_ex (+4.7, +5.8).

**Established (descriptive):** TRAIN event-level R_ex was +3.9 to +5.8 bp, two-way-cluster p ≈ 0.001 at h5–h30
only (h60 p = 0.156); below plausible cost even where strongest.

**Not established:** that the mechanism is absent; a date for the decay (it depends on weighting, correction 2);
anything about other anchors, universes, horizons or event definitions; results days; a β-adjusted benchmark.

### 2. §29 wording: accurate, over-claiming, or under-claiming?

Substance accurate; four problems:
- **(a) One hard factual error.** "All ten HOLDOUT net cells are negative at every κ" is false. Session-weighted
  h60 nets +3.18 (down) / +3.23 (up) at κ = 0 and +1.18 / +1.23 at κ = 1. Event-weighted net is negative in all ten
  cells at every κ. Neither h60 cell was VAL-confirmed, so the conclusion is unchanged, but the sentence is wrong
  in four places.
- **(b) The decay is dated on one weighting only.** "Absent from 2025Q3" holds for session-weighted R_ex
  (2025Q3 = +0.2). Event-weighted R_ex for 2025Q3 is +5.4 (TRAIN-like). On both weightings the ≈ 0 run starts at
  2025Q4. The TRAIN "+4…+6 per event" figure is event-weighted, so the report compared weightings inconsistently.
- **(c) The economic clause is presented as a test result.** "Not economically meaningful" is descriptive: the
  economic gate was conditional on HOLDOUT confirmation and was never reached; label it descriptive.
- **(d) The label is understated toward generosity** (see 3).

### 3. C6 or C5?

**Assign C5, construct-scoped (proposition A). Record "frozen-tree output: C6" verbatim as a preserved fact.**
- Every ledger C6 passed a confirmatory criterion and is incomplete elsewhere (CB-N50: HOLDOUT IC confirmed, G4
  missing; Carry v2: passed with implementation defects; TS Basis: strong SEALED through a broken gate).
- The closest precedent is scored C5: IVOL (TRAIN pass, HOLDOUT pass, SEALED fail) and Analog Path (HOLDOUT null).
  This construct has the same shape: VAL pass, then HOLDOUT fail on a predefined Holm criterion in 3 of 3 cells.
- The ledger's own test is met: §2(i) says a C5 needs a predefined criterion tested on data; the HOLDOUT
  confirmation criterion predates the read and failed.
- The tree's C6 branch keys only on the sign of the point estimate, so it emits a code whose gloss ("positive")
  is not satisfied: the two supporting estimates are non-significant raw +1.7 / +4.1 bp, R_ex about +0.4 / +0.8.
- This is a vocabulary mapping, not a rewrite: the frozen output, classification.json and every number stay
  unchanged; the protocol itself called its C-mapping "inferred".
- C6 would imply false hope ("incomplete" suggests something remains; HOLDOUT is spent, C9 unreachable, only
  forward data remains). The qualifier prevents false closure ("construct-scoped; M1c and M5c remain open"), the
  same scoping the ledger uses for Analog ("formulation-scoped") and Gann ("screen-scoped").

### 4. Non-declustered (`dedup_all`) "C7" variant

The disposal is **sound**, but the mechanism given was incomplete. The real cause is **weighting that depends on
the future**, not only overlap.
- Episode length is decided by the future path (how long |z| stays at or above c after each bar), and it predicts
  the outcome. HOLDOUT h30 by episode length: ≤ 10 bars: down +42 to +54 bp / up +42 to +56 bp; > 30 bars: −8.6 /
  −9.0 bp.
- Session and episode averaging therefore weight events by the inverse of future persistence. Episode-weighted
  mean: +12 to +56 bp; event-weighted (causal) mean: −8.6 to +5.3 bp; correlation between log session count and
  session mean: −0.27 to −0.68.
- No persistent-extreme effect is being dismissed: in HOLDOUT, event-weighted rank ≥ 6 bars average only +0.4 to
  +1.3 bp.
- The "60%" figure does not reproduce: 66% using contiguous runs, or 86% per name-session-side.
- Prominence is insufficient: the executive summary never names this variant; research log L28 ("10 of 10 …")
  contradicts ROBUSTNESS.md. A hostile reader could call this burying.
- The primary is affected the same way, but mildly: its session weighting uses counts known only at day end
  (correlation −0.04 to −0.23). This tilts the primary toward reversion, which makes the HOLDOUT null
  conservative. The report should say so.

### 5. Precision: can the report say it "rules out" an economically meaningful effect?

Use confidence intervals, not MDE (MDE is computed against zero at unadjusted α).
- **Can be said:** event-weighted (implementable) HOLDOUT two-way-cluster 95% upper bounds of gross return are
  ≤ 7.5 bp in all ten cells, below the ≈ 10 bp all-in cost (4.5 statutory + 2 × 2.75 slippage). Market-relative:
  all R_ex upper bounds below 10 bp (event ≤ 7.0, session ≤ 9.0). A gross effect at or above the all-in cost is
  excluded on the implementable estimand.
- **Cannot be said:** session-weighted raw — three upper bounds exceed 10 bp (down h30 +11.5, down h60 +15.3, up
  h60 +13.2); at zero slippage three event-weighted upper bounds (+5.9, +6.5, +7.5) exceed the 4.5 bp statutory
  cost alone. "Rules out" holds at plausible all-in cost on the event-weighted estimand; not for every estimand
  or at κ = 0.

### 6. Owner's rules

No violation found (no RFA use, no strategy, pre-specified vs post-hoc labelled, h60 and subgroups refused not
promoted, negatives preserved). Exposure points: corrections 1, 4 and 5.

### 7. Next action and housekeeping

"No next research action" is justified (no unread window exists; every rescue path is a new pre-registration).
Both housekeeping items are reasonable; the ledger entry must use the C5 code (correction 7). The substrate
findings (ISD `pit_universe` F&O flag; store name list chosen on a later universe) belong in the ledger
independent of this result.

**(a) Allowed closure statement**

"Under the frozen protocol VWAP-XREV-1, the construct is closed: own-volatility-scaled displacement from
cumulative typical-price session VWAP, first q = 0.99 crossing in 10:15–14:10, next-open entry, 5–60-minute
horizons, PIT F&O names the store carries. Its three VAL-confirmed reversion cells failed the pre-registered
one-shot HOLDOUT test: none confirmed, up/h5 reversed, and each HOLDOUT 95% interval excludes the VAL estimate.
HOLDOUT market-relative reversion is ≈ 0. Descriptively, on the implementable event-weighted estimand, HOLDOUT
excludes a gross effect at or above the ≈ 10 bp all-in cost in all ten cells. This closure is construct-scoped.
It does not close M1c or M5c as mechanisms, and it does not extend to other anchors, universes, horizons or event
definitions."

**(b) Category:** **C5, construct-scoped** (proposition A: predefined HOLDOUT confirmation criterion tested and
failed; frozen-tree output C6, recorded, on HOLDOUT point-estimate sign only; economic clause descriptive).

**(c) Required corrections**
1. Net-of-cost statements (four places): "negative at every slippage scenario tested" / "all ten net cells are
   negative at κ = 0, 2.75 and 5 (event-weighted and session-weighted)" / "net-of-cost negative in every HOLDOUT
   cell at every κ" / "all ten HOLDOUT net cells are negative at every κ". Fix: "Event-weighted net is negative
   in all ten HOLDOUT cells at every κ. Session-weighted net is negative in all ten at κ ≥ 2.75. The h60 cells
   (not VAL-confirmed) are +3.2 bp at κ = 0 and +1.2 bp at κ = 1."
2. Decay timing ("absent from 2025Q3 onward" / "≈ 0 for five consecutive quarters from 2025Q3" / "cluster
   p ≈ 0.001"). Fix: "≈ 0 or negative from 2025Q4 on both weightings (2025Q3: session +0.2, event +5.4)";
   scope the p-value to h5–h30.
3. "its 95% CI upper bounds sit below the TRAIN estimates" → add "at h10/h30/h60 (not h5/h15)" and "below the VAL
   estimates in all three confirmed cells".
4. "60% of its events…" and "The significance comes from equally weighting sessions" → "66% (contiguous runs) /
   86% (per name-session-side) of events are the 6th-or-later bar"; "Session and episode weighting down-weights long
   episodes, and episode length is fixed by the future path, so the C7 output is look-ahead weighting.
   Event-weighted rank ≥ 6 bars are +0.4 to +1.3 bp in HOLDOUT."
5. Executive summary: add "One post-primary variant (non-declustered events) would print C7 under the tree. It is a
   look-ahead weighting artefact (§20); event-weighted it is ≈ 0 and net-negative."
6. "positive on both sides in every variant (raw +4 … +17 bp …)" → add "(non-declustered: +22.5 / +23.0)".
7. "(frozen label C6; substantive reading C5-equivalent non-replication)" and "C6/non-replication" → "Vault
   category C5 (construct-scoped; frozen-tree output C6 on point-estimate sign, preserved verbatim)"; "and not
   economically meaningful" → "with no economically meaningful effect (descriptive; the economic gate was not
   reached)".
8. Research log L28 — append a correction row, do not edit in place: "9 of 10 variants; non-declustered prints 6
   HOLDOUT-confirmed cells (look-ahead weighting artefact)".
9. Add to §17/§28: "The pre-registered session weighting uses counts known only at day end and tilts mildly
   toward reversion (correlation between log session count and session mean: −0.04 to −0.23), which makes the
   HOLDOUT null conservative."

---

## What changed as a result (recorded)

| Point | Change |
|---|---|
| No number, table, label output or frozen file | **Unchanged.** `classification.json` still says C6 |
| Net-of-cost sentences | Corrected in all four places (I had written "all ten … negative at every κ"; session-weighted h60 nets are +3.2/+3.2 bp at κ = 0 and +1.2/+1.2 at κ = 1 — verified from `primary_HOLDOUT_costs.csv`) |
| Decay dating | Restated as ≈ 0/negative from 2025Q4 on both weightings; 2025Q3 event-weighted R_ex is +5.4 (verified); TRAIN cluster p scoped to h5–h30 (verified: .0008/.0014/.0006/.0002; h60 .156) |
| CI-vs-TRAIN claim | Scoped to h10/h30/h60; added the stronger "HOLDOUT excludes the VAL estimate in all three cells" (verified) |
| `dedup_all` | Mechanism rewritten as look-ahead weighting; the "60%" was my misreading of the `>20` rank bucket — the correct figure is 86% at rank ≥ 6 (verified); my own run-length check reproduces the sign flip (short episodes revert +13…+17 bp event mean, > 30-bar episodes continue −13 bp) though not Opus's exact magnitudes, so the report cites only the verified directions and my numbers. Now named in the executive summary |
| Category | Vault category assigned **C5, construct-scoped**; frozen-tree output **C6 preserved verbatim and labelled as a vocabulary-mapping mismatch found by Review C, not a change of any result** |
| Precision statement | Added: event-weighted HOLDOUT upper bounds ≤ 7.5 bp in all ten cells (verified) vs ≈ 10 bp all-in; explicit limits (session-weighted uppers >10 in three cells; at κ = 0 three event-weighted uppers exceed 4.5 bp) |
| Log | L28 kept as written; correction row appended |
