# MSRP Phase 6 — Execution-Attestation Review

**Document type:** Independent review (execution attestation)

**Subject:** Attestation that the single Phase-6 held-out scoring run executed faithfully against the certified harness

**Date:** 2026-07-07

**Reviewer:** Phase-6 attestation

**Status:** PASS — all six checks verified

---

## 1. Attestation Checks

### Check 1 — Evaluation window

`results.json → results.evaluation_window` is exactly `["2026-01-01", "2026-07-03"]`.

**PASS.**

### Check 2 — Single-touch

Exactly one Phase-6 record exists for the window `[2026-01-01, 2026-07-03]`: `validation_id = 47fe32723aa9da163aee5b32e72934609187fec79f254c7b95d64629e75a6c42`. The Phase-6 duplicate guard is in force.

**PASS.**

### Check 3 — Pinned substrate

`methodology.json` substrate matches the pre-flight pinned values:

| Field | Value | Match? |
|-------|-------|--------|
| `block_length` (L) | 28 | ✓ |
| `n_replicates` (B) | 10000 | ✓ |
| `seed` | 42 | ✓ |
| `delta_auc_bar` | 0.03 | ✓ |
| `median_window` | 20 | ✓ |
| `dossier_commit` | `d9233b1` | ✓ |
| `statsmodels` | `0.14.6` | ✓ (real version pinned, not "n/a") |

**PASS.**

### Check 4 — All seven domains resolved

`record.json → domain_verdicts` lists all seven mandatory MSI-006 domains:

| Domain | Status |
|--------|--------|
| architectural | PASS |
| scientific | PASS |
| temporal | PASS |
| robustness | REPORTED (by-design — informational, non-gating) |
| operational | PASS |
| calibration | PASS |
| reproducibility | PASS |

None missing, none defaulted. Robustness is `REPORTED` per the design spec §4.4 — correct.

**PASS.**

### Check 5 — §10 decision table mapping

Observed values: `delta_auc_gate = 0.090767`, `ci_lower = 0.019941`, `ci_upper = 0.212755`.

- `ΔAUC_gate ≥ 0.03`: **yes** (0.090767 ≥ 0.03)
- 95% CI excludes 0: **yes** (ci_lower = 0.019941 > 0)

Maps to dossier §10 row 1 → **Approved**. `record.json → candidate_verdict = "Approved (candidate)"` — matches.

**PASS.**

### Check 6 — Determinism / results_digest

- `record.json → results_digest` = `2a944f974109ba98580563542df32eb7df8dada149fef1f149ade728d8643bc0`
- Reproducibility domain evidence: `"in_domain_double_run_equal": true` — the harness itself verifies byte-identical `results_digest` across two `_score()` invocations.

Both values agree — the harness's reproducibility guarantee holds.

**PASS.**

---

## 2. Qualifier — ΔAUC_vix

`ΔAUC_vix = 0.066193 > 0`. Per dossier §3.4, this Approved verdict substantiates the §2.1 claim that "the HAR-RV structure adds forecasting power over and above the market's own implied forecast" — not merely "beats the fixture bucket."

Context: `AUC_candidate = 0.584943`, `AUC_fixture = 0.494176` (near-chance), `AUC_vix = 0.518750`. The 3-level fixture bucket coarsens VIX information; the raw-VIX comparison is the sharper bar, and the candidate clears it.

---

## 3. Attestation Verdict

**PASS.** The single held-out scoring run executed faithfully against the certified harness. All seven domains resolved correctly. The machine verdict (Approved) maps correctly to dossier §10 row 1. The sealed record carries the attested numbers. Re-seal authorized.

---

*End of execution-attestation review.*
