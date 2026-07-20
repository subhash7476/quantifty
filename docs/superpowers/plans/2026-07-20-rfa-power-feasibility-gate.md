# RFA Power-Feasibility Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a data-free pre-registration gate that returns a computed ABANDON/PROCEED verdict on whether a proposed research construct can reach statistical power 0.80 given its available formations and a frozen, independently defended effect-size band.

**Architecture:** Three layers with one responsibility each. `scripts/rfa/power.py` is pure math (noncentral-t power and its inversion), no I/O. `governance/rfa/declaration.py` is the frozen input contract plus validation. `scripts/rfa/gate.py` composes them into a verdict and emits a markdown report. Declarations live in a governance namespace outside `scripts/` because they are governance records, not tunable script inputs.

**Tech Stack:** Python 3.10+, `scipy.stats` (`nct`, `t`), `hashlib`, `dataclasses`, pytest.

## Global Constraints

- Power hurdle: **0.80**. Alpha: **0.05**.
- The gate reads **no market data**. Any data access is a design violation.
- The verdict must be **computed**, never a hardcoded string. This is the F1 defect being guarded against.
- SHA-256 digest covers the **entire declaration file's bytes**, never a subset. This is the PSB-2 partial-seal defect being guarded against.
- Provenance fields are **required and non-empty**; empty provenance is a hard validation failure, not a warning.
- `test_type` has **no default**; omission is a validation failure.
- Methodology-version mismatch is a **hard failure** — the gate refuses to emit a verdict.
- PROCEED means **"not provably infeasible"** — never "feasible", never "authorized". This wording appears in the report text verbatim.
- Repo conventions: no docstrings/comments on code you didn't change; no over-engineering; no backwards-compat shims.

---

### Task 1: Power core

**Files:**
- Create: `scripts/rfa/__init__.py` (empty)
- Create: `scripts/rfa/power.py`
- Test: `tests/rfa/__init__.py` (empty), `tests/rfa/test_power.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `power_at(delta: float, sd: float, n: int, two_sided: bool) -> float`; `n_required(delta: float, sd: float, target_power: float, two_sided: bool) -> int | None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/rfa/test_power.py
import pytest
from scripts.rfa.power import power_at, n_required


def test_reproduces_documented_formation_requirement():
    n = n_required(delta=0.03, sd=0.2, target_power=0.80, two_sided=True)
    assert 340 <= n <= 360


def test_power_increases_with_n():
    lo = power_at(delta=0.03, sd=0.2, n=100, two_sided=True)
    hi = power_at(delta=0.03, sd=0.2, n=400, two_sided=True)
    assert hi > lo


def test_power_increases_with_delta_and_decreases_with_sd():
    base = power_at(delta=0.03, sd=0.2, n=200, two_sided=True)
    assert power_at(delta=0.06, sd=0.2, n=200, two_sided=True) > base
    assert power_at(delta=0.03, sd=0.4, n=200, two_sided=True) < base


def test_one_sided_needs_fewer_observations_than_two_sided():
    one = n_required(delta=0.03, sd=0.2, target_power=0.80, two_sided=False)
    two = n_required(delta=0.03, sd=0.2, target_power=0.80, two_sided=True)
    assert one < two


def test_degenerate_inputs_return_zero_power():
    assert power_at(delta=0.03, sd=0.0, n=200, two_sided=True) == 0.0
    assert power_at(delta=0.03, sd=0.2, n=1, two_sided=True) == 0.0


def test_n_required_returns_none_when_unreachable():
    assert n_required(delta=0.0, sd=0.2, target_power=0.80, two_sided=True) is None


def test_matches_psb1_bootstrap_reference():
    from scripts.psb1.screening_harness import _power
    ref, _ = _power(0.034892, 0.104033, 84)
    ours = power_at(delta=0.034892, sd=0.104033, n=84, two_sided=False)
    assert ours == pytest.approx(ref, abs=1e-9)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/rfa/test_power.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.rfa'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/rfa/power.py
import math

from scipy.stats import nct, t as student_t

ALPHA = 0.05


def power_at(delta, sd, n, two_sided):
    if not (sd > 0) or n < 2:
        return 0.0
    tail = ALPHA / 2 if two_sided else ALPHA
    tcrit = student_t.ppf(1 - tail, df=n - 1)
    ncp = delta * math.sqrt(n) / sd
    return float(nct.sf(tcrit, n - 1, ncp))


def n_required(delta, sd, target_power, two_sided, n_max=1_000_000):
    if power_at(delta, sd, n_max, two_sided) < target_power:
        return None
    lo, hi = 2, n_max
    while lo < hi:
        mid = (lo + hi) // 2
        if power_at(delta, sd, mid, two_sided) >= target_power:
            hi = mid
        else:
            lo = mid + 1
    return lo
```

Binary search rather than a closed-form normal approximation: power is monotone in `n`, and the search resolves against the exact noncentral-t the gate actually reports, so `n_required` and `power_at` can never disagree.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/rfa/test_power.py -v`
Expected: PASS, 7 tests.

If `test_matches_psb1_bootstrap_reference` fails on import (`scripts.psb1` needs a package marker), add an empty `scripts/__init__.py` and `scripts/psb1/__init__.py` — do not weaken the assertion.

- [ ] **Step 5: Commit**

```bash
git add scripts/rfa/__init__.py scripts/rfa/power.py tests/rfa/__init__.py tests/rfa/test_power.py
git commit -m "feat: RFA power core — noncentral-t power and formation-count inversion"
```

---

### Task 2: Declaration contract and validation

**Files:**
- Create: `governance/__init__.py` (empty), `governance/rfa/__init__.py` (empty)
- Create: `governance/rfa/declaration.py`
- Create: `governance/rfa/declarations/__init__.py` (empty)
- Test: `tests/rfa/test_declaration.py`

**Interfaces:**
- Consumes: nothing.
- Produces: frozen dataclass `Declaration` with fields `name, methodology_version, delta_lo, delta_hi, sd_lo, sd_hi, delta_provenance, sd_provenance, prior_exposure, n_available, cadence, window, test_type, metric`; `validate(decl: Declaration) -> None` raising `ValueError`; `TEST_TYPES = {"one_sided", "two_sided"}`; `METRICS = {"rank_ic", "per_trade_pnl"}`; `digest_of(path: str) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/rfa/test_declaration.py
import dataclasses
import hashlib
import pytest
from governance.rfa.declaration import Declaration, validate, digest_of


def _valid(**overrides):
    base = dict(
        name="TESTC1",
        methodology_version="1.0.0",
        delta_lo=0.02, delta_hi=0.05,
        sd_lo=0.15, sd_hi=0.25,
        delta_provenance="Jegadeesh & Titman (1993) cross-sectional momentum magnitudes.",
        sd_provenance="Dispersion floor from first-principles breadth argument, N=200 names.",
        prior_exposure="Operator has read PSB-1 C5 and PSB-2 C2/C4 reports.",
        n_available=130,
        cadence="monthly",
        window="2012-01-01 to 2022-12-30",
        test_type="two_sided",
        metric="rank_ic",
    )
    base.update(overrides)
    return Declaration(**base)


def test_valid_declaration_passes():
    validate(_valid())


def test_declaration_is_immutable():
    d = _valid()
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.delta_hi = 0.99


@pytest.mark.parametrize("field", ["delta_provenance", "sd_provenance", "prior_exposure"])
def test_empty_provenance_rejected(field):
    with pytest.raises(ValueError, match=field):
        validate(_valid(**{field: "   "}))


def test_inverted_bands_rejected():
    with pytest.raises(ValueError, match="delta_lo"):
        validate(_valid(delta_lo=0.09, delta_hi=0.01))
    with pytest.raises(ValueError, match="sd_lo"):
        validate(_valid(sd_lo=0.9, sd_hi=0.1))


def test_nonpositive_sd_rejected():
    with pytest.raises(ValueError, match="sd_lo"):
        validate(_valid(sd_lo=0.0))


def test_insufficient_formations_rejected():
    with pytest.raises(ValueError, match="n_available"):
        validate(_valid(n_available=1))


def test_unknown_test_type_rejected():
    with pytest.raises(ValueError, match="test_type"):
        validate(_valid(test_type="bayesian"))


def test_unknown_metric_rejected():
    with pytest.raises(ValueError, match="metric"):
        validate(_valid(metric="sharpe"))


def test_digest_covers_entire_file(tmp_path):
    p = tmp_path / "decl.py"
    p.write_bytes(b"DECLARATION = 1\n# trailing content after any notional seal\n")
    expected = hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest_of(str(p)) == expected


def test_digest_changes_when_trailing_bytes_change(tmp_path):
    p = tmp_path / "decl.py"
    p.write_bytes(b"DECLARATION = 1\n")
    first = digest_of(str(p))
    p.write_bytes(b"DECLARATION = 1\n# appended\n")
    assert digest_of(str(p)) != first
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/rfa/test_declaration.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'governance'`

- [ ] **Step 3: Write the implementation**

```python
# governance/rfa/declaration.py
import hashlib
from dataclasses import dataclass

TEST_TYPES = {"one_sided", "two_sided"}
METRICS = {"rank_ic", "per_trade_pnl"}

_PROVENANCE_FIELDS = ("delta_provenance", "sd_provenance", "prior_exposure")


@dataclass(frozen=True)
class Declaration:
    name: str
    methodology_version: str
    delta_lo: float
    delta_hi: float
    sd_lo: float
    sd_hi: float
    delta_provenance: str
    sd_provenance: str
    prior_exposure: str
    n_available: int
    cadence: str
    window: str
    test_type: str
    metric: str


def validate(decl):
    for field in _PROVENANCE_FIELDS:
        if not getattr(decl, field).strip():
            raise ValueError(f"{field} is required and must be non-empty")
    if decl.delta_lo > decl.delta_hi:
        raise ValueError("delta_lo must not exceed delta_hi")
    if decl.sd_lo > decl.sd_hi:
        raise ValueError("sd_lo must not exceed sd_hi")
    if decl.sd_lo <= 0:
        raise ValueError("sd_lo must be strictly positive")
    if decl.n_available < 2:
        raise ValueError("n_available must be at least 2")
    if decl.test_type not in TEST_TYPES:
        raise ValueError(f"test_type must be one of {sorted(TEST_TYPES)}")
    if decl.metric not in METRICS:
        raise ValueError(f"metric must be one of {sorted(METRICS)}")


def digest_of(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/rfa/test_declaration.py -v`
Expected: PASS, 12 tests.

- [ ] **Step 5: Commit**

```bash
git add governance tests/rfa/test_declaration.py
git commit -m "feat: RFA declaration contract — frozen bands, required provenance, whole-file digest"
```

---

### Task 3: Verdict evaluation

**Files:**
- Create: `scripts/rfa/gate.py`
- Test: `tests/rfa/test_gate.py`

**Interfaces:**
- Consumes: `power_at`, `n_required` (Task 1); `Declaration`, `validate` (Task 2).
- Produces: `METHODOLOGY_VERSION: str`; `POWER_HURDLE: float`; frozen dataclass `Verdict` with fields `decision, max_power, corner_delta, corner_sd, n_available, n_required_corner, n_required_central, n_required_pessimistic, methodology_version`; `evaluate(decl: Declaration) -> Verdict`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/rfa/test_gate.py
import pytest
from governance.rfa.declaration import Declaration
from scripts.rfa.gate import METHODOLOGY_VERSION, POWER_HURDLE, evaluate


def _decl(**overrides):
    base = dict(
        name="TESTC1",
        methodology_version=METHODOLOGY_VERSION,
        delta_lo=0.02, delta_hi=0.05,
        sd_lo=0.15, sd_hi=0.25,
        delta_provenance="literature",
        sd_provenance="first principles",
        prior_exposure="none",
        n_available=130,
        cadence="monthly",
        window="2012-2022",
        test_type="two_sided",
        metric="rank_ic",
    )
    base.update(overrides)
    return Declaration(**base)


def test_abandons_when_corner_cannot_clear_hurdle():
    v = evaluate(_decl(delta_hi=0.01, sd_lo=0.30, sd_hi=0.40, n_available=50))
    assert v.decision == "ABANDON"
    assert v.max_power < POWER_HURDLE


def test_proceeds_when_corner_clears_hurdle():
    v = evaluate(_decl(delta_hi=0.20, sd_lo=0.10, n_available=400))
    assert v.decision == "PROCEED"
    assert v.max_power >= POWER_HURDLE


def test_verdict_flips_with_inputs_only():
    weak = evaluate(_decl(delta_hi=0.01, sd_lo=0.30, sd_hi=0.40, n_available=50))
    strong = evaluate(_decl(delta_hi=0.20, sd_lo=0.10, n_available=400))
    assert {weak.decision, strong.decision} == {"ABANDON", "PROCEED"}


def test_evaluates_at_optimistic_corner():
    v = evaluate(_decl())
    assert v.corner_delta == 0.05
    assert v.corner_sd == 0.15


def test_methodology_mismatch_is_hard_failure():
    with pytest.raises(ValueError, match="methodology_version"):
        evaluate(_decl(methodology_version="0.0.1-ancient"))


def test_invalid_declaration_rejected_before_evaluation():
    with pytest.raises(ValueError, match="delta_provenance"):
        evaluate(_decl(delta_provenance=""))


def test_reports_required_formations_at_each_band_point():
    v = evaluate(_decl())
    assert v.n_required_corner < v.n_required_central < v.n_required_pessimistic
```

Note on `test_abandons_when_corner_cannot_clear_hurdle`: `sd_hi` is raised to 0.40 alongside `sd_lo=0.30` so the band stays ordered and `validate` does not reject the fixture before evaluation.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/rfa/test_gate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.rfa.gate'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/rfa/gate.py
from dataclasses import dataclass

from governance.rfa.declaration import validate
from scripts.rfa.power import n_required, power_at

METHODOLOGY_VERSION = "1.0.0"
POWER_HURDLE = 0.80


@dataclass(frozen=True)
class Verdict:
    decision: str
    max_power: float
    corner_delta: float
    corner_sd: float
    n_available: int
    n_required_corner: int
    n_required_central: int
    n_required_pessimistic: int
    methodology_version: str


def evaluate(decl):
    if decl.methodology_version != METHODOLOGY_VERSION:
        raise ValueError(
            f"methodology_version mismatch: declaration targets "
            f"{decl.methodology_version}, gate is {METHODOLOGY_VERSION}. "
            f"A frozen declaration was defended against a specific ruleset; "
            f"re-approve it against the current version before re-running."
        )
    validate(decl)

    two_sided = decl.test_type == "two_sided"
    corner_delta, corner_sd = decl.delta_hi, decl.sd_lo
    mid_delta = (decl.delta_lo + decl.delta_hi) / 2
    mid_sd = (decl.sd_lo + decl.sd_hi) / 2

    max_power = power_at(corner_delta, corner_sd, decl.n_available, two_sided)

    return Verdict(
        decision="ABANDON" if max_power < POWER_HURDLE else "PROCEED",
        max_power=max_power,
        corner_delta=corner_delta,
        corner_sd=corner_sd,
        n_available=decl.n_available,
        n_required_corner=n_required(corner_delta, corner_sd, POWER_HURDLE, two_sided),
        n_required_central=n_required(mid_delta, mid_sd, POWER_HURDLE, two_sided),
        n_required_pessimistic=n_required(decl.delta_lo, decl.sd_hi, POWER_HURDLE, two_sided),
        methodology_version=METHODOLOGY_VERSION,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/rfa/test_gate.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/rfa/gate.py tests/rfa/test_gate.py
git commit -m "feat: RFA verdict — optimistic-corner evaluation against power 0.80"
```

---

### Task 4: Report generator

**Files:**
- Create: `scripts/rfa/report.py`
- Create: `scripts/rfa/run_rfa.py`
- Test: `tests/rfa/test_report.py`

**Interfaces:**
- Consumes: `Verdict`, `evaluate`, `METHODOLOGY_VERSION`, `POWER_HURDLE` (Task 3); `Declaration`, `digest_of` (Task 2).
- Produces: `render(decl: Declaration, verdict: Verdict, digest: str) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/rfa/test_report.py
from governance.rfa.declaration import Declaration
from scripts.rfa.gate import METHODOLOGY_VERSION, evaluate
from scripts.rfa.report import render


def _decl(**overrides):
    base = dict(
        name="TESTC1",
        methodology_version=METHODOLOGY_VERSION,
        delta_lo=0.02, delta_hi=0.05,
        sd_lo=0.15, sd_hi=0.25,
        delta_provenance="Momentum magnitudes from Jegadeesh & Titman (1993).",
        sd_provenance="Breadth-based dispersion floor, first principles.",
        prior_exposure="Operator has read PSB-1 and PSB-2 reports.",
        n_available=130,
        cadence="monthly",
        window="2012-2022",
        test_type="two_sided",
        metric="rank_ic",
    )
    base.update(overrides)
    return Declaration(**base)


def _render(**overrides):
    d = _decl(**overrides)
    return render(d, evaluate(d), "deadbeef" * 8)


def test_report_states_verdict_and_digest():
    out = _render(delta_hi=0.01, sd_lo=0.30, sd_hi=0.40, n_available=50)
    assert "ABANDON" in out
    assert "deadbeef" * 8 in out
    assert METHODOLOGY_VERSION in out


def test_proceed_is_qualified_as_not_provably_infeasible():
    out = _render(delta_hi=0.20, sd_lo=0.10, n_available=400)
    assert "PROCEED" in out
    assert "not provably infeasible" in out


def test_report_carries_scope_caveat_and_corner_rationale():
    out = _render().lower()
    assert "fees" in out and "maxdd" in out
    assert "intentionally unrealistic" in out


def test_report_reproduces_provenance_verbatim():
    d = _decl()
    out = render(d, evaluate(d), "0" * 64)
    assert d.delta_provenance in out
    assert d.sd_provenance in out
    assert d.prior_exposure in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/rfa/test_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.rfa.report'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/rfa/report.py
from scripts.rfa.gate import POWER_HURDLE


def render(decl, verdict, digest):
    meaning = (
        "The construct cannot be demonstrated at the declared bands. Do not build it."
        if verdict.decision == "ABANDON"
        else "not provably infeasible — this is a floor, not authorization to build."
    )
    lines = [
        f"# {decl.name} — Research Feasibility Assessment",
        "",
        f"**VERDICT: {verdict.decision}** — {meaning}",
        "",
        f"- Methodology version: `{verdict.methodology_version}`",
        f"- Declaration SHA-256: `{digest}`",
        f"- Metric: {decl.metric} | Test: {decl.test_type} | Power hurdle: {POWER_HURDLE}",
        f"- Formations available: {decl.n_available} ({decl.cadence}, {decl.window})",
        "",
        "## Optimistic corner",
        "",
        "| Quantity | Value |",
        "|---|---|",
        f"| delta (high) | {verdict.corner_delta} |",
        f"| SD (low) | {verdict.corner_sd} |",
        f"| n (raw, no AC haircut) | {verdict.n_available} |",
        f"| **Max achievable power** | **{verdict.max_power:.4f}** |",
        "",
        "The corner is **intentionally unrealistic.** Because the bands are declared",
        "independently, (delta_hi, sd_lo) may describe a large edge with unusually stable",
        "outcomes — the least plausible combination in practice and the most generous to the",
        "construct. This is deliberate: it maximizes the burden of proof for ABANDON, so a",
        "firing gate is unarguable, while correspondingly weakening PROCEED to its stated",
        "meaning of *not provably infeasible*.",
        "",
        "## Formations required for power 0.80",
        "",
        "| Band point | n required |",
        "|---|---|",
        f"| Optimistic corner | {verdict.n_required_corner} |",
        f"| Central | {verdict.n_required_central} |",
        f"| Pessimistic | {verdict.n_required_pessimistic} |",
        f"| **Available** | **{verdict.n_available}** |",
        "",
        "## Declared bands and provenance",
        "",
        f"**delta: [{decl.delta_lo}, {decl.delta_hi}]**",
        "",
        decl.delta_provenance,
        "",
        f"**SD: [{decl.sd_lo}, {decl.sd_hi}]**",
        "",
        decl.sd_provenance,
        "",
        "**Prior exposure**",
        "",
        decl.prior_exposure,
        "",
        "## Scope",
        "",
        "This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,",
        "turnover, or economic significance. A construct can clear this gate and still fail",
        "on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not",
        "clearance.",
        "",
    ]
    return "\n".join(lines)
```

```python
# scripts/rfa/run_rfa.py
import importlib
import sys
from pathlib import Path

from governance.rfa.declaration import digest_of
from scripts.rfa.gate import evaluate
from scripts.rfa.report import render


def main(name):
    module = importlib.import_module(f"governance.rfa.declarations.{name}")
    decl = module.DECLARATION
    verdict = evaluate(decl)
    out = Path("docs/reports") / f"{decl.name}_RFA.md"
    out.write_text(render(decl, verdict, digest_of(module.__file__)), encoding="utf-8")
    print(f"{decl.name}: {verdict.decision} (max power {verdict.max_power:.4f}) -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/rfa/test_report.py -v`
Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/rfa/report.py scripts/rfa/run_rfa.py tests/rfa/test_report.py
git commit -m "feat: RFA report generator and runner"
```

---

### Task 5: Retrospective check against C5, C4, C2, F1

**Files:**
- Create: `scripts/rfa/retrospective.py`
- Test: `tests/rfa/test_retrospective.py`

**Interfaces:**
- Consumes: `power_at` (Task 1); `POWER_HURDLE` (Task 3).
- Produces: `CASES: tuple[Case, ...]`; `assess() -> list[dict]`; `render(rows) -> str`; markdown at `docs/reports/RFA_RETROSPECTIVE.md`.

**Context for the implementer — read this before writing code.** CLAUDE.md claims this gate "would have saved the back half of C5, C4, C2, and F1." The design spec (§5.2) commits to *testing* that claim and reporting it wrong if it is wrong, rather than tuning the gate until it agrees. **The numbers below show it is partly wrong: C2 as recorded in PSB-2 clears the hurdle at power 0.9198, and the gate would have said PROCEED.** Do not adjust anything to make C2 fire. Report it.

Recorded values, sourced as noted:

| Case | delta | SD | n* | Source |
|---|---|---|---|---|
| C5 (PSB-1) | 0.067639 | 0.246232 | 42 | `PSB1_C5_REPORT.md` lines 23-24, 62 |
| C4 (PSB-2) | 0.046550 | 0.208949 | 42 | `PSB2_C4_REPORT.md` lines 23-24 |
| C2 (PSB-2, as recorded) | 0.034892 | 0.104033 | 84 | `PSB2_C2_REPORT.md` lines 23-24, 61 |
| C2 (Phase 0.5, extended TRAIN) | read from report | read from report | read from report | `C2_PHASE0_5_MINIBATTERY.md` variant table |
| F1 TRAIN (optimistic) | 0.0154 | derived below | 83 | `F1_FEASIBILITY_SCREEN_REPORT.md` TRAIN table |

All PSB cases used a one-sided gate (`ALPHA` in `scripts/psb1/screening_harness.py`), so pass `two_sided=False` for them.

F1 reports no rank IC. Its dispersion is recovered from the block-bootstrap CI width:
`SE ≈ (CI_high − CI_low) / (2 × 1.96)`, then `SD = SE × √n`. For TRAIN optimistic:
`SE ≈ (0.0306 − (−0.0024)) / 3.92 ≈ 0.008418`, `SD ≈ 0.008418 × √83 ≈ 0.0767`.
This is an **approximation** — the bootstrap CI is asymmetric and percentile-based, so a
normal-symmetric back-out is inexact. Label it approximate in the output. It is adequate for a
feasibility upper bound and must not be presented as F1's actual dispersion.

The Phase 0.5 C2 row must be read off the variant table in `C2_PHASE0_5_MINIBATTERY.md`
(columns `Mean IC`, `SD_IC`, `Power (n*)`) rather than taken from this plan — open the file and
use V2, the strongest variant, whose recorded power is 0.6563. The `0.023` figure that appears
in CLAUDE.md prose is a rounded restatement and is not authoritative.

- [ ] **Step 1: Write the failing tests**

```python
# tests/rfa/test_retrospective.py
from scripts.rfa.retrospective import assess


def _by_name(rows):
    return {r["name"]: r for r in rows}


def test_gate_fires_on_c5_c4_and_f1():
    rows = _by_name(assess())
    for name in ("C5", "C4", "F1_TRAIN"):
        assert rows[name]["decision"] == "ABANDON", name


def test_c2_as_recorded_in_psb2_does_not_fire():
    rows = _by_name(assess())
    assert rows["C2_PSB2"]["decision"] == "PROCEED"
    assert rows["C2_PSB2"]["max_power"] > 0.80


def test_c2_fires_only_on_extended_history_reestimate():
    rows = _by_name(assess())
    assert rows["C2_PHASE0_5"]["decision"] == "ABANDON"


def test_f1_dispersion_is_flagged_approximate():
    rows = _by_name(assess())
    assert rows["F1_TRAIN"]["sd_is_approximate"] is True
    assert rows["C5"]["sd_is_approximate"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/rfa/test_retrospective.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.rfa.retrospective'`

- [ ] **Step 3: Write the implementation**

Replace the `C2_PHASE0_5` delta/sd/n placeholders with the values you read from
`C2_PHASE0_5_MINIBATTERY.md` before running.

```python
# scripts/rfa/retrospective.py
import math
from dataclasses import dataclass
from pathlib import Path

from scripts.rfa.gate import POWER_HURDLE
from scripts.rfa.power import power_at


@dataclass(frozen=True)
class Case:
    name: str
    delta: float
    sd: float
    n: int
    sd_is_approximate: bool
    source: str


def _sd_from_ci(ci_low, ci_high, n):
    return ((ci_high - ci_low) / (2 * 1.96)) * math.sqrt(n)


CASES = (
    Case("C5", 0.067639, 0.246232, 42, False, "PSB1_C5_REPORT.md"),
    Case("C4", 0.046550, 0.208949, 42, False, "PSB2_C4_REPORT.md"),
    Case("C2_PSB2", 0.034892, 0.104033, 84, False, "PSB2_C2_REPORT.md"),
    Case("C2_PHASE0_5", 0.0, 0.0, 0, False, "C2_PHASE0_5_MINIBATTERY.md"),
    Case("F1_TRAIN", 0.0154, _sd_from_ci(-0.0024, 0.0306, 83), 83, True,
         "F1_FEASIBILITY_SCREEN_REPORT.md"),
)


def assess():
    rows = []
    for c in CASES:
        p = power_at(c.delta, c.sd, c.n, two_sided=False)
        rows.append({
            "name": c.name,
            "delta": c.delta,
            "sd": c.sd,
            "n": c.n,
            "max_power": p,
            "decision": "ABANDON" if p < POWER_HURDLE else "PROCEED",
            "sd_is_approximate": c.sd_is_approximate,
            "source": c.source,
        })
    return rows


def render(rows):
    lines = [
        "# RFA Retrospective — Non-Binding Context Appendix",
        "",
        "**These numbers are prior-exposed observations. They carry no weight in any binding",
        "RFA declaration** (design spec §2.2). They exist to test one claim in CLAUDE.md, not",
        "to calibrate the gate.",
        "",
        "**Claim under test:** the power-feasibility pre-check \"would have saved the back half",
        "of C5, C4, C2, and F1.\"",
        "",
        "| Case | delta | SD | n | Max power | Verdict | Source |",
        "|---|--:|--:|--:|--:|---|---|",
    ]
    for r in rows:
        sd = f"{r['sd']:.6f}" + ("*" if r["sd_is_approximate"] else "")
        lines.append(
            f"| {r['name']} | {r['delta']:.6f} | {sd} | {r['n']} | "
            f"{r['max_power']:.4f} | {r['decision']} | `{r['source']}` |"
        )
    lines += [
        "",
        "\\* SD recovered from block-bootstrap CI width via a normal-symmetric back-out",
        "(`SE = (CI_high - CI_low) / 3.92`, `SD = SE x sqrt(n)`). The bootstrap CI is",
        "asymmetric and percentile-based, so this is an approximation adequate for a",
        "feasibility bound — it is not F1's actual dispersion.",
        "",
        "## Finding",
        "",
        "The CLAUDE.md claim is **partly wrong, and the exception is informative.**",
        "",
        "The gate fires on C5, C4, and F1. It does **not** fire on C2 as PSB-2 recorded it:",
        "at delta=0.034892, SD=0.104033, n*=84 the projected power is 0.9198, comfortably",
        "clear of the hurdle. A pre-check run before PSB-2 would have returned PROCEED.",
        "",
        "C2 fails only once the extended-history re-estimate widens its dispersion. That is",
        "exactly the caveat PSB-2 recorded against itself: the recommendation rested on a",
        "55-observation, 2.3-year SD estimate, and power is a function of SD.",
        "",
        "**This does not weaken the gate; it locates its dependency.** The verdict is only as",
        "good as the declared SD, which is precisely why the design requires SD to be",
        "independently defended and frozen rather than inherited from a short in-sample read",
        "(design spec §2.1, §2.3).",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    rows = assess()
    Path("docs/reports/RFA_RETROSPECTIVE.md").write_text(render(rows), encoding="utf-8")
    for r in rows:
        print(f"{r['name']:14s} power={r['max_power']:.4f} -> {r['decision']}")
```

- [ ] **Step 4: Run tests and generate the appendix**

Run: `python -m pytest tests/rfa/test_retrospective.py -v`
Expected: PASS, 4 tests.

Run: `python -m scripts.rfa.retrospective`
Expected: five lines printed; `C2_PSB2` shows PROCEED at power ≈ 0.9198, the rest ABANDON.

If `C2_PSB2` does not reproduce ≈ 0.9198, the power core disagrees with `PSB2_C2_REPORT.md`
line 66 — stop and reconcile before continuing. Do not adjust the test.

- [ ] **Step 5: Commit**

```bash
git add scripts/rfa/retrospective.py tests/rfa/test_retrospective.py docs/reports/RFA_RETROSPECTIVE.md
git commit -m "test: RFA retrospective — gate fires on C5/C4/F1, not on C2 as PSB-2 recorded it"
```

---

### Task 6: Document the gate in CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` — add a new top-level RFA section after the SFB-1/F1 section, and correct the stale claim inside SFB-1/F1's "Successor — none authorized" paragraph.

**Interfaces:**
- Consumes: everything above.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Add the RFA section**

Insert after the SFB-1/F1 section, before "## Options Analysis Dashboard":

```markdown
## RFA — Research Feasibility Assessment (power pre-check)

**Status:** Active gate. Every new research construct must clear it **before any construct
code is written.**

The RFA answers one question: given the formations actually available and an independently
defended effect-size band, can this construct reach power 0.80 even under assumptions more
generous than anyone believes? It reads no market data, so it is free.

- **ABANDON is dispositive.** **PROCEED means "not provably infeasible"** — a floor, never
  authorization, and never a statement about fees or MaxDD.
- Binding inputs are **independent defended bands on delta and SD**, each with required
  provenance. Historical PSB/SFB reads are prior-exposed and **must not** define them.
- Bands are **frozen at approval** (SHA-256 over the whole declaration file) and cannot be
  revised in response to results.

| File | Purpose |
|---|---|
| `governance/rfa/declaration.py` | Frozen input contract + validation |
| `governance/rfa/declarations/` | One declaration module per candidate |
| `scripts/rfa/power.py` | Noncentral-t power + formation-count inversion |
| `scripts/rfa/gate.py` | Optimistic-corner verdict; `METHODOLOGY_VERSION` |
| `scripts/rfa/report.py`, `run_rfa.py` | Report generation |
| `scripts/rfa/retrospective.py` | Non-binding retrospective |
| `docs/reports/RFA_RETROSPECTIVE.md` | Retrospective output |
| `docs/superpowers/specs/2026-07-20-rfa-power-feasibility-gate-design.md` | Design |

**Retrospective correction.** This repo previously implied the pre-check would have saved C5,
C4, C2, and F1. Tested: it fires on C5, C4, and F1, but **not** on C2 as PSB-2 recorded it
(power 0.9198 — the gate would have said PROCEED). C2 fails only on the extended-history SD
re-estimate. The gate's verdict is only as good as the declared SD, which is why SD must be
independently defended rather than inherited from a short in-sample read.
```

- [ ] **Step 2: Correct the stale claim in the SFB-1/F1 section**

In the "Successor — none authorized" paragraph, replace:

> That gate is free, touches no data, and would have saved the back half of C5, C4, C2, and F1.

with:

> That gate is free, touches no data, and would have saved the back half of C5, C4, and F1 —
> tested, not assumed; see `docs/reports/RFA_RETROSPECTIVE.md`. C2 is the exception: as PSB-2
> recorded it, C2 clears the hurdle and the gate would have said PROCEED.

- [ ] **Step 3: Run the full RFA suite**

Run: `python -m pytest tests/rfa/ -v`
Expected: PASS, 34 tests (7 power + 12 declaration + 7 gate + 4 report + 4 retrospective).

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document RFA gate in CLAUDE.md and correct the C5/C4/C2/F1 claim"
```

---

## Notes for the executor

- Every number in Task 5 is sourced from a committed report. If a value you read disagrees
  with this plan, **the report wins** — stop and reconcile rather than editing a test to match.
- No task reads market data. If you find yourself opening a `.duckdb` file, you have left the
  plan.
- `Declaration` field names are fixed at Task 2 and used verbatim in Tasks 3-5. Do not rename.
- The retrospective's job is to test a claim, not to confirm one. A failing expectation there
  is a finding to report, not a bug to suppress.
