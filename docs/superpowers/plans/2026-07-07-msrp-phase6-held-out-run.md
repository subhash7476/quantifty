# MSRP Phase 6 — Single Held-Out Scoring Run — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pin the last open reproducibility parameter, then execute the certified A2 validation harness exactly once on the sealed held-out window (2026-01-01 → 2026-07-03), attest the run, and record the pre-registered verdict.

**Architecture:** Three stages. Stage 1 (pre-flight, dev/synthetic only) derives the bootstrap block length `L` from dev-window RV autocorrelation, verifies the seal and provenance, and rehearses the pipeline on a dev window. Stage 2 runs the one-shot `--phase 6` official scoring. Stage 3 attests the run (execution-attestation review + re-seal) and produces the report, KB sync, and tag. No production code changes to any frozen component; the only new code is two small governance/analysis scripts.

**Tech Stack:** Python 3.10+, numpy, pandas, duckdb, statsmodels, scipy, pytest. Certified harness in `core/msi/msrp/`; runner `scripts/msrp/run_forward_vol_validation.py`.

## Global Constraints

- **Single-touch invariant:** the held-out window `2026-01-01 → 2026-07-03` is read exactly once — in Task 5 (the `--phase 6` run). Every other task reads dev/synthetic data or already-sealed output files only. Any step that would read a 2026-dated candle file before Task 5 is wrong by construction.
- **No frozen-component edits.** The artifact (`core/msi/artifacts/forward_vol_v2/`), harness (`core/msi/msrp/`), DRA, and execution platform are unchanged. Additive only.
- **Pre-registered, immutable rules.** Model/label/features/metric/decision-rule are frozen in `docs/reports/MSRP_PHASE1_RESEARCH_DOSSIER.md` (commit `d9233b1`). The §10 decision table governs every outcome. Nothing is tuned, re-run, or reinterpreted after results appear.
- **Substrate:** `B = 10000` replicates, `seed = 42`; `L` derived in Task 1 (never a hardcoded 10).
- **Dossier §5 RV construct:** `RV_t = sqrt(Σ_k r_{t,k}²)`, `r_{t,k} = ln(P_{t,k}/P_{t,k-1})` over 1m `NSE_INDEX|Nifty 50` closes; intraday only. Use `core.msi.msrp.validation_scoring.compute_daily_rv` — never re-implement.
- **Dev window:** `2023-01-02 → 2025-12-31`. **Held-out window:** `2026-01-01 → 2026-07-03`.

---

## File Structure

- **Create:** `scripts/msrp/derive_block_length.py` — dev-only ACF → `L` derivation (Task 1). Auditable, committed.
- **Create:** `scripts/msrp/seal_phase6_attestation.py` — reconstructs the record from sealed JSON and re-seals with attestation fields (Task 6). Reads no held-out data.
- **Create:** `docs/implementation/msrp/reports/MSRP_PHASE6_PREFLIGHT.md` — records the `L` derivation (full ACF table), seal-integrity, and provenance checks (Tasks 1–2).
- **Create:** `docs/implementation/msrp/reports/MSRP_PHASE6_REVIEW.md` — execution attestation (Task 6).
- **Create:** `docs/implementation/msrp/reports/MSRP_PHASE6_REPORT.md` — verdict, numbers, §10 mapping, certification (Task 7).
- **Modify:** `docs/PROJECT_STATE.md`, `docs/CHANGELOG_PLATFORM.md` (Task 8).
- **Generated (not hand-edited):** `core/msi/validations/<validation_id>/` — the sealed record (Task 5), re-sealed in Task 6.

---

### Task 1: Derive & pin the bootstrap block length `L`

Closes dossier §1.1 / §5.3 — the one open pre-registration precondition. Uses a **dev-only loader** (deliberately not the runner's `load_candles_over`, whose `+7 day` forward pad would open January-2026 files and touch the seal).

**Files:**
- Create: `scripts/msrp/derive_block_length.py`
- Create/append: `docs/implementation/msrp/reports/MSRP_PHASE6_PREFLIGHT.md`

**Interfaces:**
- Consumes: `core.msi.msrp.validation_scoring.compute_daily_rv(closes_by_day: Dict[pd.Timestamp, np.ndarray]) -> pd.Series`.
- Produces: an integer `L` (the pinned block length) printed to stdout and recorded in the pre-flight doc; consumed by Tasks 4/5 as the `--block-length` argument.

- [ ] **Step 1: Write the derivation script**

```python
"""Derive the moving-block-bootstrap block length L from DEV-window RV autocorrelation.

Dossier §1.1: L is pinned from dev-window RV autocorrelation, NEVER held-out. This
script reads only 1m Nifty-50 files dated within the dev window (2023-01-02 ..
2025-12-31); it never opens a 2026 file, so the held-out seal is untouched.

Rule: L = smallest lag k>=1 with |ACF(k)| < 1.96/sqrt(n). Fallback (no such lag):
L = floor(n/20), recorded as an override.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import duckdb
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf

from core.msi.msrp.validation_scoring import compute_daily_rv

NIFTY_50 = "NSE_INDEX|Nifty 50"
CANDLES_1M = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
DEV_START = pd.Timestamp("2023-01-02").date()
DEV_END = pd.Timestamp("2025-12-31").date()


def load_dev_closes():
    closes_by_day = {}
    for f in sorted(CANDLES_1M.glob("*.duckdb")):
        try:
            d = pd.Timestamp(f.stem).date()
        except ValueError:
            continue
        if not (DEV_START <= d <= DEV_END):
            continue
        con = duckdb.connect(str(f), read_only=True)
        try:
            rows = con.execute(
                "SELECT timestamp, close FROM candles WHERE symbol = ? ORDER BY timestamp",
                [NIFTY_50],
            ).fetchall()
        finally:
            con.close()
        if not rows:
            continue
        day = pd.Timestamp(rows[0][0]).normalize()
        closes_by_day[day] = np.array([float(r[1]) for r in rows], dtype=float)
    return closes_by_day


def main() -> int:
    closes_by_day = load_dev_closes()
    rv = compute_daily_rv(closes_by_day)
    rv = rv[(rv.index >= pd.Timestamp(DEV_START)) & (rv.index <= pd.Timestamp(DEV_END))]
    vals = rv.to_numpy(dtype=float)
    n = len(vals)
    band = 1.96 / np.sqrt(n)
    nlags = min(40, n // 2)
    a = acf(vals, nlags=nlags, fft=False)

    L, override = None, False
    for k in range(1, nlags + 1):
        if abs(a[k]) < band:
            L = k
            break
    if L is None:
        L = n // 20
        override = True

    print(f"n_dev={n}  band=1.96/sqrt(n)={band:.6f}  nlags={nlags}")
    print("lag,acf,|acf|>=band")
    for k in range(1, nlags + 1):
        print(f"{k},{a[k]:.6f},{abs(a[k]) >= band}")
    print(f"PINNED L={L}  override={override}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the derivation**

Run: `python scripts/msrp/derive_block_length.py`
Expected: prints `n_dev=` (≈740), the full `lag,acf,...` table, and a final `PINNED L=<k>  override=False` line. Record `<k>` — this is the pinned `L`.

- [ ] **Step 3: Record the derivation in the pre-flight doc**

Create `docs/implementation/msrp/reports/MSRP_PHASE6_PREFLIGHT.md` with a `## 1. Block length L derivation` section: paste the script's full stdout (n_dev, band, the ACF table, the pinned `L`, override flag), and one sentence stating the rule applied (§2 of the design spec). State explicitly that the derivation read dev-dated files only.

- [ ] **Step 4: Commit**

```bash
git add scripts/msrp/derive_block_length.py docs/implementation/msrp/reports/MSRP_PHASE6_PREFLIGHT.md
git commit -m "feat(msrp): Phase 6 Task 1 — derive & pin bootstrap block length L from dev-window RV ACF"
```

---

### Task 2: Pre-flight seal-integrity & provenance verification

Confirms the seal is clean and the machinery is at its certified state — without touching held-out data.

**Files:**
- Append: `docs/implementation/msrp/reports/MSRP_PHASE6_PREFLIGHT.md`

- [ ] **Step 1: Verify no prior Phase-6 record for the held-out window**

Run: `ls core/msi/validations/ 2>/dev/null && echo "---" || echo "no validations dir yet (clean)"`
Expected: either no directory, or no sub-directory whose `results.json` has `evaluation_window == ["2026-01-01","2026-07-03"]`. If such a record exists, STOP — the single official run has already happened; do not proceed.

- [ ] **Step 2: Verify artifact checksum integrity**

Run:
```bash
python -c "import json,hashlib,pathlib; d=pathlib.Path('core/msi/artifacts/forward_vol_v2'); c=json.loads((d/'checksum.sha256').read_text()); print('combined', c['combined_hash']); print('OK' if all(hashlib.sha256((d/f).read_bytes()).hexdigest()==h for f,h in c['files'].items()) else 'MISMATCH')"
```
Expected: prints the combined hash and `OK`. If `MISMATCH`, STOP — the frozen artifact has drifted.

- [ ] **Step 3: Verify held-out data snapshot is present through 2026-07-03**

Run: `ls data/market_data/nse/candles/1m/2026-07-03.duckdb data/market_data/nse/candles/1d/2026-07-03.duckdb`
Expected: both files listed. (Presence check only — file contents are not read here.)

- [ ] **Step 4: Record commit hash**

Run: `git rev-parse HEAD`
Expected: a commit hash. Record it in the pre-flight doc as the code commit for the run.

- [ ] **Step 5: Record and commit**

Append a `## 2. Seal-integrity & provenance` section to the pre-flight doc capturing: no prior Phase-6 record (clean), artifact checksum `OK` + combined hash, data snapshot present, code commit hash.

```bash
git add docs/implementation/msrp/reports/MSRP_PHASE6_PREFLIGHT.md
git commit -m "chore(msrp): Phase 6 Task 2 — pre-flight seal-integrity & provenance record"
```

---

### Task 3: Dev-window rehearsal (`--phase 5B`)

A wiring smoke test on a **dev** window — never held-out. Uses `--phase 5B` so it cannot write a Phase-6 record or trip the Phase-6 duplicate guard.

**Files:** none created; produces a throwaway `--phase 5B` record that may be discarded.

- [ ] **Step 1: Run the rehearsal on a dev window**

Run (substitute the pinned `L` from Task 1):
```bash
python scripts/msrp/run_forward_vol_validation.py \
  --phase 5B --window-start 2025-06-01 --window-end 2025-12-31 \
  --block-length <L> --replicates 10000 --seed 42
```
Expected: prints `Validation <id> (<verdict>) -> <path>` and a line with `delta_auc_gate=...`, `CI=(...)`, `base_rate=...`, `n=...`. The run completes without error.

- [ ] **Step 2: Sanity-check the numbers**

Confirm: `n` is roughly the number of dev trading days in the rehearsal window; `base_rate` is in `(0,1)`; the in-sample `delta_auc_gate` is a finite number (in-sample it should generally be non-trivially positive — this is a smoke test, **not** a decision input and is never cited as a result). If the run errors or emits NaNs, STOP and diagnose before any held-out run.

- [ ] **Step 3: Note the rehearsal in the pre-flight doc (no commit of the record)**

Append a `## 3. Dev-window rehearsal` section: the command, the printed summary line, and a one-line "wiring OK — discarded, not a result" note. Optionally delete the throwaway `--phase 5B` record directory. Commit only the doc:

```bash
git add docs/implementation/msrp/reports/MSRP_PHASE6_PREFLIGHT.md
git commit -m "chore(msrp): Phase 6 Task 3 — dev-window rehearsal (wiring smoke test)"
```

---

### Task 4: GO / NO-GO gate (operator confirmation) — STOP

**Files:** none.

- [ ] **Step 1: Present the go/no-go summary to the operator**

Present, in one message: (a) the pinned substrate `L=<k>`, `B=10000`, `seed=42`; (b) the exact Task-5 command that will be run; (c) the pre-flight evidence (seal clean, artifact OK, snapshot present, rehearsal wiring OK). State plainly that the next step reads the sealed held-out window **once, irreversibly**.

- [ ] **Step 2: HALT for explicit authorization**

Do **not** proceed to Task 5 without an explicit operator "go". This is a hard human gate. If executing via subagents, this task is the review checkpoint where the human authorizes the one-shot run.

---

### Task 5: The official held-out run (`--phase 6`) — ONE SHOT

The single scientific act. Reads the held-out window exactly once.

**Files:** generates `core/msi/validations/<validation_id>/` (record.json, results.json, methodology.json, checksum.sha256).

- [ ] **Step 1: Execute the official run**

Run (substitute the pinned `L`):
```bash
python scripts/msrp/run_forward_vol_validation.py \
  --phase 6 --window-start 2026-01-01 --window-end 2026-07-03 \
  --block-length <L> --replicates 10000 --seed 42
```
Expected: prints `Validation <validation_id> (<candidate_verdict>) -> core/msi/validations/<validation_id>` and the `delta_auc_gate=... CI=(...) base_rate=... n=...` line. The Phase-6 duplicate guard passes (first run for this window).

- [ ] **Step 2: Confirm the sealed record exists and is checksum-valid**

Run:
```bash
python -c "import json,hashlib,pathlib,sys; base=pathlib.Path('core/msi/validations'); d=[p for p in base.iterdir() if (p/'results.json').exists() and json.loads((p/'results.json').read_text())['results']['evaluation_window']==['2026-01-01','2026-07-03']][0]; c=json.loads((d/'checksum.sha256').read_text()); ok=all(hashlib.sha256((d/f).read_bytes()).hexdigest()==h for f,h in c['files'].items()); print(d.name, 'checksum', 'OK' if ok else 'MISMATCH')"
```
Expected: prints `<validation_id> checksum OK`.

- [ ] **Step 3: Commit the sealed record (unattested)**

```bash
git add core/msi/validations/
git commit -m "feat(msrp): Phase 6 Task 5 — OFFICIAL held-out scoring run (sealed record, reviewer=None)"
```

---

### Task 6: Execution-attestation review + re-seal

Narrow-scope review (no code review): attest the run executed faithfully, then re-seal with attestation fields via the code's own sealing path. Reconstructs the record from sealed JSON — reads **no** held-out data.

**Files:**
- Create: `scripts/msrp/seal_phase6_attestation.py`
- Create: `docs/implementation/msrp/reports/MSRP_PHASE6_REVIEW.md`

**Interfaces:**
- Consumes: sealed `core/msi/validations/<validation_id>/{record,results,methodology}.json`; `core.msi.msrp.validation.{ValidationRecord, DomainResult, write_sealed_record}`.
- Produces: the same record directory, re-sealed with `reviewer` + `approval_status` set and a recomputed `combined_hash`; `validation_id` and `results_digest` unchanged.

- [ ] **Step 1: Perform the six attestation checks and write the review**

Open the sealed record and verify, recording each in `MSRP_PHASE6_REVIEW.md`:
1. `results.json → results.evaluation_window == ["2026-01-01","2026-07-03"]`.
2. Exactly one Phase-6 record exists **for that window** (a Phase-6 record on any other window is legitimate and ignored).
3. `methodology.json` substrate matches the pinned `L`, `B=10000`, `seed=42` from Task 1.
4. `record.json → domain_verdicts` lists all seven domains (Architectural, Scientific, Temporal, Robustness, Reproducibility, Operational, Calibration), each with a real `PASS`/`FAIL`/`REPORTED` status — none missing.
5. The observed `results.delta_auc_gate` + CI (`ci_lower`,`ci_upper`) maps to the correct dossier §10 row, and `record.json → candidate_verdict` matches that row: `≥0.03 ∧ ci_lower>0` → Approved; `≥0.03 ∧ ci_lower≤0` → Inconclusive; `0<Δ<0.03` → Weak/below-bar; `≤0` → Falsified.
6. `record.json → results_digest` equals the value the harness's Reproducibility domain asserts in `results.json → domains` (no separate re-run).

- [ ] **Step 2: Write the re-seal script**

```python
"""Re-seal a Phase-6 validation record with attestation fields, in place.

Reconstructs the ValidationRecord from the already-sealed JSON files (reads NO
held-out data), then re-invokes write_sealed_record with reviewer + approval_status.
validation_id and results_digest are invariant; only reviewer, approval_status,
timestamp (preserved from the original), and combined_hash change.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.msi.msrp.validation import DomainResult, ValidationRecord, write_sealed_record

VALIDATIONS_DIR = ROOT / "core" / "msi" / "validations"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validation-id", required=True)
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--approval-status", required=True)
    args = ap.parse_args()

    d = VALIDATIONS_DIR / args.validation_id
    record_j = json.loads((d / "record.json").read_text())
    results_j = json.loads((d / "results.json").read_text())
    methodology_j = json.loads((d / "methodology.json").read_text())

    domains = tuple(
        DomainResult(name=x["name"], status=x["status"], evidence=x["evidence"])
        for x in results_j["domains"]
    )
    record = ValidationRecord(
        validation_id=record_j["validation_id"],
        phase=record_j["phase"],
        candidate_verdict=record_j["candidate_verdict"],
        domain_results=domains,
        results=results_j["results"],
        methodology=methodology_j,
        results_digest=record_j["results_digest"],
        artifact_version=record_j["artifact_version"],
        artifact_checksum=record_j["artifact_checksum"],
        dataset_snapshot_hash=record_j["dataset_snapshot_hash"],
    )
    out = write_sealed_record(
        record, VALIDATIONS_DIR,
        reviewer=args.reviewer, approval_status=args.approval_status,
        timestamp_iso=record_j["timestamp"],
    )
    reread = json.loads((out / "record.json").read_text())
    assert reread["validation_id"] == record_j["validation_id"]
    assert reread["results_digest"] == record_j["results_digest"]
    assert reread["reviewer"] == args.reviewer
    assert reread["approval_status"] == args.approval_status
    print(f"re-sealed {out} reviewer={args.reviewer} status={args.approval_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run the re-seal (only if the six checks PASS)**

Run (substitute the `<validation_id>` from Task 5):
```bash
python scripts/msrp/seal_phase6_attestation.py \
  --validation-id <validation_id> --reviewer "Phase-6 attestation" --approval-status attested
```
Expected: prints `re-sealed core/msi/validations/<validation_id> reviewer=Phase-6 attestation status=attested`; the internal asserts confirm `validation_id` + `results_digest` unchanged.

- [ ] **Step 4: Confirm the re-sealed record is checksum-valid**

Run (substitute the `<validation_id>`):
```bash
python -c "import json,hashlib,pathlib; d=pathlib.Path('core/msi/validations/<validation_id>'); c=json.loads((d/'checksum.sha256').read_text()); print('OK' if all(hashlib.sha256((d/f).read_bytes()).hexdigest()==h for f,h in c['files'].items()) else 'MISMATCH')"
```
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/msrp/seal_phase6_attestation.py docs/implementation/msrp/reports/MSRP_PHASE6_REVIEW.md core/msi/validations/
git commit -m "feat(msrp): Phase 6 Task 6 — execution-attestation review + re-seal"
```

---

### Task 7: Phase-6 report + certification

**Files:**
- Create: `docs/implementation/msrp/reports/MSRP_PHASE6_REPORT.md`

- [ ] **Step 1: Author the report from the sealed record**

Transcribe from `core/msi/validations/<validation_id>/results.json` into `MSRP_PHASE6_REPORT.md`: the pinned substrate + `L` derivation summary; `delta_auc_gate` + 95% CI; `delta_auc_vix` + its CI; held-out `base_rate` + run structure; calibration coverage; the pinned sub-period split; the seven-domain PASS/FAIL/REPORTED table; and the §10-mapped verdict + next action. Include the execution-attestation result (Task 6) and the `validation_id`. Write this **regardless of outcome** — an Inconclusive verdict is an expected, non-failing result (dossier §11), not a failure to explain away.

- [ ] **Step 2: Commit**

```bash
git add docs/implementation/msrp/reports/MSRP_PHASE6_REPORT.md
git commit -m "docs(msrp): Phase 6 Task 7 — held-out scoring report + certification"
```

---

### Task 8: KB sync + tag

**Files:**
- Modify: `docs/PROJECT_STATE.md`, `docs/CHANGELOG_PLATFORM.md`

- [ ] **Step 1: Update PROJECT_STATE.md**

Add a new top `## Completed` entry dated 2026-07-07 summarizing Phase 6: pinned `L`, the one-shot official run, the seven-domain result, the §10 verdict + next action, the `validation_id`, and the report path. Update the `**Last updated:**` line.

- [ ] **Step 2: Update CHANGELOG_PLATFORM.md**

Add a Phase-6 entry mirroring the PROJECT_STATE summary.

- [ ] **Step 3: Commit and tag**

```bash
git add docs/PROJECT_STATE.md docs/CHANGELOG_PLATFORM.md
git commit -m "docs(msrp): Phase 6 — KB sync (PROJECT_STATE + CHANGELOG)"
git tag msrp-phase6-complete
```

---

## Self-Review

**Spec coverage:**
- Design §2 (pin `L`, rule + fallback) → Task 1 (fallback lives in the script's `if L is None` branch).
- Design §3 Stage 1 (pre-flight 1.1–1.5) → Tasks 1 (`L`), 2 (seal/provenance), 3 (rehearsal), 4 (go/no-go gate).
- Design §4 Stage 2 (one-shot official run) → Task 5.
- Design §5.1 (attestation review + re-seal mechanism) → Task 6 (six checks + `seal_phase6_attestation.py`, re-invoking `write_sealed_record`, `validation_id`/`results_digest` invariant asserted).
- Design §5.2 (report + certification) → Task 7. Design §5.3 (KB sync + tag) → Task 8.
- Design §6 (all four §10 outcomes) → Task 6 Step 1 check 5 + Task 7 Step 1.
- Design §9 risks (early seal read, `L` hindsight, duplicate, favorable reinterpretation, silent domain skip) → dev-only loader (Task 1), fixed rule (Task 1), duplicate guard + check 2 (Tasks 5/6), §10 mapping check (Task 6), seven-domain check (Task 6).

**Placeholder scan:** `<L>`, `<k>`, `<validation_id>` are runtime values produced by earlier steps, substituted at execution — not unresolved TODOs. All code blocks are complete and runnable.

**Type consistency:** `compute_daily_rv` signature matches `validation_scoring.py`. `ValidationRecord`/`DomainResult`/`write_sealed_record` field names and the `write_sealed_record(record, out_root, reviewer, approval_status, timestamp_iso)` signature match `validation.py`. `results.json` shape (`{"results": {...}, "domains": [{"name","status","evidence"}]}`) and `record.json` keys (`validation_id`, `phase`, `candidate_verdict`, `domain_verdicts`, `results_digest`, `timestamp`, `reviewer`, `approval_status`, `artifact_version`, `artifact_checksum`, `dataset_snapshot_hash`) match `write_sealed_record`.
