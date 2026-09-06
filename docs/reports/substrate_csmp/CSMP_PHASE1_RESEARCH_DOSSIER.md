# CSMP Phase 1 — Research Dossier (Pre-Registration)

**Hypothesis:** Cross-Sectional Relative Strength — `xs_momentum_score` (classic 12-1 momentum over the point-in-time NIFTY-200 universe)

**Document type:** Research baseline / pre-registration (Phase 1 of the Cross-Sectional Momentum Program). This document *pre-registers*; it does not report a result computed on the sealed window.

**Status:** **FROZEN — immutable Phase-1 pre-registration (Rev 7, 2026-07-12).** Passed the independent Phase-2 model review (`CSMP_PHASE2_INDEPENDENT_REVIEW.md`, GPT-5/Codex — **PASS WITH REQUIRED REVISIONS**) with all three findings folded in (`CSMP_PHASE2_LEAD_DISPOSITION.md`; operator-ratified): **F2** — the CI-coverage script now reuses the §5.2 forward-return convention (`phase1_ci_coverage.py`); **F1** — D-i's selection rule is disambiguated to *one-sided Type-I closest to nominal* and applied mechanically (it still selects Student-t; the §5.2 correction did not flip it); **F3** — the post-Inconclusive PaperBroker path is recorded as an explicit charter §6 amendment with four controls, not "satisfaction by disclosure." The three §3.4 inference decisions are operator-ratified: D-i = one-sided Student-t (one-sided-calibration rule); D-ii = one-sided; D-iii = single-shot. **Do not modify.** Any change to the universe, score, K=40, metric, baselines, cost model, §5.2 delisting convention, or inference/extension design now requires a **new pre-registration for a new increment**, not an edit. Phase 6 is the single sealed read (2023-01 → 2026-06), subject to the §8 A1 VOID precondition; the window has not been read.

**Date:** 2026-07-11 (Rev 5 content) · 2026-07-12 (Rev 6 ratification, Rev 7 freeze)

**Revision provenance:**
- **Rev 1** — initial DRAFT.
- **Rev 2** — reconciled Lead Review (`CSMP_PHASE1_DOSSIER_LEAD_REVIEW.md`): B1 §5.2 re-run, B2 power, B3 slippage 2× fix, S1–S9, A1–A3, R1–R4 (`phase1_prereg_analysis.py`).
- **Rev 3** — D-i/D-ii (`CSMP_PHASE1_OPERATOR_DECISIONS.md`): L=12 percentile CI invalid at n=42 (`phase1_ci_coverage.py`); replaced by one-sided Student-t via the coverage rule.
- **Rev 4** — D-iii, first pass: the "re-read until it clears" schedule had family-wise Type-I 0.130 (the removed bug's level); replaced with a pinned group-sequential α-spending design (`phase1_group_sequential.py`).
- **Rev 5** — D-iii resolved: the boundary math **reversed the recommendation to single-shot.** A post-2026 decay scenario shows Pocock's 0.73 terminal power is contingent (falls to 0.34 under decay, below single-shot's decay-invariant 0.41), while it halves the primary read; the charter's crowding/decay threat decides it. §10 row 3 rebuilt as spend-once + exploratory PAPER consumer + new-data re-registration.
- **Rev 6** — operator ratification applied (`CSMP_PHASE1_FREEZE_RATIFICATION.md`, 2026-07-12); author-locked; no analytical change from Rev 5.
- **Rev 7 (this) — FROZEN.** Phase-2 findings folded (F1/F2/F3 + the §3.4 record correction). **F2** shifted the dev IC population 0.0458 → **0.0457** (negligible, as predicted) and the D-i coverage table by ≤0.002; **the selected gate did not flip** — Student-t remains closest on one-sided Type-I (0.049, distance 0.001), so the freeze proceeded. The earlier inaccurate D-i integrity line is corrected in §3.4 (Student-t named as the lowest-power valid candidate; the `iid_perc` foil and the one-sided/two-sided ambiguity disclosed). Sources add the Phase-2 review and disposition. No sealed-window read.

**Predecessors & prior art:**
- `docs/reports/CSMP_PHASE0_CHARTER.md` — Phase 0 CLOSED; the five §8 (D1–D5) decisions this dossier operationalizes.
- Gates (a)–(e), all PASSED. Gate (e) returned **CONTINUE** on the dev window; **that CONTINUE has been re-confirmed under the frozen §5.2 convention (B1, §2.1)**, closing the one gap the gate-(e) review missed.
- `docs/reports/MSRP_PHASE1_RESEARCH_DOSSIER.md` — the pre-registration template and the **D1 transmission lesson** (a forecast can rank well and still not transmit to P&L). CSMP's construct makes the forecast (a ranking) and the trade (holding the top of it) the same object; gate (e) was the pre-committed transmission check MSRP's D1 lacked. *(This lesson is stated once here and invoked, not repeated, below.)*

---

## 1. Pre-Registration Statement

This dossier is committed **before** the sealed held-out window is scored. The universe, score, holding rule, metric, baselines, cost model, delisting convention, and decision table are fixed here from the **charter (locked) and the dev window only** — never from the held-out window.

- **Development window (every construct/threshold decision — already spent):** `2012-01 → 2022-12`. Every choice traces to the charter's D1–D5 or to the gate-(e) / §2.1 dev-window computation.
- **Held-out window (evaluation only — SEALED):** `2023-01 → 2026-06`. No parameter may be chosen, tuned, or inspected against it. Touched exactly once, at Phase 6, subject to the §8 VOID precondition. Gate (e) and the §2.1 re-run both read nothing past `2022-12-30` (asserted and printed).

### 1.1 Reproducibility substrate — pinned now (nothing left to choose but build-time hashes)

| Field | Value |
|---|---|
| **Inference — CI method (D-i, §3.4)** | **one-sided 95% Student-t lower bound on the monthly `IC_t` series** — selected by the ratified **one-sided-calibration** rule (§3.4; disambiguated per Phase-2 F1): one-sided null rejection closest to nominal 0.050 → Student-t at **0.049** (distance 0.001). Reported **non-gating** arms: `iid_perc` (0.053; the two-sided-coverage-reading winner) and the retired invalid `mb_L12` (0.129). Guardrail: select on calibration, NOT narrowness. **RATIFIED 2026-07-12.** |
| Bootstrap replicate count `B` (robustness arm only) | **20,000** |
| Bootstrap RNG seed | **20260711** (fixed integer — not "e.g.") |
| Slippage `κ` | **5 bps per traded side** (§8) |
| Holding size `K` | **40** (top quintile of 200; §3.2, §S8) |
| Capital (disclosed; costs are near capital-independent) | **Rs 1,00,00,000** |
| Sealed rebalance grid | **the last full session (`n_symbols ≥ 200`) of each month, 2022-12 → 2026-05 inclusive → 42 formation-months** (§3.4 / S5: the 2022-12 formation's forward return lands in 2023-01, the first legitimate out-of-sample observation, computed from dev-window formation prices — **included**). **PINNED at A2 build (Prompt 8, calendar-fact query, no prices read): count = 42 (verified == target), 2022-12-30 → 2026-05-29.** Full list: 2022-12-30, 2023-01-31, 02-28, 03-31, 04-28, 05-31, 06-30, 07-31, 08-31, 09-29, 10-31, 11-30, 12-29, 2024-01-31, 02-29, 03-28, 04-30, 05-31, 06-28, 07-31, 08-30, 09-30, 10-31, 11-29, 12-31, 2025-01-31, 02-28, 03-28, 04-30, 05-30, 06-30, 07-31, 08-29, 09-30, 10-31, 11-28, 12-31, 2026-01-30, 02-27, 03-30, 04-30, 05-29. The count is VOID-checked, never a tuning lever. |
| **Extension design (D-iii, §3.4)** | **single-shot — RATIFIED 2026-07-12.** The sealed window is scored once (#42) at full one-sided α = 0.05, ~0.41 power, and never re-read; the Inconclusive path runs the PAPER consumer exploratorily and feeds new forward data to a fresh pre-registration (§10 row 3). *(§1.1 holds only what Phase 6 builds against; the declined group-sequential alternative is recorded in §3.4.)* |
| Build-time substrate — **PINNED at A2 build (Prompt 8; corrected Prompt 9; re-pinned Prompts 11–13, 2026-07-12)** | store SHA-256 **`e51363ea9681fda72120964b483b70daed34ea64e395bd098fc5cb3a6aad5e72`**; **code commit `0ae1dc4b36df1b10b794925606abfe363aa7d7d5`** — the commit that *contains* the harness (Prompt-13 restricted `load_window()` to ever-member entities to fix a sealed-cutoff `MemoryError`; the identity legitimately changed because content changed). Dev **`validation_id` `f8153e1147246655bc451b027053b79af14d3afbe822adff8ab61ac144ef0bf1`** (Prompt-10 Step-0 tripwire). The A2 record identity is **content-addressed** by git-normalized source hashes (HEAD-independent, CRLF/LF-immune): `model.py` `db06ceffd9e4fded…`, `validation.py` `ee89aa3bee6c094d…`, `void_precondition.py` `54305a0f42340091…`, `run_a2_validation.py` `bc7a69f4dc5cb304…`, `phase1_prereg_analysis.py` `bf9879fb7b3a3bd1…`. Library versions (Python 3.13.5 / duckdb 1.4.3 / numpy 2.4.4 / scipy 1.17.0 / pandas 2.3.3) are recorded provenance, **not** part of the identity. `results.json` is byte-identical (`be662698…`) across the Prompt-9/11/12/13 re-pins — the guard/reporting/loading fixes moved no number. Full values in the A2 record `docs/reports/csmp_a2_records/`. |

---

## 2. Objectives

### 2.1 Scientific Claim — an explicit conjunction (B4)

> **(i) Over the point-in-time NIFTY-200 universe, classic 12-1 cross-sectional momentum ranks next-month relative returns with positive out-of-sample skill (2023-01 → 2026-06); AND (ii) the top-40 equal-weight book beats the stronger equal-weight-universe baseline net of realistic delivery costs.**

The two halves are adjudicated separately (§3.4): **(i) is the artifact gate** (the rank-IC test — charter D3); **(ii) is the deployment qualifier** (`Δ_net`). An Approved artifact whose `Δ_net ≤ 0` substantiates **(i) only** — "the ranking has skill but does not transmit net of cost" — and is **not deployed** (§10 row 2, the D1 outcome). The full §2.1 claim holds only when both halves clear.

**Dev-window evidence under the frozen §5.2 convention (B1 — re-run, dev-only, reproducible).** Gate (e)'s CONTINUE was computed on a panel that silently dropped delisting names (the §5.2 bug). Re-running with §5.2 applied and gating on the **stronger** baseline (S1):

| Quantity (dev 2012–2022, §5.2) | Value | Gate-(e) as-reported |
|---|---|---|
| Mean monthly rank IC | **0.0457** | 0.0458 |
| Block-bootstrap 95% CI (L=12) | **[0.0091, 0.0811]** | [0.0093, 0.0812] |
| Delisting names re-included (rule-1 / rule-2) | **21 / 1** over 131 months | (dropped) |
| Net top-40 minus formation-complete universe (fees) | **+6.24%/yr** | +6.38% (weaker baseline) |
| …net of fees **+ 5 bps/side slippage** | **+5.95%/yr** | — |
| Gate-(e) stop rule (IC>0.02 ∧ CI_lo>0 ∧ spread>0) | **CONTINUE** | CONTINUE |

CONTINUE survives §5.2, the −100% rule-2 stress (§5.2), and the stronger-baseline choice. **§2.1 now cites numbers this document endorses.** The sealed window tests whether this dev edge **generalizes** — the crowding/decay defense.

### 2.2 Engineering Deliverable

1. A `PublishedArtifact v2` (MSI-007) emitting, per universe symbol, `xs_momentum_score` (`dimension = <symbol>`) with a pinned scalar `uncertainty` (§7), per the MM13 §4 N-estimate contract.
2. The minimal MSI-006 **A2 harness** — one immutable validation record, seven domains, adapted to the cross-sectional metric.
3. (Phase 7) A top-`K` equal-weight monthly `SignalSource`, `GuardedSignalSource`-wrapped, **PaperBroker only**.

Building the artifact is not evidence the claim is true.

---

## 3. Hypotheses and Decision Rule (pre-registered)

### 3.1 Common target

At each monthly rebalance `t` (last full session of the month), `U_t` = the gate-(c) point-in-time NIFTY-200 members (`method = turnover_top200`, entity-continuous). Forward return `t → t+1` on the gate-(b) CA-adjusted close, entity-resolved. **Delisting convention §5.2 is binding** on every forward return in both the IC set and both portfolios: a name that stops trading is never dropped; it bears its realized return to its last available close. (This is the fix whose dev-window effect is quantified in §2.1: 22 member-months re-included, verdict unchanged.)

### 3.2 One candidate, two nested baselines, no reference arm

- **Candidate** `s^{mom}_{i,t} = adj_close_i(t−1m)/adj_close_i(t−12m) − 1` (classic 12-1, 1-month skip). A name lacking a complete formation window is **not scored** (cannot enter the top-40); the excluded count is reported (dev: 382/131 months).
- **Gating baseline — the stronger of two, pre-registered now (S1).** Both the **formation-complete** equal-weight universe (dev net 9.20%) and the **true all-200** equal-weight universe (dev net 9.11%, the charter "just buy everything") are computed; the gate uses the **higher-returning (harder) of the two on the sealed window.** *This removes the appearance of picking the easier bar — the Rev-1 "switch to all-200 is conservative" framing was backwards (all-200 is the weaker bar); gating on the stronger is unimpeachable.*
- **Reference arm — REMOVED (R1, resolved now).** The NIFTY200 Momentum 30 TRI is **not obtainable** by a deterministic fetch: `niftyindices.com/IndexConstituent/ind_nifty200Momentum30_Data.csv` and the `getTotalReturnIndexString` endpoint both return **HTTP 200 with `Content-Type: text/html` (`<!DOCTYPE html>`, 77,356 bytes)** — a wrong-content shell, not a TRI series (the gate-(a) G4 failure mode). It is non-gating and carrying an unresolved public-data probe into the single sealed run is pure liability, so the arm is **dropped from the dossier**. (An operator may re-add it later as its own reported series; it never gates.)

**Holding rule — FROZEN at K = 40** (charter D2 delegated "top-quintile ≈ 40 vs top-30" here). Equal-weight, monthly, long-only (D4). Bottom quintile reported (long-short spread), not traded. **No selection occurred (S8):** gate (e) computed only the quintile (40) net portfolio and the quintile/decile *gross* spreads — no top-30 book was ever computed, so K could not have been tuned; and the dev **decile** gross spread (1.22%/mo) *exceeded* the quintile's (1.07%/mo), so K=40 is demonstrably **not** the dev-maximizing choice. K=40 is chosen for diversification and charter-quintile continuity, not performance.

### 3.3 H₀ / H₁

Over the sealed window: `IC_t` = monthly cross-sectional Spearman rank correlation of `s^{mom}` vs the §5.2 forward return; `mean_IC` = its mean; `Δ_net` = annualized net-of-fee-and-slippage top-40 return minus the stronger-baseline return.

- **H₀:** `mean_IC ≤ 0` — no rank skill. *(Artifact gate.)*
- **H₁ (directional):** `mean_IC > 0`, tested by the **one-sided 95% lower bound** (§3.4 D-i/D-ii) excluding 0. Deployment additionally requires `Δ_net > 0`.

### 3.4 Inference decisions, then the power reality (B2, S2)

**Artifact Approved** iff the one-sided 95% lower bound of `mean_IC` exceeds 0. **Deployable** iff additionally `Δ_net > 0`. Read mechanically; no post-hoc widening.

The two inference choices are **not independent, and not equal weight** (`CSMP_PHASE1_OPERATOR_DECISIONS.md`). **D-i (the CI method) is a *validity* question and is settled first; D-ii (one-sided vs two-sided) is a *power* question, meaningful only once the test is valid.** Deciding the tail on top of an invalid interval would stack a liberal test on a liberal tail.

**D-i — CI method (validity). The pre-registered L=12 moving-block percentile CI is invalid at n=42 and is replaced.** A coverage simulation (dev-only; `scripts/csmp/phase1_ci_coverage.py`; population = the empirical 131-month dev IC distribution built under the §5.2 forward-return convention — Phase-2 **F2**, reusing `phase1_prereg_analysis.fwd()`; iid resampling justified by that series' near-zero serial dependence — the block-L12 CI is only 1.011× the iid CI at n=131) gives, at n=42:

| CI method | 2-sided coverage (sanity only) | 1-sided Type-I (**selection metric**) | 1-sided power @ dev IC |
|---|---:|---:|---:|
| **Student-t (selected gate)** | 0.957 | **0.049** | 0.397 |
| iid percentile bootstrap (reported, non-gating) | 0.949 | 0.053 | 0.416 |
| stationary bootstrap (mean-block 3) | 0.924 | 0.065 | 0.452 |
| **moving-block L=12 percentile (retired — invalid)** | **0.809** | **0.129** | 0.539 |
| *nominal* | *0.950* | *0.050* | *—* |

The incumbent covers at **81%, not 95%** — a one-sided Type-I of **~13%** (≈ 2.6× nominal); its apparent power (0.539) is **borrowed from that invalidity**. **Selection rule (ratified 2026-07-12, disambiguated per Phase-2 F1): because the primary gate is a one-sided lower bound, select the CI method whose one-sided null rejection rate at n=42 is closest to nominal 0.050; two-sided coverage is reported as a sanity check, not used to select. Guardrail, unchanged: select on calibration, NOT on narrowness.** Applied mechanically by `phase1_ci_coverage.py` (which prints the selected method and its distance), the rule selects the **one-sided 95% Student-t lower bound** (one-sided Type-I 0.049, distance 0.001 from 0.050). The **non-selected candidates are pre-registered as reported, non-gating arms** at Phase 6: `iid_perc` (0.053 — the winner under a literal *two-sided-coverage* reading, distance 0.001 from 0.950) and the retired `mb_L12` (invalid). Both readings stay visible in this frozen document so neither can be silently preferred after the sealed result is seen.

**On why Student-t and not power (record-corrected per Phase-2 F1 / disposition §3).** Student-t is the **lowest-power valid candidate** (0.397, vs `iid_perc` 0.416 and stationary 0.452) — chosen on **one-sided calibration for a one-sided gate, not for power**. The rule as first written ("coverage closest to nominal") was **underspecified** between the one-sided and two-sided readings (Phase-2 **F1**); under a literal two-sided reading it selects `iid_perc`. It was **disambiguated to one-sided pre-seal, applied to a corrected table (the §5.2 forward-return fix, Phase-2 F2), and disclosed** — not resolved after the fact. Student-t errs conservative (0.049 < 0.050) while `iid_perc` errs liberal (0.053 > 0.050); selecting the conservative candidate is coherent with the very reason the D-i episode existed — removing an anti-conservative test.

**D-ii — one-sided (power).** H₁ is directional; nobody deploys on a significantly negative IC, so a two-sided test spends half its α guarding an outcome with no decision attached. A one-sided 95% lower bound satisfies charter D3's "95% CI excluding zero" on a plain reading. The **operator ratified this reading on 2026-07-12, before the seal** — legitimate precisely because H₁'s direction (`mean_IC > 0`) was committed in §3.3 from Rev 1, before any sealed read. It buys ~11 points of power at a correctly-calibrated 5% Type-I.

**The power reality (B2) — the single most important disclosure in this document.** At the sealed `n ≈ 42` and the dev IC SD `0.208`, `SE(mean_IC) = 0.208/√42 = 0.032`, so the one-sided gate needs a sealed mean IC of **~0.053** (the two-sided version needed ~0.063 — *above* the 0.0458 the dev window produced). Honest power (on the corrected, calibrated test):

| Assumed true sealed IC | Two-sided power | One-sided power (the gate) |
|---|---:|---:|
| 0.02 | 9% | 15% |
| 0.0458 (= dev) | 30% | **~40%** |
| 0.064 | 51% | 64% |
| 0.08 | 70% | 80% |

Months for 50% power at the dev IC: 80 (two-sided) / **56 (one-sided)**; for 80%: 163 / 128. **Even on the best *valid* test available on 42 months — one-sided, correctly covered — "Inconclusive" remains the modal outcome (~60%) if the true edge equals the dev edge.** 40% is not a good test; it is the honest ceiling at this sample size, and the alternative (the incumbent's higher apparent power) is a false-positive rate wearing power's clothes. §11 states this in plain words. **D-i and D-ii are operator-ratified (2026-07-12, `CSMP_PHASE1_FREEZE_RATIFICATION.md`)** — the Phase-2 reviewer may nonetheless reopen either; the evidence above is exactly what they are meant to attack.

**D-iii — the extension path is a multiplicity problem, and must be a controlled group-sequential design (not "re-read until it clears").** Rev 3's §10 extension rule ("re-read at #56, annually to #128, *or the gate clears*") is a stop-on-success schedule of ~8 looks on nested accumulating data; simulated (dev-only, `scripts/csmp/phase1_group_sequential.py`) its **family-wise one-sided Type-I is 0.130 — identical to the mb_L12 bug (0.129) D-i just removed.** Disclosure does not control it; a formalized "keep looking until significant" is *more* dangerous than an informal one because it looks rigorous. The honest options over the pre-specified 8-look calendar (looks at cumulative months #42, #56, #68, …, #128; information fractions 0.33 → 1.0), each holding overall one-sided α = 0.05:

| Design | #42 (Phase-6) power | #128 (2033) power | Extensions Approval-bearing? |
|---|---:|---:|---|
| **Single-shot primary at #42 (RATIFIED)** | **0.41** | — | No — extensions feed a *new* pre-registration with fresh α (see §10) |
| Group-sequential, **Pocock** spend (constant boundary Z ≈ 2.13) | 0.24 | 0.73 | Yes |
| Group-sequential, **O'Brien–Fleming** spend (Z 3.15 → 1.80) | 0.04 | 0.78 | Yes |

The boundary math **reversed the earlier "take the group-sequential" recommendation, and the operator ratified single-shot (D-iii, 2026-07-12).** OBF is disqualified outright — its first look at t=0.33 spends almost nothing, collapsing #42 power from 41% to **4%** (the primary read becomes decorative). The **Pocock group-sequential alternative is declined** (retained here for the record, not pinned in §1.1), because Pocock's headline **0.73 is not 73% — it is 0.73 × P(the edge still exists at dev strength in 2033).** Simulating an edge that is alive across the sealed window and then decays afterward (the charter's central thesis; the NIFTY200 M30 ETF went live in 2020, *before* the sealed window opens):

| post-2026 edge | single-shot #42 power | Pocock #128 power |
|---|---:|---:|
| persists at dev strength | 0.41 | 0.73 |
| decays to half | 0.41 | 0.50 |
| **dead after 2026** | **0.41** | **0.34** |

**Single-shot's 0.41 is invariant to post-2026 decay — it conditions only on 2023–2026, data that already exists. Pocock's terminal power is entirely contingent on a good case the program's own primary risk says is doubtful, and under decay it falls *below* single-shot while having already halved the primary read to 0.24.** You cannot bank power obtained by assuming away crowding/decay. Stripped of machinery, D-iii collapsed to one non-statistical question — *do we believe this edge survives to 2033? Yes → Pocock; No or unknown → single-shot* — and the charter answers it (crowding/decay is the named central threat); **the operator ratified single-shot.** The "no Approval-bearing extension" bind is resolved not by re-reading old data but by accumulating genuinely new forward months (§10 row 3). *(The Phase-2 reviewer may reopen D-iii like any other decision; the decay evidence above is what they would test.)*

---

## 4. Latent Variable and Economic Rationale

**Latent variable:** `xs_momentum_score` — one named `Estimate` per symbol (`value` = 12-1 score; `uncertainty` per §7; `dimension = symbol`) in the multidimensional `MarketState` (MSI-OD-001).

**Structurally-motivated predictor (not a causal claim).** Intermediate-horizon relative-strength persistence is among the most replicated anomalies (Jegadeesh–Titman 1993; Asness–Moskowitz–Pedersen 2013; NSE's live NIFTY200 Momentum 30). The 1-month skip removes short-term reversal. The mechanism motivates out-of-sample generalization; it is not manipulationist.

**Why the equal-weight universe is the bar.** A naive investor gets it free. If the top-40 cannot beat the *stronger* of the two universe baselines net of gate-(d) fees and 5 bps/side slippage, the ranking adds no decision value and §2.1(ii) is false regardless of a positive IC.

---

## 5. Labels / Target Definition

### 5.1 Score and forward return
- **Score:** `adj_close(t−1m)/adj_close(t−12m) − 1` (CA-adjusted, entity-continuous).
- **Forward return:** `adj_close(t+1)/adj_close(t) − 1`, subject to §5.2.

### 5.2 Delisting / suspension convention (pre-registered, binding)

For a name `i` priced at `t`:
1. **Rule 1 — trades again in `(t, t+1]`:** forward return uses its **last available adjusted close** in that interval (a realized, possibly large-negative return); position **liquidated at that price**, capital to cash, redeployed next rebalance.
2. **Rule 2 — no session in `(t, t+1]`:** **liquidated at its own entry close `t` → a 0% step** (DeepSeek F1 wording: "liquidated at the entry close"; 0% = no gain, no loss). This is the pre-registered gate value. **Because 0% is generous in exactly momentum's left tail** (the realistic generator is a suspension ahead of a bankruptcy delisting, whose true value is nearer −100%), a **non-gating −100% sensitivity is also reported** (S7).
3. **A name is never dropped** from the IC set or a portfolio for a missing `t+1` price.

**Dev-window incidence (§2.1 re-run):** 21 rule-1 and **1** rule-2 member-months over 131 months; the −100% stress moves the verdict not at all (spread 6.24% → 6.28% fees-only; CI and IC unchanged to 4 dp). **Required Phase-6 disclosure:** the rule-1/rule-2 counts by year, and — because any rule-2 name in the top-40 could mask a real loss — an explicit highlight of every top-40 rule-2 event.

---

## 6. Feature Library

Single-feature by design (charter §7 fence: momentum only).

| Feature | Definition (as of `t`) | Source | Leak check |
|---|---|---|---|
| `s^{mom}` (12-1) | `adj_close(t−1m)/adj_close(t−12m) − 1` | gate-(b) adjusted view | uses only prices ≤ `t−1m` |

**Rejected (will not be silently added after a weak sealed result):** 6-1/3-1 or weekly cadence (each its own increment-2 pre-registration); volatility-scaled momentum; volume/turnover/delivery overlays (turnover feeds *membership* only, never the signal); Block-H intermarket features.

---

## 7. Model / Artifact

**Parameter-free construct.** The score is a deterministic transform of adjusted prices — nothing is fitted, so there are no coefficients and no estimation error. What is frozen is the *specification* (12-1, skip-1, entity continuity, `turnover_top200` universe, K=40, EW, monthly). `evaluate()` reads member prices and emits one score per name; identical evidence ⇒ identical `MarketState`.

**Uncertainty — fully specified (S4/R4).** The MSI `Estimate` carries **one** scalar: `uncertainty = SD of the 11 monthly formation sub-returns` (a name whose 12-1 total is a few violent months is a less reliable momentum estimate than one built from steady accrual). Formation-window **completeness** is carried as **separate metadata, not folded into the scalar.** Increment 1 **consumes ranks only** — `uncertainty` does **not** enter ranking, K-selection, or weighting (charter §4's permitted "reported-not-acted-on" path). Its **calibration test (runnable, non-gating, S4):** at each dev `t`, sort names into uncertainty terciles and compute `mean_IC` within each; a calibrated uncertainty implies monotonically higher IC in the low-uncertainty tercile. Measured on dev, reported once on held-out, never tuned. Acting on uncertainty (abstention/weighting) is an explicit **increment-2** hypothesis.

---

## 8. Methodology

**Data.** gate-(b) adjusted close; gate-(c) `universe_membership`; gate-(a) `symbol_changes`; gate-(d) `delivery_equity_fees`.

**Split.** Dev 2012-01 → 2022-12 (spent). Held-out 2023-01 → 2026-06 (scored once, Phase 6, subject to the VOID precondition below). Grid and count pinned per §1.1 (target 42).

**Protocol.** At each sealed `t`: score formation-complete members; rank; compute §5.2 forward returns; form `IC_t`, the top-40 and both universe portfolios, and the (reported-only) long-short spread.

**Costs — pre-registered, applied identically to all arms.**
1. **Fees:** gate-(d) `delivery_equity_fees` on every buy/sell leg of rebalance turnover; first rebalance buys the whole book; terminal book marked, not liquidated.
2. **Slippage `κ = 5 bps` per traded side.** **Turnover is defined unambiguously as *traded notional as a fraction of capital, per month*** — **twice** the gate-(e) `two_way` metric, which is `(enters+exits)/(2N)` and reports *half* the traded notional (B3). At the dev top-40 turnover, traded notional is **47.5%/month**, not 23.76% (cross-check: STT 0.1%/side × 47.5% = 4.75 bp/mo, matching gate (e)'s reported 5.22 bp/mo fee drag; the half-reading gives 2.6 bp/mo, contradicting it). **Correct slippage impact: top-40 ≈ 29–33 bp/yr, universe ≈ 4 bp/yr, differential ≈ 29 bp/yr — not the ~12 bp/yr Rev 1 stated.** Immaterial against the 624 bp dev spread; **material against a sealed `Δ_net` that may be a bare +30 bp** — which is exactly why the cost model must be arithmetically correct.
3. Equal-weight drift of continuing holdings not re-traded (symmetric across arms).

**Inference.** `mean_IC` CI via the ratified one-sided Student-t interval (§3.4 D-i), with the moving-block bootstrap (L=12, B=20000, seed 20260711) retained as a reported robustness arm, because the raw L=12 percentile CI under-covers at n=42. **A2 (added): `Δ_net` is reported with its own block-bootstrap CI and is pre-registered as non-gating** — a bare 42-month point estimate is close to a coin flip and must not be retrofitted as a gate.

**A1 — sealed-run data-integrity VOID precondition (the biggest safeguard, added).** Step 0 of the Phase-6 run re-executes gate (b)'s `|move| ≥ 20%` single-day CA-classification screen over 2023-01 → 2026-06. **If unexplained residue > 0, the run is VOID** — no metric is read, the window is re-sealed pending a gate-(b) fix. A single wrong split factor on one name manufactures ±50% phantom momentum and a 1.25% top-40 move, and can inject that name into the top quintile; §12.1 names this as the scariest inherited assumption, and this precondition acts on it. The residue count is a data-quality fact, not a result, so the seal is preserved.

**Point-in-time discipline.** Scores use prices ≤ `t−1m`; membership is gate-(c) PIT; every query fenced and the boundary printed.

---

## 9. Validation Plan → Minimal MSI-006 (seven domains)

| Domain | Method pre-committed |
|---|---|
| **Architectural** | MSI-007 shape; one `xs_momentum_score` per member, scalar `uncertainty` (§7), `dimension = symbol`. |
| **Scientific** | §3.4 `mean_IC` gate (one-sided Student-t lower bound, D-i) and `Δ_net` qualifier; §10 table. |
| **Temporal** | PIT/no-leak audit; **A1 VOID precondition**; fence asserted and printed. |
| **Robustness** | `mean_IC` one-sided 95% **Student-t** lower bound (the gate) **plus the L=12 moving-block CI reported as a robustness arm** (§3.4 D-i); by-year IC/hit-rate; §5.2 rule-1/rule-2 counts + the −100% sensitivity; one sub-period split (2023-24 vs 2025-26), reported. **Risk metrics both arms (S6/A2), non-gating:** annualized vol, Sharpe, max drawdown, with dev values for context — dev shows the top-40 book at **vol 21.3% / Sharpe 0.79 / maxDD −35.5%** vs the universe **22.6% / 0.51 / −49.9%** (momentum was *lower*-risk on dev, so a positive `Δ_net` there is not mere risk compensation; the sealed window re-tests this). Plus the `Δ_net` bootstrap CI (A2). |
| **Reproducibility** | §1.1 pinned substrate → deterministic, byte-identical re-run; dev numbers reproduce from `scripts/csmp/phase1_prereg_analysis.py`. |
| **Operational** | `evaluate()` deterministic, side-effect-free; consumer `GuardedSignalSource`-wrapped, PaperBroker only. |
| **Calibration** | The §7 uncertainty-tercile monotonic-IC test; dev-measured, held-out reported once, non-gating. |

---

## 10. Post-Experiment Decision Table (fixed before results exist)

Gate = the one-sided 95% lower bound of `mean_IC` (§3.4 D-i/D-ii); `Δ_net` is the deployment qualifier.

| Sealed-window outcome | Verdict | Next action |
|---|---|---|
| `mean_IC` lower bound > 0 **and** `Δ_net > 0` | **Approved & deployable** | Phase 7: top-40 EW PaperBroker consumer, measured forward vs the stronger baseline. |
| `mean_IC` lower bound > 0 **but** `Δ_net ≤ 0` | **Approved, not deployed** (signal real, no net transmission — the D1 outcome, out-of-sample) | Record; do not tune. Cost-aware/lower-turnover construct is a new increment-2 pre-registration. |
| `mean_IC` lower bound ≤ 0, `mean_IC > 0` | **Inconclusive (underpowered — the modal outcome, ~60%, §3.4)** | **Not Approved. The sealed window is spent once and never re-read** (re-reading nested data is the D-iii multiplicity trap — naive-schedule FWER 0.130). The artifact stays **Not Approved**; per the **charter §6 amendment (2026-07-12, Phase-2 F3; recorded in `CSMP_PHASE0_CHARTER.md`)** the top-40 PaperBroker consumer may still be built and run as an **explicitly exploratory** deployment, under four controls: (1) it is **not** Phase-7 completion and must not be recorded as such; (2) it may **never** appear in Approved / Deployable / certified language — in code, dashboards, or reports; (3) it runs under a **separate exploratory runbook**, distinct from the production consumer path; (4) its forward data (2026-07 onward) may enter **only** a fresh pre-registration with frozen rules and fresh α — never a re-read of the spent window, never a retrofit of this one. This is an **amendment to charter §6's Approval precondition, not satisfaction of it** — the earlier disclosure-only framing (which treated the precondition as met because a PaperBroker consumer puts no capital at risk) is **withdrawn** (Phase-2 F3): it modelled capital risk alone and did not answer anchoring, sunk cost, or the quiet promotion of a Not-Approved artifact into an operationally trusted one. |
| `mean_IC ≤ 0`, **any** `Δ_net` | **Artifact Rejected (falsified)** | The IC is the gate (charter D3). Incl. the **tail-driven case** `mean_IC ≤ 0` **but** `Δ_net > 0` (B4): rank IC is insensitive to the right tail, and an EW top-bucket harvests much of its return *from* the tail, so a few large winners carrying the book while the ordering is otherwise noise is a live outcome — it is **not** the hypothesis and does not rescue it. "The payoff is in the tail, not the ranking" is a separate increment-2 pre-registration. Do not deploy. |

---

## 11. Threats to Validity

> A valid, one-sided, correctly-covered test on 42 months is **~41% powered** against the program's own point estimate. **The single likeliest outcome of Phase 6 is "Inconclusive" (~59%) — even if the hypothesis is exactly true.** This was computed **before the window was spent, not after.**

**Statistical power & test validity (B2 + S2) — the dominant threat, now quantified and settled.** Two facts, both dev-computable, both in `scripts/csmp/phase1_ci_coverage.py`: **(1) validity** — the originally pre-registered L=12 moving-block percentile CI covers at only **81%** at n=42 (one-sided Type-I ~13%, ≈ 2.6× nominal); it is replaced by the one-sided Student-t interval, which covers at 0.957 / Type-I 0.049 (§3.4). **(2) power** — on that *valid* test, if the true out-of-sample edge equals the dev 0.0458, the gate clears only **~40%** of the time. **In plain words: "Inconclusive" is the single most likely outcome (~60%) even if the hypothesis is exactly true.** ~40% is not a good test; it is the honest ceiling on 42 months, and the incumbent's higher apparent power was a false-positive rate wearing power's clothes. This is a property of the available sample, not the hypothesis; §10 row 3 gives it a defined next step so it cannot become a licence to tune.

**Effective sample size (S3) — a conceptual correction.** The cross-section (~200 names) reduces the *measurement error of each monthly `IC_t`*; it does **not** reduce the *month-to-month dispersion of the true IC*, which governs the power of `mean_IC`. Under the null, a 200-name Spearman has sampling SD ≈ `1/√199 ≈ 0.071`, versus the observed `SD = 0.208` — so `√(0.208² − 0.071²) ≈ 0.196` of the SD is **genuine month-to-month variation** in momentum's efficacy. **The effective n for the gate is 42, not ~8,400.** (The charter §1 "order of magnitude more observations" claim is the root cause of the power question going unnoticed; it is corrected here.)

**Momentum crashes / regime dependence.** Dev by-year IC was negative in 2014, 2016 (25% hit), 2022. Fat left tail at reversals; no crash overlay (charter fence); drawdown disclosed (§9), not hedged.

**Crowding / decay (central external-validity threat).** Indian momentum is ETF-implemented (NIFTY200 M30, live 2020 — *before* the sealed window even opens); the dev edge may have decayed. **This is precisely what the sealed test measures.** A decayed edge is a legitimate falsification. **This threat also decides D-iii (§3.4):** a group-sequential extension's road to 80% power reaches ≈2033 and banks power *conditional on the edge holding at dev strength for seven more years* — but simulating a post-2026 decay collapses Pocock's terminal power from 0.73 to **0.34** (below single-shot's decay-invariant 0.41), while it has already halved the primary read to 0.24. A program cannot stake its recovery plan on the falsity of its own primary risk, and "wait seven years for the edge to appear" removes the possibility of being usefully wrong (MSRP's STOP was valuable because it *arrived*). Hence the ratified single-shot design: score the window once on data that already exists, and buy any further power from **new** forward months via a fresh pre-registration (§10 row 3), never from re-reading the spent window.

**Internal validity (leakage / survivorship).** (i) No parameter chosen against held-out — all fixed on charter/dev; (ii) survivorship via delisting-drop — closed by §5.2 and confirmed immaterial-but-correct on dev (§2.1); (iii) survivor-list contamination — excluded by gate-(c) PIT construction.

**Forward-return horizon heterogeneity (S9).** A §5.2 rule-1 name contributes a *partial-month* return while continuing names contribute a full month; the Spearman IC and the block bootstrap treat these as homogeneous. Small (delistings are rare) but real; the per-month rule-1/rule-2 counts (§5.2) bound it.

**Execution realism.** Close-price fills are optimistic even with `κ`; impact/partial fills for the top-40 tail are unmodelled. PaperBroker-only (Phase 7); no LIVE claim (MM14).

---

## 12. Assumptions and Known Simplifications

1. **Gate-(b) CA adjustment is correct over the sealed window** — the scariest inherited assumption (dev residue 0; sealed residue was counted-not-examined by gate (b)). **Now guarded by the §8 A1 VOID precondition**, which re-runs the move screen before any metric is read.
2. Gate-(c) mechanical `turnover_top200` is an acceptable stand-in for true index membership (official history unobtainable — gate c); turnover rank may diverge from the published index at the margin.
3. `κ = 5 bps/side` is a single disclosed, non-optimized assumption; gate-(d)'s pre-2020 stamp / post-2024 txn `[VERIFY]` notes are immaterial in magnitude.
4. Equal-weight, monthly, no intra-month rebalancing; drift not re-traded (symmetric).
5. **K-shortfall / bucket structure (S5):** if a sealed month has fewer than 40 formation-complete names, hold all of them; the 40/40 quintile spread assumes **≥ 80** names with forward returns per month. Structurally guaranteed on dev (exactly 200 members/month, ≈197 with forward returns) and **inherited, not re-certified, for the sealed window** — the VOID/point-in-time checks will surface any breach.
6. Reference arm removed (R1); its absence never affects the verdict (was non-gating).
7. `uncertainty` reflects formation-window dispersion only (no fitted parameter exists); reported-not-acted-on (§7).
8. Overnight/gap risk between rebalance signal and fill unmodelled; PaperBroker fills at the adjusted close (disclosed for Phase 7).

---

## 13. Sources

| Source | Role |
|---|---|
| `docs/reports/CSMP_PHASE0_CHARTER.md` | D1–D5 this dossier operationalizes |
| `docs/reports/CSMP_GATE_C_UNIVERSE_AUDIT.md` / `_LEAD_REVIEW.md` | PIT survivorship-free universe |
| `docs/reports/CSMP_GATE_B_CORPORATE_ACTIONS_AUDIT.md` | CA-adjusted price view; the A1 move screen |
| `core/execution/equity/delivery_fees.py` / `CSMP_GATE_D_LEAD_REVIEW.md` | Delivery-fee model |
| `docs/reports/CSMP_GATE_E_TRIAGE.md` / `_LEAD_REVIEW.md` | Dev transmission evidence (pre-§5.2) |
| `docs/reports/CSMP_PHASE1_DOSSIER_LEAD_REVIEW.md` | The reconciled Lead Review (B1–B4, S1–S9, A1–A3, R1–R4) folded into Rev 2 |
| `docs/reports/CSMP_PHASE1_OPERATOR_DECISIONS.md` | Lead-Reviewer memo reordering D-i/D-ii; folded into Rev 3 |
| `docs/reports/CSMP_PHASE1_FREEZE_RATIFICATION.md` | Operator ratification of D-i/D-ii/D-iii and author-lock (applied at Rev 6) |
| `docs/reports/CSMP_PHASE2_INDEPENDENT_REVIEW.md` | Independent Phase-2 review (GPT-5/Codex): F1/F2/F3, folded at Rev 7 |
| `docs/reports/CSMP_PHASE2_LEAD_DISPOSITION.md` | Lead disposition accepting F1/F2/F3; the ratified one-sided D-i rule + F3 amendment |
| `scripts/csmp/phase1_prereg_analysis.py` | Dev-only; reproduces every §2.1/§8/§11 number (seed 20260711) |
| `scripts/csmp/phase1_ci_coverage.py` | Dev-only; the §3.4 D-i coverage simulation (CI-method selection) |
| `scripts/csmp/phase1_group_sequential.py` | Dev-only; the §3.4 D-iii extension-schedule FWER + α-spending boundaries |
| `docs/reports/MSRP_PHASE1_RESEARCH_DOSSIER.md` | Template; the D1 lesson |
| MSI-007 / `MSI_006_VALIDATION_FRAMEWORK.md` / MM13 `KnowledgeSignalSource` | Artifact shape; seven domains; consumer contract |
| Jegadeesh & Titman (1993); Asness, Moskowitz & Pedersen (2013) | Momentum precedent |

---

*End of pre-registration — **FROZEN (Rev 7, 2026-07-12).** Nothing here reports a result computed on the sealed held-out window (2023-01 → 2026-06); the §2.1 / §3.4 numbers are dev-window (2012–2022) or calendar facts, reproducible from `phase1_prereg_analysis.py`, `phase1_ci_coverage.py`, and `phase1_group_sequential.py` (seed 20260711). The dossier passed the independent Phase-2 review (`CSMP_PHASE2_INDEPENDENT_REVIEW.md`) with F1/F2/F3 folded in (`CSMP_PHASE2_LEAD_DISPOSITION.md`); D-i/D-ii/D-iii are operator-ratified (`CSMP_PHASE1_FREEZE_RATIFICATION.md`). The construct fence (universe, score, K=40, metric, baselines, cost model, §5.2 delisting convention, ratified inference/extension design) is now **immutable** — any change is a new pre-registration for a new increment, not an edit. The only remaining step is **Phase 6**: the single sealed read, subject to the §8 A1 VOID precondition. The window has not been read.*
