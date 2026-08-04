# TS Basis — Directional-Strength Filter Protocol: Design Review

**Date:** 2026-08-03
**Reviewer:** review pass — no code written, no data read, no window spent.
**Subject:** `docs/reports/TS_BASIS_FILTER_PROTOCOL.md` (DRAFT, commit `ab84ad1`).
**Verdict:** **NOT a confirm.** The three filters (G1 VIX regime, G2 OI confirmation, G3 expiry
skip) are explorable at **zero window cost** on already-burned surfaces. But **P4 (the SEALED
spend) must not be authorized on this protocol as written** — its window ledger is stale in two
places, and its intermediate gate does not exist for the daily arm. The mandatory free gate (RFA)
is also skipped, and the protocol is written in units the RFA cannot consume.

---

## 1. The blocker — the window ledger is stale in two places (one class of defect)

The protocol's safety architecture is "we only spend SEALED if HOLDOUT passes" (§3.2: P3 → P4).
That architecture is **illusory**, because two of the three window rows in §3.2 / §3.1 name
surfaces that are already spent.

**(a) Monthly arm has no confirmatory surface at all.** §3.1 evaluates "TS Basis Monthly" with
§3.2's `SEALED 2023-01-01 → 2026-07-24`. That window was **read on 2026-07-24** (monthly TS Basis
sealed read: IC +0.077, t=5.89, net +22.57%, then de-authorized). There is no unread monthly
sealed window. Half the protocol therefore has no P4 surface — it cannot be confirmed even in
principle.

**(b) Daily arm's HOLDOUT is already burned — so P3 tells you nothing, and P4 becomes a
near-unconditional spend.** CLAUDE.md, verbatim:

> "TS Basis Daily … TRAIN (1,202 formations) and HOLDOUT (495) are **both burned as SELECTION
> surfaces** — the `basis_reverting` filter was chosen on TRAIN and promoted on a HOLDOUT
> accept/reject check (`48f83bb`), TP@0.5% set on both (`4521b86`), an ML filter trained across
> all three (`80f5e86`)."

The reauthorization assessment §B.1 states it plainly: *"HOLDOUT was not a holdout for this
construct. It was a selection surface."* Yet §3.2 lists `HOLDOUT | 2019 → 2022 | Single confirm
read`. A window that has already accepted/rejected variants cannot serve as the single clean
confirm that authorizes a one-shot sealed spend. P3 passing carries almost no information, which
makes P4 an **effectively unconditional spend of the last preserved basis-family window** (the 876
daily formations the operator deliberately preserved).

*(A span-reconciliation note: the protocol's HOLDOUT is 2019→2022; the burned daily HOLDOUT is 495
formations. Whether these are the same span or the protocol is asserting a fresh one must be
resolved — but under either reading P3 is not a clean gate, because CLAUDE.md records the daily
HOLDOUT as burned.)*

**Both rows are the same class of error the reader must not miss: the protocol's window ledger
does not match the repo's recorded state.** This is exactly the failure that de-authorized the
monthly TS Basis (a read authorized on a gate that did not hold).

## 2. The mandatory free gate is skipped — and the protocol speaks the wrong units

A **filtered** TS Basis is a new construct. CLAUDE.md's RFA rule is unambiguous: *"Every new
research construct must clear it before any construct code is written."* §7 Deliverables jumps
straight to a measurement harness with no RFA. The RFA reads no data, costs one declaration file,
and has already killed FLOW and RS-MOM for $0 — it is the cheapest possible way to learn whether
this is demonstrable at all.

But the RFA **cannot consume this protocol as written.** §3.3/§3.4 evaluate in **direction
hit-rate** and **L/S-adjusted return**. The RFA contract accepts only `rank_ic` (δ/sd bands) or
`per_trade_pnl` (annualized Sharpe band + cadence). So before an RFA can even be drafted, the
construct must **pick a metric**, and the fork decides whether it is declarable:

- **`per_trade_pnl`** → faces `√T_sealed ≈ 1.89` head-on. RS-MOM died here needing Sharpe ≥ 1.30.
  A filtered top-5/side book is a small-name P&L series; check what Sharpe it would need before
  writing anything.
- **`rank_ic`** → needs δ/sd measured on the **filtered** book. Critically, δ must **not** be
  inherited from the sealed +0.077 — the C2 lesson, restated in the reauthorization assessment
  §A.5: the HOLDOUT +0.0412 is the planning number, not the sealed result that prompted the
  reconsideration.

This fork is the first decision, and it is free.

## 3. Breadth is the scarce resource — and G2 spends it

The demonstrability wall is sample-size × effect-size. For a `rank_ic` construct the relevant
"size" is per-formation IC dispersion (sd_IC).

- §3.1 fixes the daily subject as **top-5 per side = a 10-name cross-section**. G2's hard admission
  filter (`sign(OI_chg) == sign(basis z)`) removes names; §3.4's `coverage ≥ 60%` floor still
  permits cutting to **6 names**.
- The cost is **sd inflation, not n reduction**: formation count is unchanged, but fewer names per
  formation makes each per-formation IC noisier — directly raising sd_IC, directly lowering power.
  The daily construct was already at central power **0.7472** (reauthorization §B.3); cutting
  breadth pushes it further below 0.80, not toward it.
- §3.4 criterion 1 ("hit rate improves ≥4pp") is measured on the large TRAIN sample, so it is
  detectable *there* — but **TRAIN detectability is not confirmatory power**, and on the smaller
  confirmatory samples a 4pp bar sits near the noise floor. Hit-rate improvement on TRAIN does not
  map to clearing power 0.80 on the confirmatory window; only the RFA arithmetic answers that.

## 4. The operator decision this reverses (yours to make knowingly)

On **2026-08-01** the operator declared TS Basis Daily **research-only**: no promotion path, not
frozen, not gated, **876-formation sealed window preserved unspent**, and `run_sealed.py` guarded
to refuse to run. This protocol's P4 spends exactly that window. Running it **reverses the
2026-08-01 decision** — which the operator is entitled to do, but it is a knowing reversal, not a
fresh path. The `run_sealed.py` guard is a control, and the assessment already records that
deleting the guard is not itself authorization to spend the window.

## 5. Per-filter merit (the "are they good enough" question)

| Filter | Merit | The honest objection |
|---|---|---|
| **G1 VIX regime** `clip(vix_med/vix, 0.25, 2.0)` | Sound *mechanism* (carry = dispersion harvest; stress compresses dispersion). It is **bet-sizing, not prediction** — the protocol says so. Plausible as a **drawdown control**. | It is **undemonstrable as a return improvement** — its value is a bet on one VIX series, and its stress evidence is essentially **one event**: HOLDOUT 2019–2022 is COVID. In-repo precedent for the trap: the Nifty–BankNifty pair research found *54% of profit came from COVID 2020*. Judge G1 on drawdown, never on return. |
| **G2 OI confirmation** `sign(OI_chg)==sign(basis z)` | Cross-sectional (per-name), so it does **not** re-import the index timing wall. Plausible microstructure. | Spends breadth (see §3) — sd_IC inflation on an already-tight 10-name book. And OI-sign confirmation is itself an unproven feature = added multiplicity. |
| **G3 expiry skip** | Lowest risk. Legitimate contamination hygiene. | **Near-inert for monthly** (formations rarely land on expiry). F1 lesson applies: a filter selected into near-inactivity means the construct reduces to the thing it was meant to differ from. Fine to keep; will not move the needle. |
| **A3 / B3 (per-side asymmetry)** | — | **Contaminated.** Both are motivated by "the SHORT side is weaker," which comes from the 30-day read at protocol line 6. §6 discloses that read as *"pre-specification only… no filter choice depended on it"* — but A3 and B3 **are** filter choices that depend on it. This is the quiet-contamination class the diagnosis doc says lost TS Basis Daily. **Drop A3/B3, or disclose them as fitted.** |

## 6. Recommended path (all free, in order)

1. **Pick the metric** — `per_trade_pnl` or `rank_ic` (§2). This decides everything downstream.
2. **Run the RFA on the *filtered* construct** against an independently-defended effect-size band
   (δ from HOLDOUT-class reads, not sealed), with the reduced-breadth sd for the `rank_ic` case.
   If it ABANDONs — likely, given the breadth loss — the construct is dead for $0 and the sealed
   window is untouched.
3. **Only if RFA PROCEEDs:** correct §3.2's window ledger (monthly has no surface; daily HOLDOUT
   is burned), decide whether to reverse the 2026-08-01 research-only decision, drop or disclose
   A3/B3, and re-scope what "confirm" can mean when the only clean surface left is forward paper.

Filter selection on TRAIN/HOLDOUT as **hypothesis generation** is fine at any time — both are
already burned for this family, so nothing is lost. What must not happen is treating a
TRAIN/HOLDOUT hit-rate lift as authorization to spend the preserved sealed window.

---

**Bottom line.** Good mechanisms, careful intent, real defects. The protocol's promise — "sealed
window preserved, spent one-shot only if HOLDOUT passes" — does not hold: the monthly arm has no
sealed window, the daily HOLDOUT is already burned so P3 is not a real gate, and no RFA has been
run in units it can read. This is **explorable now at zero cost**; it is **not** a design to freeze
and take to a sealed read. Next step is the metric fork + a free RFA, not a harness.
