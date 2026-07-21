# RFA v2 Remediation Report — Tasks 1–5

**Date:** 2026-07-21
**Status:** CLOSED

---

## 1. What changed and why

### Tasks 1–4 (prior work, commits `43c5d46`, `3767c21`, `d7fa9c8`)

| Task | Change | SHA |
|---|---|---|
| T1 | O1 PROCEED withdrawn — banner on `O1_RFA.md`, body preserved | `43c5d46` |
| T2 | Contract v2 — Sharpe band for `per_trade_pnl`, delta/sd rejected for that metric | `3767c21` |
| T3 | `METHODOLOGY_VERSION` → `2.0.0`; `o1_vrp` (1.0.0) now hard-fails | `3767c21` |
| T4 | `report.py` — conditional independence claim for `rank_ic`, no-crossed-corner text for PnL | `d7fa9c8` |

### Task 5a — Delete stale DayTypeEngine section from `CLAUDE.md`

The `## DayTypeEngine — Feature Blocks` section (lines 100–114) documented a component that does not exist in the repository — pre-SALVAGE residue. No `.py` file contains `DayTypeEngine`, `build_intraday_features.py`, `train_daytype_classifier.py`, or a `logistic_13pm_prod` model artifact. The deletion makes `CLAUDE.md` consistent with its own "Production Strategy Status" section, which states historical designs were not ported during the SALVAGE migration.

### Task 5b — Update RFA section for contract v2

Added to the RFA section in `CLAUDE.md`:
- **Contract v2 / METHODOLOGY_VERSION 2.0.0**: for `per_trade_pnl`, declared quantity is an annualized Sharpe band + `cadence_per_year`; supplying separate delta and SD for that metric is rejected. `rank_ic` retains delta/SD bands.
- **Why Sharpe for PnL**: mean and SD are estimated off the same series, so separate bands let a crossed corner smuggle in an undefended Sharpe.
- **Cadence invariance**: `ncp = S·√T` means higher cadence buys no power — trading weekly vs monthly exactly offsets.
- **O1 withdrawn**: note pointing at `RFA_GATE_O1_REVIEW.md`, no successor authorized.
- Added `RFA_GATE_O1_REVIEW.md` and `RFA_V2_REMEDIATION_PROMPT.md` to the file table.

### Task 5c — Correct cadence claim in SFB-1/F1 section

Line 248 previously claimed "higher cadence → more formations → escapes the sample wall." This is wrong: `ncp = (delta/sd)·√n = S·√T` — cadence `c` cancels because multiplying formations by `c` divides per-formation Sharpe by `√c`. Rewritten to state the honest case: futures help (if at all) through fee structure, never through cadence.

### Task 5d — Caveat O2 in `OPTIONS_STRATEGY_RESEARCH.md`

Two edits:
1. Under the O2 heading: added a caveat block noting the 80%-validation-accuracy classifier does not exist in this repository. O2 cannot be pre-registered until rebuilt and independently validated.
2. In §4 executive summary: corrected "a validated 80% day-type classifier" to acknowledge only two of three claimed assets are real. Softened O2's "monetizes proprietary IP" claim and the O1+O2 slate recommendation accordingly.

---

## 2. Test results

```
$ python -m pytest tests/rfa/ -v
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.0.3, pluggy-1.6.0
rootdir: F:\Nifty
configfile: pyproject.toml
plugins: anyio-4.13.0, asyncio-1.3.0
collected 42 items

tests/rfa/test_contract_v2.py::test_per_trade_pnl_requires_sharpe_band PASSED
tests/rfa/test_contract_v2.py::test_per_trade_pnl_rejects_delta_sd_bands PASSED
tests/rfa/test_contract_v2.py::test_rank_ic_rejects_sharpe_band PASSED
tests/rfa/test_contract_v2.py::test_per_trade_pnl_sharpe_band_range_checks PASSED
tests/rfa/test_contract_v2.py::test_o1_original_bands_now_abandon PASSED
tests/rfa/test_contract_v2.py::test_sharpe_1_0_is_thin_proceed PASSED
tests/rfa/test_contract_v2.py::test_power_is_cadence_invariant PASSED
tests/rfa/test_contract_v2.py::test_withdrawn_declaration_raises_on_version PASSED
tests/rfa/test_declaration.py::test_valid_declaration_passes PASSED
tests/rfa/test_declaration.py::test_declaration_is_immutable PASSED
tests/rfa/test_declaration.py::test_empty_provenance_rejected (3 params) PASSED
tests/rfa/test_declaration.py::test_inverted_bands_rejected PASSED
tests/rfa/test_declaration.py::test_nonpositive_sd_rejected PASSED
tests/rfa/test_declaration.py::test_insufficient_formations_rejected PASSED
tests/rfa/test_declaration.py::test_unknown_test_type_rejected PASSED
tests/rfa/test_declaration.py::test_unknown_metric_rejected PASSED
tests/rfa/test_declaration.py::test_digest_covers_entire_file PASSED
tests/rfa/test_declaration.py::test_digest_changes_when_trailing_bytes_change PASSED
tests/rfa/test_gate.py::test_abandons_when_corner_cannot_clear_hurdle PASSED
tests/rfa/test_gate.py::test_proceeds_when_corner_clears_hurdle PASSED
tests/rfa/test_gate.py::test_verdict_flips_with_inputs_only PASSED
tests/rfa/test_gate.py::test_evaluates_at_optimistic_corner PASSED
tests/rfa/test_gate.py::test_methodology_mismatch_is_hard_failure PASSED
tests/rfa/test_gate.py::test_invalid_declaration_rejected_before_evaluation PASSED
tests/rfa/test_gate.py::test_reports_required_formations_at_each_band_point PASSED
tests/rfa/test_power.py::test_reproduces_documented_formation_requirement PASSED
tests/rfa/test_power.py::test_power_increases_with_n PASSED
tests/rfa/test_power.py::test_power_increases_with_delta_and_decreases_with_sd PASSED
tests/rfa/test_power.py::test_one_sided_needs_fewer_observations_than_two_sided PASSED
tests/rfa/test_power.py::test_degenerate_inputs_return_zero_power PASSED
tests/rfa/test_power.py::test_n_required_returns_none_when_unreachable PASSED
tests/rfa/test_power.py::test_matches_psb1_bootstrap_reference PASSED
tests/rfa/test_report.py::test_report_states_verdict_and_digest PASSED
tests/rfa/test_report.py::test_proceed_is_qualified_as_not_provably_infeasible PASSED
tests/rfa/test_report.py::test_report_carries_scope_caveat_and_corner_rationale PASSED
tests/rfa/test_report.py::test_report_reproduces_provenance_verbatim PASSED
tests/rfa/test_retrospective.py::test_gate_fires_on_c5_c4_and_f1 PASSED
tests/rfa/test_retrospective.py::test_c2_as_recorded_in_psb2_does_not_fire PASSED
tests/rfa/test_retrospective.py::test_c2_fires_only_on_extended_history_reestimate PASSED
tests/rfa/test_retrospective.py::test_f1_dispersion_is_flagged_approximate PASSED

============================= 42 passed in 1.93s ==============================
```

**34 original + 8 new in `tests/rfa/test_contract_v2.py`** — all 42 pass.

---

## 3. Invariant confirmation

### Invariant 1: `o1_vrp.py` digest unchanged

```
$ python -c "import hashlib; data=open('governance/rfa/declarations/o1_vrp.py','rb').read(); print(hashlib.sha256(data).hexdigest())"
25d4a723679ade9dedcabcf94d9968074e3e0e350f158630e301f697b64f2dad
```

Digest matches the published value — the withdrawal preserves the declaration file as recorded.

### Invariant 2: `scripts/rfa/retrospective.py` still passes

```
$ python -m scripts.rfa.retrospective
C5             power=0.5422 -> ABANDON
C4             power=0.4110 -> ABANDON
C2_PSB2        power=0.9198 -> PROCEED
C2_PHASE0_5    power=0.6563 -> ABANDON
F1_TRAIN       power=0.5672 -> ABANDON
```

The retrospective uses `Case` tuples, not `Declaration`, so the contract change did not touch it. All five cases report the expected verdicts.

---

## 4. What is now true

A future builder needs to know:

1. **O1 is withdrawn.** The sole real declaration (Nifty VRP) returned PROCEED via a crossed-corner artifact. The declaration file and its digest are preserved; no successor is authorized.

2. **Sharpe band is the declared quantity for PnL metrics.** For `metric="per_trade_pnl"`, declarations supply an annualized Sharpe band + `cadence_per_year`. Separate delta and SD bands are rejected for this metric. For `rank_ic`, delta/SD bands remain.

3. **Cadence buys no statistical power.** `ncp = S·√T` — cadence cancels. The only escapes from the demonstrability wall are a longer calendar window or a genuinely higher Sharpe.

4. **DayTypeEngine does not exist.** The component documented in `CLAUDE.md` was pre-SALVAGE residue not ported in the 2026-06-04 migration. No `DayTypeEngine` class, `build_intraday_features.py`, `train_daytype_classifier.py`, or `logistic_13pm_prod` model artifact exists in this repository.

5. **RFA gate contract v2 / METHODOLOGY_VERSION 2.0.0** is in effect. Any declaration with `methodology_version != "2.0.0"` is rejected as a hard failure before evaluation.

---

## 5. Disputes and findings

No disputes with the specification. All specifications were implemented as directed. One note:

- The prompt's reference table (Sharpe 0.601→0.4908, 1.0→0.8540, 1.442→0.9877) is the v1 evaluation of O1's original delta/SD bands translated to Sharpe space. Under v2, these values are no longer produced by the gate (v2 reads Sharpe directly from the declaration). The tests confirm the gate's behavior is correct for both v2 declarations and v1 declarations (which are now rejected).

---

## Files changed

| File | Change |
|---|---|
| `CLAUDE.md` | Delete DayTypeEngine section (§5a); update RFA section for v2 (§5b); correct SFB cadence claim (§5c) |
| `docs/reports/OPTIONS_STRATEGY_RESEARCH.md` | Caveat O2 classifier nonexistence; correct §4 three-assets claim (§5d) |
| `docs/reports/RFA_GATE_O1_REVIEW.md` | Committed (untracked → tracked, §6) |
| `docs/reports/RFA_V2_REMEDIATION_PROMPT.md` | Committed (untracked → tracked, §6) |
| `docs/reports/RFA_V2_TASK5_PROMPT.md` | Committed (untracked → tracked, §6) |

---

**Commit:** `2b37fe1` (Task 5 + Task 6)
**Tasks 1–4:** `43c5d46`, `3767c21`, `d7fa9c8`
