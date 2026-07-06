# MSRP Phase 5B — A2 Validation Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic MSI-006 A2 Validation Harness that validates the certified `ForwardVolatilityArtifact` across the seven MSI-006 domains and assembles one checksum-sealed, immutable validation record — built and verified on dev/synthetic data only (the held-out scoring run is a separate Phase 6 act).

**Architecture:** A `ValidationHarness` class holds immutable execution state and exposes seven `_evaluate_<domain>()` methods + a `run()` aggregator. A pure scoring module produces per-day discriminant scores by calling the frozen artifact's `evaluate()` directly (not the DRA `KnowledgeObject` wrapper). A pure statistics module provides ROC-AUC and the moving-block-bootstrap ΔAUC CI. Record I/O writes a checksum-sealed directory keyed by a content-addressed `validation_id`.

**Tech Stack:** Python 3.10+, numpy, pandas, duckdb, pytest. Reuses certified MSI v1.0 components (`FilesystemArtifactLoader`, the frozen artifact) and existing `core/msi/msrp/forward_vol.py` feature functions.

**Governing documents:**
- Design spec: `docs/implementation/msrp/reports/MSRP_PHASE5B_A2_DESIGN_SPEC.md` (the contract this plan implements — read it first).
- Frozen pre-registration: `docs/reports/MSRP_PHASE1_RESEARCH_DOSSIER.md` (§3 head-to-head, §3.4 decision rule, §1.1 substrate).
- `docs/architecture/market_state_intelligence/MSI_006_VALIDATION_FRAMEWORK.md` (seven domains, §7 record fields, MSI-6D-05).

## Global Constraints

- **Additive only.** No modification to any frozen component: `core/msi/contracts/*`, `core/msi/interfaces/*`, `core/msi/dra/*`, `core/msi/artifacts/forward_vol_v2/*`, `core/msi/msrp/forward_vol.py`, the dossier, or any MSI spec. New files only, plus new test files.
- **No `core/` → `tests/` dependency.** The harness hardcodes the VIX gate thresholds; it never imports the `tests/` fixture.
- **Held-out window is sealed.** No test or script in this plan reads `2026-01-01 → 2026-07-03`. All verification uses the dev window (`2023-01-02 → 2025-12-31`) or synthetic data. The held-out run is Phase 6, out of scope here.
- **Determinism.** The only stochastic element is the moving-block bootstrap; it takes an explicit integer seed. Same inputs + same `harness_version` ⇒ byte-identical `results_digest` and `validation_id`.
- **Frozen artifact evidence field names** (verbatim): `rv_daily`, `rv_weekly`, `rv_monthly`, `vix_close`. Required symbols: `NSE_INDEX|Nifty 50`, `NSE_INDEX|India VIX`.
- **VIX gate rule** (verbatim): regime `0` if `vix < 15`, `1` if `15 <= vix < 25`, `2` if `vix >= 25`.
- **Label** (verbatim): `Y_t = 1[RV_{t+1} > M_t]`, `M_t` = trailing-20-trading-day median of `RV` inclusive of day `t`.
- **`results_digest` float formatting:** fixed 6 decimal places, canonical JSON (sorted keys).
- **`validation_id` preimage** (verbatim, §5.1): `{artifact_version, artifact_checksum, dataset_snapshot_hash, methodology_fingerprint, harness_version}`. `methodology_fingerprint` excludes `harness_version`.
- **`HARNESS_VERSION`** starts at `"1.0.0"`; must be bumped on any behavior-affecting change (process obligation, no CI guard).

---

## File Structure

| File | Responsibility |
|------|----------------|
| `core/msi/msrp/validation_stats.py` | Pure numeric primitives: ROC-AUC, moving-block-bootstrap ΔAUC CI, canonical-JSON + 6dp float formatting, sha256 helpers. No I/O, no MSI imports. |
| `core/msi/msrp/validation_scoring.py` | `ScoredWindow` DTO + `score_window(...)`: builds per-day Evidence, calls `artifact.evaluate()` directly, returns per-day `s_cand`, `s_fix`, `s_vix`, `Y`, `dates`, `n_dropped_boundary`. |
| `core/msi/msrp/validation.py` | `Substrate`, `Methodology`, `DomainResult`, `ValidationRecord` DTOs; `ValidationHarness` (seven domain methods + `_score`, `_delta_auc_ci`, `run`); `validation_id`, `results_digest`, `write_sealed_record`. |
| `scripts/msrp/run_forward_vol_validation.py` | Phase-6 composition root: wires loader + scoring + substrate, enforces the phase-6 duplicate guardrail, writes the sealed record dir. Exercised in 5B only on dev/synthetic. |
| `tests/msi/msrp/test_validation_stats.py` | Task-1 unit tests. |
| `tests/msi/msrp/test_validation_scoring.py` | Task-2 unit tests. |
| `tests/msi/msrp/test_forward_vol_validation.py` | Harness verification: domains, aggregator, id/digest determinism, checksum seal, phase guard, two-instance reproducibility. |
| `core/msi/validations/.gitkeep` | Ensures the sealed-record output directory exists in the tree. |

---

### Task 1: Statistical primitives (`validation_stats.py`)

**Files:**
- Create: `core/msi/msrp/validation_stats.py`
- Test: `tests/msi/msrp/test_validation_stats.py`

**Interfaces:**
- Consumes: numpy only.
- Produces:
  - `roc_auc(scores: np.ndarray, labels: np.ndarray) -> float` — rank-based AUC with tie handling; returns `float('nan')` if labels are single-class.
  - `moving_block_bootstrap_delta_auc_ci(cand, ref, labels, block_length, n_replicates, seed, alpha=0.05) -> tuple[float, float]` — (lower, upper) percentile CI of `AUC(cand)-AUC(ref)`.
  - `canonical_json(obj) -> str` — sorted-keys JSON.
  - `format_6dp(x: float) -> float` — 6-decimal rounding.
  - `sha256_hex(s: str) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/msi/msrp/test_validation_stats.py
import numpy as np
import pytest

from core.msi.msrp.validation_stats import (
    roc_auc,
    moving_block_bootstrap_delta_auc_ci,
    canonical_json,
    format_6dp,
    sha256_hex,
)


def test_roc_auc_perfect_separation():
    assert roc_auc(np.array([0.1, 0.2, 0.8, 0.9]), np.array([0, 0, 1, 1])) == pytest.approx(1.0)


def test_roc_auc_inverted_is_zero():
    assert roc_auc(np.array([0.9, 0.8, 0.2, 0.1]), np.array([0, 0, 1, 1])) == pytest.approx(0.0)


def test_roc_auc_ties_average():
    assert roc_auc(np.array([0.5, 0.5, 0.5, 0.5]), np.array([0, 1, 0, 1])) == pytest.approx(0.5)


def test_roc_auc_single_class_is_nan():
    assert np.isnan(roc_auc(np.array([0.1, 0.2]), np.array([1, 1])))


def test_bootstrap_ci_is_deterministic_under_seed():
    rng = np.random.default_rng(0)
    n = 120
    cand = rng.normal(size=n)
    labels = (cand + rng.normal(size=n) > 0).astype(int)
    ref = rng.normal(size=n)
    ci_a = moving_block_bootstrap_delta_auc_ci(cand, ref, labels, 10, 500, seed=42)
    ci_b = moving_block_bootstrap_delta_auc_ci(cand, ref, labels, 10, 500, seed=42)
    assert ci_a == ci_b
    assert ci_a[0] <= ci_a[1]


def test_format_6dp_and_canonical_json():
    assert format_6dp(0.1234567) == 0.123457
    assert canonical_json({"b": format_6dp(1 / 3), "a": 2}) == '{"a": 2, "b": 0.333333}'


def test_sha256_hex_stable():
    assert sha256_hex("abc") == sha256_hex("abc")
    assert len(sha256_hex("abc")) == 64
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/msi/msrp/test_validation_stats.py -v`
Expected: FAIL with `ModuleNotFoundError: core.msi.msrp.validation_stats`.

- [ ] **Step 3: Write minimal implementation**

```python
# core/msi/msrp/validation_stats.py
"""Pure numeric primitives for the A2 Validation Harness.

No I/O and no MSI imports — deterministic functions only. ROC-AUC is rank-based
(Mann-Whitney U form) with average-rank tie handling; the moving-block bootstrap
resamples contiguous day-blocks to respect the autocorrelated label (dossier §8,
Phase-2 finding M2).
"""

import hashlib
import json
from typing import Tuple

import numpy as np


def roc_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    n_pos = int(np.sum(labels == 1))
    n_neg = int(np.sum(labels == 0))
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    ranks = np.empty(len(scores), dtype=float)
    i = 0
    while i < len(sorted_scores):
        j = i
        while j + 1 < len(sorted_scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # ranks are 1-based
        ranks[order[i : j + 1]] = avg_rank
        i = j + 1
    sum_ranks_pos = float(np.sum(ranks[labels == 1]))
    auc = (sum_ranks_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def _delta_auc(cand: np.ndarray, ref: np.ndarray, labels: np.ndarray) -> float:
    return roc_auc(cand, labels) - roc_auc(ref, labels)


def moving_block_bootstrap_delta_auc_ci(
    cand: np.ndarray,
    ref: np.ndarray,
    labels: np.ndarray,
    block_length: int,
    n_replicates: int,
    seed: int,
    alpha: float = 0.05,
) -> Tuple[float, float]:
    cand = np.asarray(cand, dtype=float)
    ref = np.asarray(ref, dtype=float)
    labels = np.asarray(labels, dtype=int)
    n = len(labels)
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block_length))
    max_start = n - block_length
    deltas = np.empty(n_replicates, dtype=float)
    filled = 0
    for _ in range(n_replicates):
        starts = rng.integers(0, max_start + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block_length) for s in starts])[:n]
        d = _delta_auc(cand[idx], ref[idx], labels[idx])
        if not np.isnan(d):
            deltas[filled] = d
            filled += 1
    deltas = deltas[:filled]
    lower = float(np.percentile(deltas, 100 * (alpha / 2)))
    upper = float(np.percentile(deltas, 100 * (1 - alpha / 2)))
    return (lower, upper)


def format_6dp(x: float) -> float:
    return float(f"{float(x):.6f}")


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(", ", ": "))


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/msi/msrp/test_validation_stats.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add core/msi/msrp/validation_stats.py tests/msi/msrp/test_validation_stats.py
git commit -m "feat(msrp): A2 harness statistical primitives (AUC, MBB CI, digest helpers)"
```

---

### Task 2: Per-day scoring pipeline (`validation_scoring.py`)

**Files:**
- Create: `core/msi/msrp/validation_scoring.py`
- Test: `tests/msi/msrp/test_validation_scoring.py`

**Interfaces:**
- Consumes: `core.msi.msrp.forward_vol.compute_daily_rv`, `compute_har_features`; `core.msi.contracts.evidence.Evidence`; a loaded artifact with `.evaluate()`.
- Produces:
  - `@dataclass(frozen=True) ScoredWindow(dates: tuple[str, ...], s_cand: np.ndarray, s_fix: np.ndarray, s_vix: np.ndarray, y: np.ndarray, n_dropped_boundary: int, requested_window: tuple[str, str])`.
  - `vix_regime(vix: float) -> int` — the hardcoded 15/25 gate.
  - `build_day_evidence(rv_daily, rv_weekly, rv_monthly, vix, as_of) -> tuple[Evidence, ...]`.
  - `score_window(artifact, closes_by_day: dict, vix_series, window_start: str, window_end: str, warmup_days: int = 22) -> ScoredWindow`.

**Note on data loading:** `score_window` takes already-loaded `closes_by_day` (dict[day → 1m close array]) and `vix_series` so it is pure and unit-testable with synthetic data. The composition root (Task 6) does the DuckDB loading.

- [ ] **Step 1: Write the failing test**

```python
# tests/msi/msrp/test_validation_scoring.py
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from core.msi.msrp.validation_scoring import (
    ScoredWindow,
    vix_regime,
    build_day_evidence,
    score_window,
)


def test_vix_regime_thresholds():
    assert vix_regime(14.9) == 0
    assert vix_regime(15.0) == 1
    assert vix_regime(24.9) == 1
    assert vix_regime(25.0) == 2


def test_build_day_evidence_has_four_named_features():
    ev = build_day_evidence(0.01, 0.011, 0.012, 13.0, datetime(2024, 3, 1))
    assert {e.evidence_type for e in ev} == {"rv_daily", "rv_weekly", "rv_monthly", "vix_close"}
    assert all(e.artifact_version == "v1.0.0" for e in ev)


def _synthetic_inputs(n_days=60):
    rng = np.random.default_rng(7)
    days = pd.bdate_range("2024-01-01", periods=n_days)
    closes_by_day = {}
    for d in days:
        base = 20000 + 100 * np.sin(d.dayofyear)
        closes_by_day[pd.Timestamp(d).normalize()] = base + rng.normal(0, 5, size=90).cumsum()
    vix = pd.Series(15 + 5 * np.cos(np.arange(n_days)), index=days, name="vix")
    return closes_by_day, vix


def test_score_window_shapes_and_boundary_drop():
    from core.msi.dra.filesystem_artifact_loader import FilesystemArtifactLoader
    root = Path(__file__).resolve().parents[3]
    artifact = FilesystemArtifactLoader().load(
        str(root / "core" / "msi" / "artifacts" / "forward_vol_v2")
    )
    closes_by_day, vix = _synthetic_inputs(60)
    sw = score_window(artifact, closes_by_day, vix, "2024-02-15", "2024-03-22", warmup_days=22)
    assert isinstance(sw, ScoredWindow)
    n = len(sw.dates)
    assert n > 0
    assert sw.s_cand.shape == sw.s_fix.shape == sw.s_vix.shape == sw.y.shape == (n,)
    assert sw.s_unc.shape == sw.rv_next.shape == (n,)
    assert np.all(sw.s_unc >= 0) and np.all(sw.rv_next > 0)
    assert set(np.unique(sw.y)).issubset({0, 1})
    assert sw.n_dropped_boundary >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/msi/msrp/test_validation_scoring.py -v`
Expected: FAIL with `ModuleNotFoundError: core.msi.msrp.validation_scoring`.

- [ ] **Step 3: Write minimal implementation**

```python
# core/msi/msrp/validation_scoring.py
"""Per-day discriminant scoring for the A2 Validation Harness (dossier §3).

Computes s_cand (frozen artifact's expected_next_day_realized_vol via a DIRECT
evaluate() call — not the DRA KnowledgeObject wrapper), s_fix (hardcoded VIX gate),
s_vix (raw VIX), and the label Y = 1[RV_{t+1} > trailing-20d median]. Pure over the
supplied closes_by_day / vix_series so it is unit-testable on synthetic data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from core.msi.contracts.evidence import Evidence
from core.msi.msrp.forward_vol import compute_daily_rv, compute_har_features

MEDIAN_WINDOW = 20  # trailing-20-trading-day median (dossier §3.1)


@dataclass(frozen=True)
class ScoredWindow:
    dates: Tuple[str, ...]
    s_cand: np.ndarray       # predicted E[RV_{t+1}] (estimate value)
    s_fix: np.ndarray
    s_vix: np.ndarray
    y: np.ndarray
    s_unc: np.ndarray        # predicted uncertainty (estimate.uncertainty) — for calibration
    rv_next: np.ndarray      # actual RV_{t+1} — for calibration coverage
    n_dropped_boundary: int
    requested_window: Tuple[str, str]


def vix_regime(vix: float) -> int:
    if vix < 15.0:
        return 0
    if vix < 25.0:
        return 1
    return 2


def build_day_evidence(
    rv_daily: float, rv_weekly: float, rv_monthly: float, vix: float, as_of: datetime
) -> Tuple[Evidence, ...]:
    fields = [
        ("rv_daily", rv_daily),
        ("rv_weekly", rv_weekly),
        ("rv_monthly", rv_monthly),
        ("vix_close", vix),
    ]
    return tuple(
        Evidence(
            evidence_id=f"{name}|{as_of.isoformat()}",
            source_observation_ids=(),
            construction_timestamp=as_of,
            evidence_type=name,
            evidence_value=float(value),
            artifact_version="v1.0.0",
            provenance_metadata={},
            quality_metadata={},
            version="1.0",
        )
        for name, value in fields
    )


def score_window(
    artifact,
    closes_by_day: Dict[pd.Timestamp, np.ndarray],
    vix_series: pd.Series,
    window_start: str,
    window_end: str,
    warmup_days: int = 22,
) -> ScoredWindow:
    rv = compute_daily_rv(closes_by_day)
    feats = compute_har_features(rv)  # rv_daily / rv_weekly / rv_monthly, warmup-trimmed
    vix = vix_series.copy()
    vix.index = pd.DatetimeIndex([pd.Timestamp(d).normalize() for d in vix.index])

    ws = pd.Timestamp(window_start)
    we = pd.Timestamp(window_end)

    med = rv.rolling(window=MEDIAN_WINDOW, min_periods=MEDIAN_WINDOW).median()  # trailing 20d
    rv_next = rv.shift(-1)  # RV_{t+1}

    dates, s_cand, s_fix, s_vix, y, s_unc, rvn = [], [], [], [], [], [], []
    n_dropped = 0
    for t in feats.index:
        if t < ws or t > we:
            continue
        if t not in vix.index or pd.isna(med.get(t, np.nan)):
            continue
        rvt_next = rv_next.get(t, np.nan)
        if pd.isna(rvt_next):
            n_dropped += 1  # boundary day: no t+1 in snapshot -> unscorable, recorded
            continue
        row = feats.loc[t]
        vix_t = float(vix.loc[t])
        ev = build_day_evidence(
            float(row["rv_daily"]), float(row["rv_weekly"]), float(row["rv_monthly"]),
            vix_t, t.to_pydatetime(),
        )
        ms = artifact.evaluate(ev)
        dates.append(t.date().isoformat())
        s_cand.append(float(ms.estimates[0].value))
        s_unc.append(float(ms.estimates[0].uncertainty))
        s_fix.append(float(vix_regime(vix_t)))
        s_vix.append(vix_t)
        rvn.append(float(rvt_next))
        y.append(1 if float(rvt_next) > float(med.loc[t]) else 0)

    return ScoredWindow(
        dates=tuple(dates),
        s_cand=np.array(s_cand, dtype=float),
        s_fix=np.array(s_fix, dtype=float),
        s_vix=np.array(s_vix, dtype=float),
        y=np.array(y, dtype=int),
        s_unc=np.array(s_unc, dtype=float),
        rv_next=np.array(rvn, dtype=float),
        n_dropped_boundary=n_dropped,
        requested_window=(window_start, window_end),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/msi/msrp/test_validation_scoring.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add core/msi/msrp/validation_scoring.py tests/msi/msrp/test_validation_scoring.py
git commit -m "feat(msrp): A2 harness per-day scoring pipeline (direct evaluate path)"
```

---

### Task 3: DTOs + `ValidationHarness` core (`validation.py`, part 1)

**Files:**
- Create: `core/msi/msrp/validation.py`
- Test: `tests/msi/msrp/test_forward_vol_validation.py`

**Interfaces:**
- Consumes: `ScoredWindow`, `validation_stats.*`.
- Produces: `HARNESS_VERSION`, `Substrate`, `Methodology`, `DomainResult`, `ValidationRecord`, `ValidationHarness.__init__` + `_delta_auc_ci`, `methodology_fingerprint`, `results_digest`.

- [ ] **Step 1: Write the failing test**

```python
# tests/msi/msrp/test_forward_vol_validation.py
import numpy as np

from core.msi.msrp.validation import (
    HARNESS_VERSION,
    Substrate,
    Methodology,
    ValidationHarness,
    methodology_fingerprint,
    results_digest,
)
from core.msi.msrp.validation_scoring import ScoredWindow


def _methodology():
    return Methodology(
        substrate=Substrate(
            block_length=10, n_replicates=500, seed=42,
            lib_versions={"numpy": "x", "pandas": "y"}, commit="deadbeef",
        ),
        median_window=20, delta_auc_bar=0.03, dossier_commit="d9233b1",
        calibration_nominal=0.90, calibration_tolerance=0.05,
    )


def _scored(sep=True, n=120, seed=0):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) > 0.5).astype(int)
    base = 0.3 * y if sep else np.zeros(n)
    s_cand = np.exp(base + rng.normal(0, 0.2, n))     # positive predicted RV
    s_unc = s_cand * 0.3                               # positive uncertainty
    rv_next = np.exp(rng.normal(-3.0, 0.3, n))         # positive actual RV_{t+1}
    return ScoredWindow(
        dates=tuple(f"2024-01-{i % 28 + 1:02d}" for i in range(n)),
        s_cand=s_cand, s_fix=rng.normal(0, 1, n), s_vix=rng.normal(15, 3, n), y=y,
        s_unc=s_unc, rv_next=rv_next,
        n_dropped_boundary=1, requested_window=("2024-01-01", "2024-06-30"),
    )


def _harness(scored):
    return ValidationHarness(
        artifact=None, methodology=_methodology(), scored=scored,
        evaluation_window=("2024-01-01", "2024-06-30"), phase="5B",
        artifact_checksum="artifactsum", dataset_snapshot_hash="datasetsum",
    )


def test_methodology_fingerprint_excludes_harness_version():
    fp = methodology_fingerprint(_methodology())
    assert isinstance(fp, str) and len(fp) == 64
    assert HARNESS_VERSION not in fp


def test_delta_auc_ci_is_shared_and_deterministic():
    h = _harness(_scored())
    ci_a = h._delta_auc_ci()
    ci_b = h._delta_auc_ci()
    assert ci_a == ci_b
    assert ci_a[0] <= ci_a[1]


def test_results_digest_is_stable_and_6dp():
    r = {"delta_auc_gate": 1 / 3, "domain_verdicts": {"scientific": "PASS"}}
    assert results_digest(r) == results_digest(r)
    assert len(results_digest(r)) == 64
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/msi/msrp/test_forward_vol_validation.py -v`
Expected: FAIL with `ModuleNotFoundError: core.msi.msrp.validation`.

- [ ] **Step 3: Write minimal implementation**

```python
# core/msi/msrp/validation.py  (part 1 of 3 — DTOs, digests, shared CI)
"""MSI-006 A2 Validation Harness for the ForwardVolatilityArtifact.

Deterministic, additive. Executes the frozen Phase-1 dossier's seven-domain
validation and assembles one immutable, checksum-sealed record. See
docs/implementation/msrp/reports/MSRP_PHASE5B_A2_DESIGN_SPEC.md.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

from core.msi.msrp.validation_scoring import ScoredWindow
from core.msi.msrp.validation_stats import (
    canonical_json,
    format_6dp,
    moving_block_bootstrap_delta_auc_ci,
    roc_auc,
    sha256_hex,
)

HARNESS_VERSION = "1.0.0"


@dataclass(frozen=True)
class Substrate:
    block_length: int
    n_replicates: int
    seed: int
    lib_versions: Dict[str, str]
    commit: str


@dataclass(frozen=True)
class Methodology:
    substrate: Substrate
    median_window: int
    delta_auc_bar: float
    dossier_commit: str
    calibration_nominal: float
    calibration_tolerance: float


@dataclass(frozen=True)
class DomainResult:
    name: str
    status: str  # "PASS" | "FAIL" | "REPORTED"
    evidence: Dict[str, object]


@dataclass(frozen=True)
class ValidationRecord:
    validation_id: str
    phase: str
    candidate_verdict: str
    domain_results: Tuple[DomainResult, ...]
    results: Dict[str, object]
    methodology: Dict[str, object]
    results_digest: str
    artifact_version: str
    artifact_checksum: str
    dataset_snapshot_hash: str


def methodology_fingerprint(methodology: Methodology) -> str:
    payload = {
        "substrate": {
            "block_length": methodology.substrate.block_length,
            "n_replicates": methodology.substrate.n_replicates,
            "seed": methodology.substrate.seed,
            "lib_versions": methodology.substrate.lib_versions,
            "commit": methodology.substrate.commit,
        },
        "median_window": methodology.median_window,
        "delta_auc_bar": methodology.delta_auc_bar,
        "dossier_commit": methodology.dossier_commit,
        "calibration_nominal": methodology.calibration_nominal,
        "calibration_tolerance": methodology.calibration_tolerance,
    }
    # harness_version deliberately excluded (design spec §5.1b)
    return sha256_hex(canonical_json(payload))


def _round_results(results: Dict[str, object]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for k, v in results.items():
        if isinstance(v, float):
            out[k] = format_6dp(v)
        elif isinstance(v, dict):
            out[k] = _round_results(v)
        elif isinstance(v, (list, tuple)):
            out[k] = [format_6dp(x) if isinstance(x, float) else x for x in v]
        else:
            out[k] = v
    return out


def results_digest(results: Dict[str, object]) -> str:
    return sha256_hex(canonical_json(_round_results(results)))


class ValidationHarness:
    def __init__(
        self,
        artifact,
        methodology: Methodology,
        scored: ScoredWindow,
        evaluation_window: Tuple[str, str],
        phase: str,
        artifact_checksum: str,
        dataset_snapshot_hash: str,
    ):
        self._artifact = artifact
        self._methodology = methodology
        self._scored = scored
        self._evaluation_window = evaluation_window
        self._phase = phase
        self._artifact_checksum = artifact_checksum
        self._dataset_snapshot_hash = dataset_snapshot_hash

    def _delta_auc_ci(self) -> Tuple[float, float]:
        s = self._scored
        m = self._methodology.substrate
        return moving_block_bootstrap_delta_auc_ci(
            s.s_cand, s.s_fix, s.y,
            block_length=m.block_length, n_replicates=m.n_replicates, seed=m.seed,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/msi/msrp/test_forward_vol_validation.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add core/msi/msrp/validation.py tests/msi/msrp/test_forward_vol_validation.py
git commit -m "feat(msrp): A2 harness DTOs, digests, shared bootstrap CI"
```

---

### Task 4: The seven domain methods + `run()` aggregator (`validation.py`, part 2)

**Files:**
- Modify: `core/msi/msrp/validation.py` (add methods to `ValidationHarness`)
- Test: `tests/msi/msrp/test_forward_vol_validation.py` (append)

**Interfaces:**
- Produces on `ValidationHarness`: `_score() -> dict`, `_evaluate_architectural/scientific/temporal/robustness/operational/calibration/reproducibility() -> DomainResult`, `run() -> ValidationRecord`, `validation_id() -> str`.

**Decision rule (dossier §3.4):** Scientific PASS iff `delta_auc_gate >= delta_auc_bar` AND CI lower bound `> 0`. Aggregator: any mandatory `FAIL` ⇒ `candidate_verdict = "Rejected"`; else `"Approved (candidate)"`. `REPORTED` never gates. Mandatory PASS/FAIL: Architectural, Scientific, Temporal, Operational, Calibration, Reproducibility. Robustness is `REPORTED`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/msi/msrp/test_forward_vol_validation.py

def test_scientific_pass_on_separated_scores():
    dr = _harness(_scored(sep=True))._evaluate_scientific()
    assert dr.name == "scientific" and dr.status == "PASS"
    assert dr.evidence["delta_auc_gate"] >= 0.03


def test_scientific_fail_on_noise():
    assert _harness(_scored(sep=False))._evaluate_scientific().status == "FAIL"


def test_robustness_is_reported_only():
    dr = _harness(_scored())._evaluate_robustness()
    assert dr.status == "REPORTED"
    assert "subperiod_first_half_delta_auc_gate" in dr.evidence


def test_temporal_records_window_and_boundary_drop():
    dr = _harness(_scored())._evaluate_temporal()
    assert dr.evidence["evaluation_window"] == ["2024-01-01", "2024-06-30"]
    assert dr.evidence["n_dropped_boundary"] == 1


def test_calibration_reports_coverage_and_gates():
    # rv_next drawn from the artifact-implied log-normal -> coverage ~= nominal -> PASS
    rng = np.random.default_rng(3)
    n = 300
    mu = rng.normal(-3.0, 0.2, n)
    sig = 0.27
    value = np.exp(mu + sig ** 2 / 2)
    unc = value * np.sqrt(np.exp(sig ** 2) - 1)
    rv_next = np.exp(mu + rng.normal(0, sig, n))
    sw = ScoredWindow(
        dates=tuple(str(i) for i in range(n)),
        s_cand=value, s_fix=rng.normal(0, 1, n), s_vix=rng.normal(15, 3, n),
        y=(rng.random(n) > 0.5).astype(int), s_unc=unc, rv_next=rv_next,
        n_dropped_boundary=0, requested_window=("2024-01-01", "2024-12-31"),
    )
    dr = _harness(sw)._evaluate_calibration()
    assert dr.name == "calibration" and dr.status == "PASS"
    assert dr.evidence["nominal"] == 0.90
    assert 0.85 <= dr.evidence["empirical_coverage"] <= 0.95


def test_run_produces_record_with_conjunctive_verdict():
    rec = _harness(_scored(sep=False)).run()
    assert rec.candidate_verdict == "Rejected"
    assert rec.phase == "5B"
    assert len(rec.validation_id) == 64
    assert rec.results_digest == results_digest(rec.results)


def test_validation_id_excludes_results():
    h1 = _harness(_scored(sep=True, seed=1))
    h2 = _harness(_scored(sep=False, seed=2))
    assert h1.validation_id() == h2.validation_id()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/msi/msrp/test_forward_vol_validation.py -v`
Expected: FAIL with `AttributeError: 'ValidationHarness' object has no attribute '_evaluate_scientific'`.

- [ ] **Step 3: Write minimal implementation**

Append these methods to `ValidationHarness` in `core/msi/msrp/validation.py`:

```python
    # --- scoring (recursion-free; used by Domains 5/6 double-run) -------------
    def _score(self) -> Dict[str, object]:
        s = self._scored
        auc_cand = roc_auc(s.s_cand, s.y)
        auc_fix = roc_auc(s.s_fix, s.y)
        auc_vix = roc_auc(s.s_vix, s.y)
        ci_low, ci_high = self._delta_auc_ci()
        n = len(s.y)
        half = (n + 1) // 2  # ceil(n/2); the earlier half takes the odd extra day (spec §4.4)

        def _dg(lo, hi):
            yy = s.y[lo:hi]
            if len(set(yy.tolist())) < 2:
                return float("nan")
            return roc_auc(s.s_cand[lo:hi], yy) - roc_auc(s.s_fix[lo:hi], yy)

        return {
            "evaluation_window": list(self._evaluation_window),
            "auc_candidate": auc_cand,
            "auc_fixture": auc_fix,
            "auc_vix": auc_vix,
            "delta_auc_gate": auc_cand - auc_fix,
            "delta_auc_vix": auc_cand - auc_vix,
            "ci_lower": ci_low,
            "ci_upper": ci_high,
            "base_rate": float(np.mean(s.y)) if n else float("nan"),
            "n_scored": n,
            "n_dropped_boundary": s.n_dropped_boundary,
            "subperiod_first_half_delta_auc_gate": _dg(0, half),
            "subperiod_second_half_delta_auc_gate": _dg(half, n),
        }

    def _evaluate_architectural(self) -> DomainResult:
        art = self._artifact
        if art is None:
            return DomainResult("architectural", "PASS", {"skipped": "no artifact (unit ctx)"})
        names = [f["name"] for f in art.get_evidence_rules()["features"]]
        ok = names == ["rv_daily", "rv_weekly", "rv_monthly", "vix_close"]
        return DomainResult(
            "architectural", "PASS" if ok else "FAIL",
            {"feature_names": names, "artifact_version": art.metadata.artifact_version},
        )

    def _evaluate_scientific(self) -> DomainResult:
        r = self._score()
        passed = (r["delta_auc_gate"] >= self._methodology.delta_auc_bar) and (r["ci_lower"] > 0.0)
        return DomainResult(
            "scientific", "PASS" if passed else "FAIL",
            {k: r[k] for k in (
                "auc_candidate", "auc_fixture", "auc_vix", "delta_auc_gate",
                "delta_auc_vix", "ci_lower", "ci_upper", "base_rate",
            )},
        )

    def _evaluate_temporal(self) -> DomainResult:
        s = self._scored
        return DomainResult(
            "temporal", "PASS",
            {
                "evaluation_window": list(self._evaluation_window),
                "n_scored": len(s.y),
                "n_dropped_boundary": s.n_dropped_boundary,
                "note": "features as-of close of t; label uses RV_{t+1}; boundary drop recorded",
            },
        )

    def _evaluate_robustness(self) -> DomainResult:
        r = self._score()
        return DomainResult(
            "robustness", "REPORTED",
            {k: r[k] for k in (
                "ci_lower", "ci_upper", "base_rate",
                "subperiod_first_half_delta_auc_gate",
                "subperiod_second_half_delta_auc_gate",
            )},
        )

    def _evaluate_operational(self) -> DomainResult:
        ok = results_digest(self._score()) == results_digest(self._score())
        return DomainResult("operational", "PASS" if ok else "FAIL", {"score_repeatable": ok})

    def _evaluate_calibration(self) -> DomainResult:
        # Empirical coverage of the log-normal predictive interval reconstructed from
        # (value, uncertainty): s^2 = ln((unc/value)^2 + 1); mu = ln(value) - s^2/2;
        # PI = [exp(mu - z s), exp(mu + z s)]. Coverage = fraction of actual RV_{t+1}
        # inside. Mandatory domain (MSI-006 §7; dossier §9 finding Mo2). z from nominal.
        from scipy.stats import norm

        s = self._scored
        nominal = self._methodology.calibration_nominal
        tol = self._methodology.calibration_tolerance
        z = float(norm.ppf(1 - (1 - nominal) / 2))
        value, unc, rv_next = s.s_cand, s.s_unc, s.rv_next
        mask = (value > 0) & (unc > 0) & (rv_next > 0) & np.isfinite(rv_next)
        n_valid = int(np.sum(mask))
        if n_valid == 0:
            return DomainResult("calibration", "REPORTED",
                                {"note": "no valid days for coverage", "nominal": nominal})
        v, u, r = value[mask], unc[mask], rv_next[mask]
        s2 = np.log((u / v) ** 2 + 1.0)
        sig = np.sqrt(s2)
        mu = np.log(v) - s2 / 2.0
        inside = (r >= np.exp(mu - z * sig)) & (r <= np.exp(mu + z * sig))
        coverage = float(np.mean(inside))
        passed = abs(coverage - nominal) <= tol
        return DomainResult(
            "calibration", "PASS" if passed else "FAIL",
            {"nominal": nominal, "empirical_coverage": coverage,
             "tolerance": tol, "n_valid": n_valid},
        )

    def _evaluate_reproducibility(self) -> DomainResult:
        ok = results_digest(self._score()) == results_digest(self._score())
        return DomainResult(
            "reproducibility", "PASS" if ok else "FAIL",
            {
                "in_domain_double_run_equal": ok,
                "block_length": self._methodology.substrate.block_length,
                "n_replicates": self._methodology.substrate.n_replicates,
                "seed": self._methodology.substrate.seed,
            },
        )

    def validation_id(self) -> str:
        preimage = {
            "artifact_version": (
                self._artifact.metadata.artifact_version if self._artifact else "v1.0.0"
            ),
            "artifact_checksum": self._artifact_checksum,
            "dataset_snapshot_hash": self._dataset_snapshot_hash,
            "methodology_fingerprint": methodology_fingerprint(self._methodology),
            "harness_version": HARNESS_VERSION,
        }
        return sha256_hex(canonical_json(preimage))

    def run(self) -> ValidationRecord:
        domains = (
            self._evaluate_architectural(),
            self._evaluate_scientific(),
            self._evaluate_temporal(),
            self._evaluate_robustness(),
            self._evaluate_operational(),
            self._evaluate_calibration(),
            self._evaluate_reproducibility(),
        )
        verdict = "Rejected" if any(d.status == "FAIL" for d in domains) else "Approved (candidate)"
        results = self._score()
        results["domain_verdicts"] = {d.name: d.status for d in domains}
        methodology = {
            "harness_version": HARNESS_VERSION,
            "methodology_fingerprint": methodology_fingerprint(self._methodology),
            "substrate": {
                "block_length": self._methodology.substrate.block_length,
                "n_replicates": self._methodology.substrate.n_replicates,
                "seed": self._methodology.substrate.seed,
                "lib_versions": self._methodology.substrate.lib_versions,
                "commit": self._methodology.substrate.commit,
            },
            "median_window": self._methodology.median_window,
            "delta_auc_bar": self._methodology.delta_auc_bar,
            "dossier_commit": self._methodology.dossier_commit,
        }
        artifact_version = self._artifact.metadata.artifact_version if self._artifact else "v1.0.0"
        return ValidationRecord(
            validation_id=self.validation_id(),
            phase=self._phase,
            candidate_verdict=verdict,
            domain_results=domains,
            results=results,
            methodology=methodology,
            results_digest=results_digest(results),
            artifact_version=artifact_version,
            artifact_checksum=self._artifact_checksum,
            dataset_snapshot_hash=self._dataset_snapshot_hash,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/msi/msrp/test_forward_vol_validation.py -v`
Expected: PASS (Task 3 + Task 4 tests).

- [ ] **Step 5: Commit**

```bash
git add core/msi/msrp/validation.py tests/msi/msrp/test_forward_vol_validation.py
git commit -m "feat(msrp): A2 harness seven-domain methods + conjunctive run() aggregator"
```

---

### Task 5: Sealed-record I/O + `dataset_snapshot_hash` (`validation.py`, part 3)

**Files:**
- Modify: `core/msi/msrp/validation.py` (add record-writing + snapshot-hash functions)
- Create: `core/msi/validations/.gitkeep`
- Test: `tests/msi/msrp/test_forward_vol_validation.py` (append)

**Interfaces:**
- Produces (module-level): `dataset_snapshot_hash(files) -> str`; `write_sealed_record(record, out_root, reviewer, approval_status, timestamp_iso) -> Path`.
- In Phase 5B `reviewer`/`approval_status` are `None` (candidate); the Phase-6 review sets the final values (design spec §6).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/msi/msrp/test_forward_vol_validation.py
import hashlib
import json

from core.msi.msrp.validation import dataset_snapshot_hash, write_sealed_record


def test_dataset_snapshot_hash_is_sorted_and_scoped(tmp_path):
    a = tmp_path / "b.duckdb"; a.write_bytes(b"BB")
    b = tmp_path / "a.duckdb"; b.write_bytes(b"AA")
    assert dataset_snapshot_hash([a, b]) == dataset_snapshot_hash([b, a])
    assert len(dataset_snapshot_hash([a, b])) == 64


def test_write_sealed_record_roundtrip_and_checksum(tmp_path):
    rec = _harness(_scored(sep=True)).run()
    out = write_sealed_record(rec, tmp_path, reviewer=None, approval_status=None,
                              timestamp_iso="2026-07-06T00:00:00")
    assert out.name == rec.validation_id
    for fname in ("record.json", "methodology.json", "results.json", "checksum.sha256"):
        assert (out / fname).exists()
    checks = json.loads((out / "checksum.sha256").read_text())
    for fname, digest in checks["files"].items():
        assert hashlib.sha256((out / fname).read_bytes()).hexdigest() == digest
    rec_json = json.loads((out / "record.json").read_text())
    assert rec_json["phase"] == "5B"
    assert rec_json["results_digest"] == rec.results_digest
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/msi/msrp/test_forward_vol_validation.py -k "snapshot or sealed" -v`
Expected: FAIL with `ImportError: cannot import name 'dataset_snapshot_hash'`.

- [ ] **Step 3: Write minimal implementation**

Add these module-level functions to `core/msi/msrp/validation.py` (imports `hashlib`, `json`, `Path`, `Optional` already present from Task 3):

```python
def dataset_snapshot_hash(files) -> str:
    lines = []
    for p in files:
        p = Path(p)
        lines.append(f"{p.as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}")
    return sha256_hex("\n".join(sorted(lines)) + "\n")


def write_sealed_record(
    record: ValidationRecord,
    out_root,
    reviewer: Optional[str],
    approval_status: Optional[str],
    timestamp_iso: str,
) -> Path:
    out = Path(out_root) / record.validation_id
    out.mkdir(parents=True, exist_ok=True)

    results_obj = _round_results(record.results)
    record_obj = {
        "validation_id": record.validation_id,
        "phase": record.phase,
        "artifact_version": record.artifact_version,
        "artifact_checksum": record.artifact_checksum,
        "dataset_snapshot_hash": record.dataset_snapshot_hash,
        "candidate_verdict": record.candidate_verdict,
        "domain_verdicts": {d.name: d.status for d in record.domain_results},
        "results_digest": record.results_digest,
        "timestamp": timestamp_iso,
        "reviewer": reviewer,
        "approval_status": approval_status,
    }

    def _dump(name, obj):
        (out / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    _dump("results.json", {
        "results": results_obj,
        "domains": [
            {"name": d.name, "status": d.status, "evidence": _round_results(d.evidence)}
            for d in record.domain_results
        ],
    })
    _dump("methodology.json", record.methodology)
    _dump("record.json", record_obj)

    content_files = ["record.json", "methodology.json", "results.json"]
    file_hashes = {f: hashlib.sha256((out / f).read_bytes()).hexdigest() for f in content_files}
    combined = hashlib.sha256("".join(file_hashes[f] for f in content_files).encode()).hexdigest()
    _dump("checksum.sha256", {"algorithm": "sha256", "files": file_hashes, "combined_hash": combined})
    return out
```

Create `core/msi/validations/.gitkeep` (empty file).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/msi/msrp/test_forward_vol_validation.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add core/msi/msrp/validation.py core/msi/validations/.gitkeep tests/msi/msrp/test_forward_vol_validation.py
git commit -m "feat(msrp): A2 harness sealed-record I/O + dataset snapshot hash"
```

---

### Task 6: Composition root + phase guardrail + two-instance reproducibility

**Files:**
- Create: `scripts/msrp/run_forward_vol_validation.py`
- Test: `tests/msi/msrp/test_forward_vol_validation.py` (append)

**Interfaces:**
- Produces: `load_candles_over(window_start, window_end, warmup_days) -> tuple[dict, pd.Series, list[Path]]`; `phase6_guard(out_root, held_out_window) -> None` (raises `RuntimeError` on duplicate); `main(argv=None) -> int`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/msi/msrp/test_forward_vol_validation.py
import pytest as _pytest


def test_phase6_guard_blocks_duplicate(tmp_path):
    from scripts.msrp.run_forward_vol_validation import phase6_guard
    d = tmp_path / "someid"; d.mkdir()
    (d / "record.json").write_text(json.dumps({"phase": "6"}), encoding="utf-8")
    (d / "results.json").write_text(
        json.dumps({"results": {"evaluation_window": ["2026-01-01", "2026-07-03"]}}),
        encoding="utf-8",
    )
    with _pytest.raises(RuntimeError):
        phase6_guard(tmp_path, ("2026-01-01", "2026-07-03"))


def test_phase6_guard_allows_new_window(tmp_path):
    from scripts.msrp.run_forward_vol_validation import phase6_guard
    phase6_guard(tmp_path, ("2026-01-01", "2026-07-03"))  # no records -> no raise


def test_two_independent_instances_reproduce_digest():
    h1 = _harness(_scored(sep=True, seed=5))
    h2 = _harness(_scored(sep=True, seed=5))  # rebuilt from identical inputs
    assert h1.run().results_digest == h2.run().results_digest
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/msi/msrp/test_forward_vol_validation.py -k "guard or two_independent" -v`
Expected: FAIL with `ModuleNotFoundError: scripts.msrp.run_forward_vol_validation`.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/msrp/run_forward_vol_validation.py
"""Phase-6 composition root for the A2 Validation Harness (dossier §9).

Wires the certified FilesystemArtifactLoader + the frozen artifact + the pinned
substrate, scores an EXPLICIT window, and writes the sealed record. In Phase 5B this
is exercised only on dev/synthetic windows; the held-out run is Phase 6.

The evaluation window is a required CLI argument — NEVER hardcoded. The phase-6
duplicate guard prevents an accidental second official run over the same window.
"""

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.msi.dra.filesystem_artifact_loader import FilesystemArtifactLoader  # noqa: E402
from core.msi.msrp.validation import (  # noqa: E402
    Methodology,
    Substrate,
    ValidationHarness,
    dataset_snapshot_hash,
    write_sealed_record,
)
from core.msi.msrp.validation_scoring import score_window  # noqa: E402

NIFTY_50 = "NSE_INDEX|Nifty 50"
INDIA_VIX = "NSE_INDEX|India VIX"
CANDLES_1M = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
CANDLES_1D = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
ARTIFACT_DIR = ROOT / "core" / "msi" / "artifacts" / "forward_vol_v2"
VALIDATIONS_DIR = ROOT / "core" / "msi" / "validations"


def _iter_duckdb_days(root: Path, start: str, end: str):
    start_d = pd.Timestamp(start).date()
    end_d = pd.Timestamp(end).date()
    for f in sorted(root.glob("*.duckdb")):
        try:
            d = pd.Timestamp(f.stem).date()
        except ValueError:
            continue
        if start_d <= d <= end_d:
            yield f


def load_candles_over(window_start: str, window_end: str, warmup_days: int = 30):
    load_start = (pd.Timestamp(window_start) - pd.Timedelta(days=warmup_days * 2)).date().isoformat()
    load_end = (pd.Timestamp(window_end) + pd.Timedelta(days=7)).date().isoformat()
    files = []
    closes_by_day = {}
    for f in _iter_duckdb_days(CANDLES_1M, load_start, load_end):
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
        files.append(f)
        day = pd.Timestamp(rows[0][0]).normalize()
        closes_by_day[day] = np.array([float(r[1]) for r in rows], dtype=float)
    records = []
    for f in _iter_duckdb_days(CANDLES_1D, load_start, load_end):
        con = duckdb.connect(str(f), read_only=True)
        try:
            rows = con.execute(
                "SELECT timestamp, close FROM candles WHERE symbol = ?", [INDIA_VIX]
            ).fetchall()
        finally:
            con.close()
        if rows:
            files.append(f)
        for ts, close in rows:
            records.append((pd.Timestamp(ts).normalize(), float(close)))
    vix = pd.Series([r[1] for r in records],
                    index=pd.DatetimeIndex([r[0] for r in records]), name="vix")
    return closes_by_day, vix, files


def phase6_guard(out_root, held_out_window: Tuple[str, str]) -> None:
    out_root = Path(out_root)
    if not out_root.exists():
        return
    for d in out_root.iterdir():
        rec = d / "record.json"
        if not rec.exists():
            continue
        try:
            rj = json.loads(rec.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if rj.get("phase") != "6":
            continue
        window = None
        res = d / "results.json"
        if res.exists():
            try:
                window = json.loads(res.read_text())["results"]["evaluation_window"]
            except (json.JSONDecodeError, KeyError, OSError):
                window = None
        if window == list(held_out_window):
            raise RuntimeError(
                f"A phase-6 validation for window {held_out_window} already exists at {d}. "
                "Refusing to run a duplicate official validation."
            )


def _lib_versions() -> dict:
    import statsmodels
    import sklearn
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "statsmodels": statsmodels.__version__,
        "scikit-learn": sklearn.__version__,
    }


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT)).decode().strip()
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-start", required=True)
    ap.add_argument("--window-end", required=True)
    ap.add_argument("--phase", required=True, choices=["5B", "6"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--block-length", type=int, default=10)
    ap.add_argument("--replicates", type=int, default=10000)
    args = ap.parse_args(argv)

    window = (args.window_start, args.window_end)
    if args.phase == "6":
        phase6_guard(VALIDATIONS_DIR, window)

    artifact = FilesystemArtifactLoader().load(str(ARTIFACT_DIR))
    artifact_checksum = json.loads((ARTIFACT_DIR / "checksum.sha256").read_text())["combined_hash"]

    closes_by_day, vix, files = load_candles_over(args.window_start, args.window_end)
    snapshot_hash = dataset_snapshot_hash(files)
    scored = score_window(artifact, closes_by_day, vix, args.window_start, args.window_end)

    methodology = Methodology(
        substrate=Substrate(
            block_length=args.block_length, n_replicates=args.replicates, seed=args.seed,
            lib_versions=_lib_versions(),
            commit=_git_commit(),
        ),
        median_window=20, delta_auc_bar=0.03, dossier_commit="d9233b1",
        calibration_nominal=0.90, calibration_tolerance=0.05,
    )
    harness = ValidationHarness(
        artifact=artifact, methodology=methodology, scored=scored,
        evaluation_window=window, phase=args.phase,
        artifact_checksum=artifact_checksum, dataset_snapshot_hash=snapshot_hash,
    )
    record = harness.run()
    out = write_sealed_record(
        record, VALIDATIONS_DIR, reviewer=None, approval_status=None,
        timestamp_iso=datetime.now().isoformat(timespec="seconds"),
    )
    print(f"Validation {record.validation_id} ({record.candidate_verdict}) -> {out}")
    print(f"  delta_auc_gate={record.results['delta_auc_gate']:.6f} "
          f"CI=({record.results['ci_lower']:.6f}, {record.results['ci_upper']:.6f}) "
          f"base_rate={record.results['base_rate']:.6f} n={record.results['n_scored']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/msi/msrp/test_forward_vol_validation.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Smoke-run on the dev window (off-window, allowed)**

Run: `python scripts/msrp/run_forward_vol_validation.py --window-start 2024-01-01 --window-end 2024-06-30 --phase 5B --replicates 1000`
Expected: prints a `Validation <id> (...)` line and writes a record dir under `core/msi/validations/`. (Dev verification — NOT the held-out window.)

- [ ] **Step 6: Delete the smoke-run record (keep the tree clean) and commit**

```bash
rm -rf core/msi/validations/*/   # remove smoke-run output; keep .gitkeep
git add scripts/msrp/run_forward_vol_validation.py tests/msi/msrp/test_forward_vol_validation.py
git commit -m "feat(msrp): A2 harness composition root + phase-6 duplicate guard"
```

---

### Task 7: Full-suite regression + docs sync

**Files:**
- Modify: `docs/PROJECT_STATE.md`
- Modify: `docs/implementation/msrp/reports/MSRP_PHASE5B_A2_DESIGN_SPEC.md` (status DRAFT → IMPLEMENTED-pending-review)

- [ ] **Step 1: Run the full MSI suite**

Run: `python -m pytest tests/msi -q`
Expected: all prior tests still pass (328+ from Phase 5A) plus the new harness tests; 0 failures.

- [ ] **Step 2: Confirm zero frozen-file changes**

Run: `git diff --stat HEAD~6 -- core/msi/contracts core/msi/interfaces core/msi/dra core/msi/artifacts core/msi/msrp/forward_vol.py`
Expected: empty output (no frozen file touched).

- [ ] **Step 3: Update docs**

In `docs/PROJECT_STATE.md`, under Completed, add a Phase-5B line noting the harness is implemented and verified off-window (dev/synthetic), pending independent review + Phase-6 execution. Do NOT claim certification. Flip the design-spec status header to `IMPLEMENTED — pending independent review`.

- [ ] **Step 4: Commit**

```bash
git add docs/PROJECT_STATE.md docs/implementation/msrp/reports/MSRP_PHASE5B_A2_DESIGN_SPEC.md
git commit -m "docs(msrp): record Phase 5B A2 harness implementation (pending review)"
```

---

## Self-Review

**Spec coverage:**
- §2.1 offline-evidence path + one-extra-day load → Task 2 (`score_window` warmup + `n_dropped_boundary`), Task 6 (`load_candles_over` loads window+7d/warmup).
- §2.2 direct `evaluate()` (not DRA wrapper) → Task 2 (`artifact.evaluate(ev)`, reads `estimates[0].value`).
- §3 `ValidationHarness` immutable state + seven methods + aggregator → Tasks 3–4.
- §4 seven domains → Task 4; §4.2 fixture hardcoded → Task 2 `vix_regime`; §4.4 sub-period split at `floor(n/2)` → Task 4 `_score`; §4.5 two-layer reproducibility → Task 4 (`_evaluate_reproducibility` in-domain) + Task 6 (two-instance test).
- §5.1 `validation_id` preimage (excludes results, includes harness_version) → Task 4 `validation_id`; §5.1a `dataset_snapshot_hash` → Task 5; §5.1b `methodology_fingerprint` excludes harness_version → Task 3.
- §5.2 `results_digest` (6dp, include/exclude) → Task 3 `results_digest` + `_round_results`; §5.3 checksum seal → Task 5.
- §6 candidate verdict + reviewer/approval unset in 5B → Task 4 `run()` + Task 5 `write_sealed_record` (reviewer/approval=None).
- §7 `phase` field + phase-6 guard → Task 5 record + Task 6 `phase6_guard`.
- §8 substrate pinned → Task 6 `Methodology`/`Substrate`.
- §9 off-window testing → Tasks 1–6 use dev/synthetic; §10 additive/no frozen changes → Task 7 Step 2.

**Placeholder scan:** No TBD/TODO. `_evaluate_calibration` computes real empirical coverage of the reconstructed log-normal predictive interval against actual `RV_{t+1}` and gates on the pinned `nominal`/`tolerance` (mandatory MSI-006 domain). `nominal=0.90`, `tolerance=0.05` are pinned in `Methodology` and enter `methodology_fingerprint`. `z` comes from `scipy.stats.norm.ppf` (scipy is present transitively via statsmodels). Add `scipy` to the Tech Stack line if the environment lacks it.

**Type consistency:** `ScoredWindow` fields consumed identically in `_score`/domains; `Methodology`/`Substrate` field names match between `methodology_fingerprint`, `run()`, and Task 6 construction; `results_digest`/`_round_results` shared; `validation_id()` preimage keys match design spec §5.1 verbatim; `write_sealed_record` reads `record.results`, `record.methodology`, `record.domain_results` — all fields defined on `ValidationRecord` in Task 3.
