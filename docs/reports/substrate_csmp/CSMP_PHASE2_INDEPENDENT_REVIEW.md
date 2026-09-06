# CSMP Phase 2 - Independent Model Review

**Date:** 2026-07-12
**Reviewer:** Codex / GPT-5, acting as the third-model Phase-2 reviewer
**Artifact reviewed:** `docs/reports/CSMP_PHASE1_RESEARCH_DOSSIER.md` Rev 6
**Verdict:** **PASS WITH REQUIRED REVISIONS**

The dossier is not safe to freeze as-is. The dev evidence reproduces on the dev-truncated store, the sealed-window fence held, and the core construct is coherent. But D-i's CI-method selection rule is internally inconsistent: the written rule says "coverage closest to nominal", while the printed table would select `iid_perc` on two-sided coverage, not the ratified Student-t method. Student-t is selected only if the rule is explicitly "one-sided Type-I closest to nominal" for the one-sided gate. That must be fixed before Rev 7 freezes.

I did not read the sealed window. I ran the three required scripts with `equity_bhavcopy_devtruncated.duckdb` temporarily placed at the hardcoded path `data/market_data/equity_bhavcopy.duckdb`, then restored the full store. The truncated-store SHA-256 matched the handoff:

`c6945bdf657c2f79dd8d99d57579751709429f7bb2b42efb6e66fabefd64694c`

Seal checks on the truncated store:

| Check | Result |
|---|---:|
| `equity_bhavcopy` row count / max date | 5,077,338 / 2022-12-30 |
| `equity_bhavcopy_adjusted` rows on or after 2023-01-01 | 0 |
| `adjustment_factors` rows on or after 2023-01-01 | 382 |
| `adjustment_factors` columns | `symbol`, `ex_date`, `factor`, `action_type`, `source` |

The 382 post-2022 adjustment factors are bare multiplicative metadata, not prices, returns, or cash amounts. I accept the handoff rationale that retaining them is necessary for byte-exact backward-adjusted dev reproduction across rename/CA boundaries.

## Re-derived Evidence

`scripts/csmp/phase1_prereg_analysis.py` reproduced the dossier's load-bearing dev numbers:

| Quantity | Re-derived |
|---|---:|
| Dev IC sample | n = 131 |
| Mean IC / SD / t | 0.0457 / 0.2079 / 2.52 |
| L=12 block-bootstrap CI | [0.0091, 0.0811] |
| Rule-1 / rule-2 forward-return events | 21 / 1 |
| Formation exclusions | 382 |
| Top-40 net, fees | 15.44% |
| Formation-complete universe net, fees | 9.20% |
| Net spread, fees | +6.24% |
| Net spread, fees + 5 bp/side slippage | +5.95% |
| Gate-(e) re-run verdict | CONTINUE |

The -100% rule-2 sensitivity also stayed CONTINUE: mean IC unchanged to 4 dp, fees-only spread +6.28%, fees+slippage spread +5.99%.

`scripts/csmp/phase1_ci_coverage.py` reproduced the D-i table:

| Method | 2s coverage | 2s Type-I | 2s power | 1s Type-I | 1s power |
|---|---:|---:|---:|---:|---:|
| Student_t | 0.957 | 0.024 | 0.286 | 0.049 | 0.398 |
| iid_perc | 0.949 | 0.027 | 0.308 | 0.054 | 0.418 |
| mb_L12 | 0.811 | 0.097 | 0.469 | 0.129 | 0.538 |
| stationary_L3 | 0.924 | 0.038 | 0.347 | 0.064 | 0.453 |

`scripts/csmp/phase1_group_sequential.py` reproduced the D-iii table:

| Design | Phase-6 #42 power | Terminal power |
|---|---:|---:|
| Single-shot | 0.412 | n/a |
| Naive repeated looks | invalid; FWER 0.130 | 0.867 inflated |
| O'Brien-Fleming | 0.042 | 0.784 |
| Pocock | 0.241 | 0.727 |

Pocock terminal power under post-#42 decay reproduced as 0.727 if the edge persists, 0.497 if it halves, and 0.339 if it dies after 2026.

## Findings

### F1 - HIGH - The D-i selection rule does not select Student-t as written

**Claim:** The dossier says the CI method is selected by "coverage closest to nominal", but the printed coverage table makes `iid_perc` closer to nominal two-sided coverage than Student-t.

**Failure scenario:** Rev 7 freezes the sentence "pick the method whose n=42 coverage is closest to nominal." The Phase-6 operator or an external auditor applies that rule mechanically to the table in the dossier: `iid_perc` has 2-sided coverage 0.949, distance 0.001 from 0.950; Student-t has 0.957, distance 0.007. The frozen text therefore points to `iid_perc`, while the implementation and ratification use Student-t. If the sealed result is near the decision boundary, the program has two plausible frozen gates and can choose after seeing the result.

**Evidence:** The reproduced `phase1_ci_coverage.py` output is exactly the table above. Student-t is closest on **one-sided Type-I**: 0.049 is distance 0.001 from 0.050, while `iid_perc` is 0.054, distance 0.004. That is a valid reason to choose Student-t for a one-sided gate, but it is not the rule currently written in the dossier, operator memo, or ratification record.

**Fix:** Before freeze, rewrite D-i everywhere as a one-sided-gate calibration rule. Minimal wording: "Because the primary gate is one-sided, select the method whose one-sided null rejection rate is closest to nominal 0.050, with two-sided coverage reported as a sanity check." Then keep Student-t. Alternative: keep the literal two-sided coverage rule and freeze `iid_perc`. Do not freeze the current hybrid.

### F2 - MEDIUM - The CI coverage simulation does not use the frozen section 5.2 forward-return convention

**Claim:** `phase1_ci_coverage.py` builds the dev IC population by requiring a full `t+1` price and silently dropping names without `pb`, while the dossier says section 5.2 is binding on every forward return in the IC set.

**Failure scenario:** A future re-run or port of the coverage script on a store/window with more missing forward prices estimates the IC population from a survivorship-filtered series. That can change the empirical IC distribution, the simulated coverage, and the method selected by D-i. The frozen dossier would claim section 5.2 was applied while the calibration code did not apply it.

**Evidence:** In `scripts/csmp/phase1_ci_coverage.py`, `dev_ic_series()` appends a return only under `if p12 and p1 and pa and pb and p12 > 0 and pa > 0`, then uses `pb / pa - 1.0`. It does not implement rule 1 or rule 2. The current numeric effect is small: the section-5.2 re-run reports mean IC 0.0457, while the coverage script reports 0.0458. Small is not the same as aligned.

**Fix:** Refactor the coverage script to reuse the same `fwd()` convention as `phase1_prereg_analysis.py`, then re-run the table. If the selected method and figures remain unchanged, record that as the closure. If they move, update the dossier before freeze.

### F3 - MEDIUM - The Not-Approved PaperBroker path is a charter amendment, not merely "satisfied in substance"

**Claim:** The dossier and ratification record reframe charter section 6's Approval precondition as satisfied by disclosure because PaperBroker has no capital at risk. That is too narrow a risk model.

**Failure scenario:** Phase 6 returns Inconclusive. The artifact is formally Not Approved, but the program still builds and runs a production-shaped consumer under the Phase-7 banner. Over time, dashboards, reports, and engineering investment cause the Not-Approved artifact to become operationally trusted. Forward PaperBroker performance is then interpreted with anchoring and sunk-cost pressure, or used to justify incremental changes, despite the original sealed test failing to approve the artifact.

**Evidence:** The current decision table explicitly says the top-40 PaperBroker consumer is built "regardless of verdict" after an Inconclusive result. The ratification record says the Approval precondition is "satisfied-in-substance by disclosure." That handles capital risk but not epistemic, governance, or promotion risk. Charter section 6 originally made Approval a phase precondition; changing what counts as satisfying it is a real amendment.

**Fix:** Keep the engineering path if the operator wants it, but label it as an explicit charter amendment with controls, not as satisfaction of the old condition. Minimal controls: the post-Inconclusive consumer is not called Phase 7 completion, cannot be used in any Approved/Deployable language, has a separate exploratory runbook, and its forward data can only enter a fresh pre-registration with frozen rules and fresh alpha.

## Charter Lenses

**Hidden assumptions:** The largest hidden assumption is now F1: "coverage" changes meaning between two-sided coverage and one-sided Type-I. The PaperBroker path also assumes no-capital-risk means no governance risk; I do not accept that as written.

**Leaking features:** I found no evidence that the score sees future prices. The score uses `t-12` to `t-1`, membership is PIT, and the dev scripts fence queries at `trade_date <= 2022-12-31`. The dev-truncated store structurally prevented sealed price reads during this review.

**Unstable labels:** Section 5.2 is a real improvement. Rule 1/2 events are rare on dev, the -100% rule-2 stress did not change the verdict, and required disclosure of top-40 rule-2 events is appropriate. F2 is the remaining alignment issue: every analysis script that calibrates the gate should use the same label convention.

**Causal vs predictive:** The economic rationale is adequate for a pre-registered predictive test. The dossier does not overclaim causality; it uses momentum precedent to justify a directional H1, then correctly lets the sealed window adjudicate generalization.

**Unmodelled uncertainty:** The mean-IC uncertainty is now honestly treated. `Delta_net` remains a deployment point-estimate qualifier, but the dossier already requires a reported non-gating block-bootstrap CI. Execution slippage and close-fill optimism are disclosed; live execution is out of scope.

## Checked And Found Sound

- The dev-truncated handoff store has no sealed priced rows in `equity_bhavcopy` or `equity_bhavcopy_adjusted`.
- The three required scripts reproduced the dossier's key numbers on the truncated store.
- Gate-(e) survives the section-5.2 delisting convention and the -100% rule-2 sensitivity.
- The slippage 2x correction is arithmetically right: top-40 drag 33.0 bp/yr, universe drag 4.0 bp/yr, differential 29.0 bp/yr.
- K=40 is not contradicted by the gate-(e) record: the audited code/report show top-quintile net results and gross quintile/decile spreads, not a top-30 net search.
- The single-shot choice over Pocock is defensible under the charter's crowding/decay threat. Pocock buys later power by cutting the primary read from about 0.41 to 0.24 and relies on survival of the edge to 2033.
- The post-experiment decision table is exhaustive in the important result states: Approved/deployable, Approved/not deployed, Inconclusive, and Rejected.

## Could Not Check

- I did not inspect or compute any sealed-window statistic. The full store exists on this machine, but script execution was done with the dev-truncated store at the hardcoded path.
- I did not independently re-audit gate (a) through gate (d) from raw exchange files. I reviewed their inherited claims through the dossier, gate reports, and the scripts.
- I did not test official NIFTY 200 membership against the mechanical `turnover_top200` fallback. The dossier correctly discloses this as an inherited simplification.
- I did not validate future Phase-6 harness code, because it does not exist in this review scope.

## The 41% Power Judgment

Yes, the approximately 41%-powered experiment is worth running, with the F1/F2 fixes applied.

The reason is not that 41% is strong. It is weak, and the dossier now says so plainly. The reason to proceed is that the sealed 2023-01 to 2026-06 window already exists, the construct is parameter-light, the gate is now close to calibrated, and the alternative ways to increase apparent power either inflate Type-I error or wait until 2033 while assuming away the program's own decay risk. A single honest read that often returns Inconclusive is still useful evidence. It is also better governance than repeated looks at the same window.

The condition is that Inconclusive must remain Not Approved. Any forward PaperBroker work after that should be explicitly exploratory and governed as a new-data collection path, not treated as a quiet continuation of an approved strategy.

## Required Before Freeze

1. Fix D-i's rule/selection mismatch by making the selection criterion explicitly one-sided Type-I closeness, or switch the frozen method to the literal two-sided-coverage winner.
2. Re-run `phase1_ci_coverage.py` under the section-5.2 forward-return convention and update the table if anything changes.
3. Recast the Not-Approved PaperBroker path as an explicit charter amendment with guardrails, not as automatic satisfaction of the Approval precondition.

After those revisions are folded in, I would expect the dossier to be safe to freeze at Rev 7 without another full Phase-2 cycle, provided the revised text and re-run outputs are mechanically reviewed.
