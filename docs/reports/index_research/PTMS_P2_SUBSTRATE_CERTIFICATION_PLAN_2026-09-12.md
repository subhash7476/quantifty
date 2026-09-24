# PTMS — P2 Substrate Certification Plan

**Date:** 2026-09-12 · **Authority:** operator ruling PTMS-2026-09-12
**Scope:** certify the surfaces PTMS may use, and establish V1 timestamp semantics.
**This plan authorizes no reads beyond meta + substrate verification and no construct code.**

---

## 0. What P2 must deliver

P2 ends when a construct can ask *"is this surface, over this window, safe to use, and on
what clock?"* and get a certified answer. Four gates:

| Gate | Question | Blocks |
|---|---|---|
| **C1 — Timestamp semantics (V1)** | What clock is each era on, and how is era resolved? | Everything intraday |
| **C2 — PIT & entity integrity** | Universe, entity, ISIN, CA, calendar | Everything cross-sectional |
| **C3 — Tradeability & synthetics** | Which bars represent trades? | Everything post-CAS |
| **C4 — VIX certification** | Are the three VIX assets usable, and how? | Any volatility-state covariate |

The **L0 access layer** (alignment record §7) is P2's implementation vehicle: certification
arms and the loader are the same code, so a certified guarantee is one a construct cannot
bypass.

---

## 1. Gate C1 — V1 timestamp semantics **(elevated to a gate by operator ruling)**

**The measured facts.** Index 1m runs `09:16 → 15:30` for 2012-01-02 → 2022-12-30 plus
2023-01-31; `09:15 → 15:29` from 2023-01-02 for every symbol. `ingest_reference_1m.py`
declares `EXPECTED_BARS = 375  # 9:15 to 15:29 inclusive` while writing 09:16-first rows.

**The daily-close test is retired.** Operator ruling: explicitly insufficient, must not be
reused as certification evidence. It was tried and failed to discriminate — the last 1m close
matched the 1d close in *neither* era (2020-01-02: 12282.35 vs 12282.20; 2023-06-15: 18682.15
vs 18688.10), because an index close is not the last traded print and the 1d store is a
different source.

**Start from what already exists — do not rediscover it.** The intraday analog-path track
carries the repo's only recorded treatment of this seam (see `PTMS_I_BETA_DEPENDENCY_AUDIT_2026-09-12.md` §5):
vendor era **end-labelled** (bar stamped *t* covers *t−1 → t*), native era **start-labelled**
(bar stamped *t* opens at *t*), era resolved by the **observed first-bar stamp, not the
calendar date** (AP-D4), with 20 January-2023 sessions whose metadata disagreed with their
labelling already handled. **Operator ruling (P2/P3 review): AP-D4's `observed_bar_labeling` is now the FROZEN CANDIDATE
SEMANTIC RULE, not a newly invented hypothesis.** C1's job is to **independently verify and
generalize it store-wide** using the evidence arms below. It may not be rediscovered,
replaced, or re-derived without evidence that contradicts it.

**Admissible evidence (three arms; C1 passes on at least two agreeing).**

| Arm | Test | Why it discriminates |
|---|---|---|
| **C1-a — source documentation** | Vendor bundle's own spec for the reference CSVs; Upstox V3 candle-interval semantics for the native era | Direct evidence; needs no inference. Requires the operator to supply the vendor statement |
| **C1-b — cross-source intraday alignment** | Compare the pre-2023 index slice against a *third* intraday feed on the same dates at ±1 minute shifts; the shift that maximizes exact-match tells the offset. Candidate feeds: `1m_vendor/` (101 symbols, 2015-02-02 → 2025-08-06) for a co-listed name; the vendor VIX CSV where it overlaps | The same shift test that settled vendor-CSV-vs-canonical VIX (8,227 / **8,249** / 8,227 at −1/0/+1). Bar-level, not daily aggregate — this is why it discriminates where the close test did not |
| **C1-c — event anchoring** | On dates with a known intraday timestamped event (circuit breaker halts 2020-03-13/23 — already enumerated in the analog-path defect register), test which labelling places the event in the correct minute | Independent of any feed's convention; anchors to exchange time |

**Deliverables.** (i) A certified era rule, expressed as AP-D4's observed-first-bar-stamp
mechanism generalized store-wide; (ii) an L0 loader that applies it and **refuses** an
unrecognized first-bar stamp rather than guessing; (iii) a contiguity + label census over all
3,613 files recording the observed stamp per file — this is the artifact that makes the seam
visible for good.

**Consequence if C1 cannot be resolved.** The 2012–2022 and 2023+ index slices must be
treated as **two surfaces on different clocks**, not one. Any construct spanning them
declares which clock it uses and accepts the other era as out of scope.

## 2. Gate C2 — PIT & entity integrity

Contract-shaped, three unfiltered arms at entity grain (PSB-1's suite is the template; its
six structural-defect classes are the known failure modes). Arms: intra-symbol CA shape ·
cross-symbol entity handoff (`symbol_entity_intervals`; recycled tickers) · ISIN
issuer-prefix linkage (face-value re-issue) · `prev_close` identity across series ·
adjusted-series continuity (zero view-induced fabrications).

**PTMS-specific additions.** (a) `pit_membership` (898 sessions, 2023-01-02 → 2026-08-24)
must be certified as a *universe*, not as the writer's symbol set — the store map's own
pitfall says a per-day file's symbol set is whichever universe its writer used. (b) The
2,515-session vendor VIX CSV and the 1d index family need calendar contiguity checks, with
**Muhurat sessions preserved** (ten dates, correct data that looks anomalous).
(c) Sector/thematic index membership is **not PIT-tabled** — certify as unusable for
cross-sectional work until it is, rather than silently allowing survivorship in.

## 3. Gate C3 — Tradeability & synthetics

- **Assert `is_synthetic = FALSE`, never count bars.** A contiguity gate that counts one bar
  per slot passes on carry-forward data; ISD's did, over 16 certified sessions.
- **The synthetic predicate is `NSE_EQ`-only.** Indices carry volume 0 on every bar; resolve
  the index era by rule. (Verified already: zero `NSE_INDEX` rows are marked synthetic.)
- **C3 REMAINS BLOCKED (operator ruling).** The defect must be resolved by either (i) obtaining
  or fixing upstream Category-I coverage, or (ii) an **explicit operator-approved quarantine
  boundary**. **PTMS may not silently work around it.** Detail: The 10 post-CAS sessions 2026-08-31 → 2026-09-11
  carry zero equity synthetic marks — `cas_category.duckdb` ends 2026-08-28, and `mark_file()`
  returns 0 with no Category I list, so an unmarked session looks marked. Certification must
  **assert the Category I list is non-empty** before marking, and the marker must be re-run
  after any ingest touching post-CAS sessions.
- **Coverage is checked against the universe you need**, never against the file
  (`scripts/cas/fo_1m_coverage.py`).

## 4. Gate C4 — VIX certification (folded in per ruling)

**Status: DATA-AVAILABLE, CERTIFICATION-BLOCKED. No research window may be spent to certify it.**

| Item | Work |
|---|---|
| **V2** | Enumerate and quarantine the **88 defect sessions** (2022-03-24 → 2026-03-04; 83 in 2022) carrying 376–378 bars to 15:31/15:32. The broad >15:30 filter also catches **3 Muhurat** sessions — correct data, separated out, never quarantined. Preserve all 10 Muhurat and 2 NSE Saturday-special sessions |
| **Vendor 1m CSV** | 2,547 invalid-OHLC rows (`high < low`, or open/close outside `[low, high]`) across 28 sessions in 2018–2019: quarantine, enumerated. Truncated tail at 2025-03-05 11:30: drop the partial session. Sub-minute stamps on 46 sessions: floor to the minute. Provenance now stated (external vendor) — record it |
| **EOD CSV** | Run the **unrun** 2015 → 2025-06 overlap against the canonical 1d store before relying on the 2010–2015 prefix. Schema: DD-MM-YYYY, UTF-8 BOM, `Price` = close, `Vol.` empty, `Change %` derived |
| **Canonical 1m VIX** | Already 99.98% value-verified against the vendor CSV over 294,131 bars / 789 sessions. Promote that check from one-off to a standing gate, re-run as canonical coverage grows |
| **Ingest** | Committed, re-runnable script; vendor assets never written into `nse/candles/1m/{date}.duckdb`; copy-first baseline **before** any write to an existing store |

## 5. Cross-cutting requirements

1. **Certification certifies provenance.** Mutate a source-of-truth store only from
   committed, re-runnable code, and take the baseline copy *before* the write — provenance
   cannot be reconstructed afterwards.
2. **A gate over a time series needs an explicit contiguity check.** Completeness checks on
   the container are not checks on the contents: deleting rows from 59 files left all six
   Gate-A checks passing.
3. **Catch only the exception intended.** A bare `except: pass` around a fetch turns "we
   failed" to "the source doesn't have it"; a 404 is evidence of absence only for a date that
   has closed.
4. **Every certified claim carries its verification command and a timestamp.** The VIX count
   was corrected twice in one day because an ingest landed between readings.
5. Certification runs at **meta + substrate-verification level only**.

## 6. Sequence

```
C1  timestamp semantics (V1)          <- gate; blocks all intraday work
 |     C1-a operator supplies vendor spec   (no code)
 |     C1-b cross-source shift test          (substrate verification)
 |     C1-c event anchoring                  (substrate verification)
 v
C2  PIT & entity     ||   C3  tradeability/synthetics  ||   C4  VIX
 \___________________________|__________________________/
                             v
                L0 access layer + certification report
                             v
                   eligible surfaces & windows
                             v
        P3 catalogue -> P4 RFA (unblocked only at this point)
```

C1 is first because C2/C3/C4 all need to know what a timestamp means. C4 may run in parallel
once C1 fixes the clock.

## 7. Blocking dependencies on the operator

1. **C1-a**: the vendor's own specification for the reference 1m bundle — the cheapest
   possible resolution of V1, and the only arm that needs no inference.
2. **C3**: authority to fix or escalate **V3** (`cas_category` ends 2026-08-28). It is a live
   substrate defect outside PTMS scope but C3 cannot certify around it.
3. Confirmation that promoting the analog-path **AP-D4** era rule store-wide is acceptable —
   it is an existing frozen decision being generalized, not a new one.
