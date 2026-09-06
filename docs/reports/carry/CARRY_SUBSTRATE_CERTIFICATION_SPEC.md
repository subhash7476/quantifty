# Carry Substrate — Certification Spec (DRAFT)

**Status:** DRAFT. Design spec for the futures/spot substrate underpinning the Carry sleeve.
**Parent:** `CARRY_PHASE0_PRE_REGISTRATION.md` §2–§3 (universe, basis construction);
`SIGNAL_ENGINE_DESIGN.md` (engine).
**Purpose:** certify that the downloaded single-stock-futures + spot data is fit to compute a
basis, **before** a single rank-IC is read. Authorizes no signal code — only the contract
suite and its structural guards.

---

## 1. Why carry needs its own substrate gate

The basis is a **difference of two large legs**: `F − S`. A small misalignment between the
futures feed and the spot feed produces a **fabricated basis** — a large, wrong signal value
that is invisible to the rank-IC read downstream, exactly as the equity CA mis-keys
(DVL→DTIL, PHILIPCARB/PCBL) produced fabricated *returns* invisible to the PSB gap filter.
Carry is more exposed than any prior construct because it is the only one that joins **two
independent feeds per name per day** and subtracts them. The substrate must therefore
guarantee, per (name, date): both legs resolve to **one point-in-time entity**, both are
**corporate-action consistent**, the future maps to a **valid live contract**, and the
resulting basis is not a structural artifact.

This mirrors the PSB four-arm contract discipline (`scripts/psb1/contract_arms.py`) — zero
structural filters, entity grain, whole panel — adapted from one-leg adjusted returns to the
two-leg basis.

---

## 2. Falsifiable pre-run predictions

Stated before the certification runs (the research-script equivalent of a RED test):

1. On a clean substrate, the cross-sectional distribution of annualized `resid_carry` is
   **near-symmetric around zero** each day (the demean in §3.3 of the pre-reg forces this) and
   its tails are bounded by an economically plausible cap (§ Arm D). Systematic skew or
   fat one-sided tails on specific dates flags one-sided CA adjustment.
2. Basis does **not** jump discontinuously on futures **roll dates** (a jump ⇒ the roll leaked
   a price level, not a carry change).
3. Basis does **not** spike on **ex-dividend / ex-split dates** (a spike ⇒ one leg adjusted,
   the other did not).

If any prediction fails on the raw substrate, the defect is repaired (validate-then-apply,
copy-first) before certification passes — the numbers are not "explained away."

---

## 3. Certification arms

Each arm is a contract test over the **whole panel at entity grain**, no structural
pre-filtering. All four must return zero violations (or an explicitly dispositioned,
committed exception) for the substrate to certify.

### Arm A — Contract identity & roll integrity
- Every futures record resolves to a valid `(underlying_entity, expiry)` with a correctly
  computed `days_to_expiry` against the **actual NSE expiry calendar** (last-Thursday rule +
  holiday shifts + the 2024–25 expiry-day changes — verify against the dated calendar).
- No phantom/duplicate expiries; no record whose expiry is in the past relative to its trade
  date.
- The **near-month continuous series** (roll at T−3, per pre-reg §3.4) has **no gaps and no
  overlaps** at the roll seam: exactly one active near-month contract per (name, date).
- **Roll-continuity invariant:** at each roll date, the *level* discontinuity in the traded
  contract is expected (new contract), but the computed **basis** must be continuous within
  tolerance — Prediction 2.

### Arm B — Two-leg entity alignment (the recycled-ticker / re-ISIN threat)
- For each (name, date), the futures underlying and the spot series must resolve to the **same
  point-in-time entity** via `symbol_entity_intervals` + ISIN issuer-prefix linkage (reuse
  the CSMP entity machinery, `scripts/csmp/build_universe.py`).
- Guard the three known equity failure modes, now across two feeds:
  - **Recycled ticker** — a vacated symbol reassigned to a new company (DTIL→tea): time-aware
    resolution, union-find alone insufficient.
  - **Re-ISIN on face-value change** — issuer-prefix linkage, not full-ISIN match.
  - **Symbol rename** — futures feed and spot feed may adopt a rename on different dates; the
    basis must be **suppressed** on any date where the two feeds disagree on entity identity,
    not silently computed.

### Arm C — Corporate-action consistency across legs
- Splits/bonuses: on ex-date the future and spot both reprice; certify the **ratio** is
  applied to both legs on the **same date**. A one-sided adjustment is the primary fabricated-
  basis source — Prediction 3.
- Dividends: per pre-reg §3.2, only **announced/ex-date-known** dividends adjust the basis, and
  **no lookahead** — the dividend used at formation *t* must have been public at *t*. Certify
  the dividend join is PIT (announcement date ≤ formation date).
- Special CAs (demerger, scheme, symbol change with contract reconstitution): dispositioned in
  a committed register (mirror `scripts/psb1/disposition_register.py`), not hand-patched.

### Arm D — Basis fabrication invariant
- Compute the annualized `raw_basis` panel; flag any |annualized basis| beyond an
  **economically defensible bound** (pre-set, e.g. ±X% — hard-to-borrow names legitimately run
  rich, so the bound is generous but finite). Every flagged cell is either (a) traced to a real
  illiquidity/borrow event (kept, tagged) or (b) traced to a data defect and repaired. No
  flagged cell is dropped by a blanket filter — that is the exact blind spot that hid the
  equity mis-keys.
- **Staleness/timestamp:** `F` and `S` for a (name, date) must come from the **same trading
  session close**; no stale carry-forward of one leg against a fresh other leg. Certify no
  cell mixes sessions.

---

## 4. PIT universe

- F&O-eligibility membership is **point-in-time**: a name enters the eligible panel on its
  actual SEBI/NSE F&O-inclusion date and exits on exclusion. Certify no name contributes a
  basis on a date it was not F&O-listed (survivorship + look-ahead guard).
- Liquidity/ADV screen (pre-reg §2) applied **after** certification, at formation time — it is
  a construction choice, not a substrate filter, so it does not mask defects.

---

## 5. Deliverable & discipline

- **Runner:** `scripts/signal_engine/carry/certify_substrate.py` — the four-arm suite + PIT
  guard, whole-panel, entity grain, zero structural filters.
- **Contract library:** `scripts/signal_engine/carry/contract_arms.py` (Arm A–D tests).
- **Disposition register:** committed, for the special-CA exceptions.
- **Report:** `docs/reports/CARRY_SUBSTRATE_CERTIFICATION.md` — script-generated, no
  hand-edited numbers; states each arm's violation count and the continuity invariants.
- **Discipline:** copy-first (never mutate the raw store), validate-then-apply for any repair,
  each repair its own committed runner (mirror `scripts/psb1/repair_*.py`).
- **Gate:** the Carry TRAIN read (pre-reg §9 gate 2) **may not run** until this report shows
  zero un-dispositioned violations and all three §2 predictions hold.

---

## 6. What this spec deliberately does NOT do

- No roll-adjusted *return* series (carry is a level signal; the continuous series exists only
  to pick the near-month contract and enforce roll continuity). Return-based roll adjustment is
  a Trend-sleeve concern, specified separately.
- No signal computation, neutralization, or fee logic — those live in the pre-reg, downstream
  of a certified substrate.
- No new abstraction layer beyond the reused CSMP entity machinery — per `CLAUDE.md`, no
  speculative generality; the equity entity resolver is adopted, not re-built.
