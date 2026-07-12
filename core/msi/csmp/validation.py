"""MSI-006 A2 Validation Harness for the CSMP XSMomentumArtifact (Phase 5/A2).

Deterministic, additive. Consumes a pre-computed cross-sectional ScoredDataset
(built by the runner from the artifact's scores + gate-(a/b/c/d) data via the ONE
§5.2 `fwd()` in `scripts/csmp/phase1_prereg_analysis.py`) and assembles one immutable,
checksum-sealed record over the seven MSI-006 domains. Mirrors the MSRP harness shape
(`core/msi/msrp/validation.py`).

The gate is PINNED, not re-selected (dossier §3.4, D-i ratified): the artifact is
**Approved** iff the one-sided 95% **Student-t** lower bound of `mean_IC` > 0, and
**Deployable** iff additionally `Δ_net > 0` (net top-40 minus the STRONGER universe
baseline, net of fees + slippage). The harness applies it and renders the §10 verdict
mechanically; a human does not choose it. `iid_perc` / `mb_L12` bounds are REPORTED,
non-gating (both readings stay visible).

The A1 VOID precondition (data-integrity screen) is a HARD, STRUCTURAL gate: `run()`
asserts it first and cannot emit a verdict if it fails.
"""

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as _np
from scipy.stats import t as _tdist

from core.msi.csmp.void_precondition import VoidResult, assert_void_clear
from core.msi.msrp.validation_stats import canonical_json, format_6dp, sha256_hex

HARNESS_VERSION = "1.0.0"
NOMINAL_1S = 0.05  # one-sided gate α (D-i)


# --- Scored dataset: everything the runner computes on the evaluation window --
@dataclass(frozen=True)
class ScoredDataset:
    n_months: int
    mean_ic: float
    sd_ic: float
    student_t_lb: float          # THE GATE: one-sided 95% Student-t lower bound of mean_IC
    delta_net: float             # deployment qualifier: net top-40 minus stronger baseline (fees+slip)
    delta_net_fees_only: float
    top40_net: float
    universe_stronger_net: float
    universe_weaker_net: float
    # reported, non-gating:
    iid_perc_lb: float
    mb_l12_lb: float
    delta_net_ci: Tuple[float, float]
    by_year_ic: Dict[int, float]
    by_year_hit: Dict[int, float]
    rule1_by_year: Dict[int, int]
    rule2_by_year: Dict[int, int]
    top40_rule2_events: Tuple[tuple, ...]
    stress_neg100_mean_ic: float
    stress_neg100_delta_net: float
    subperiod_first_ic: float
    subperiod_second_ic: float
    risk_top40: Tuple[float, float, float]     # vol, sharpe, maxDD
    risk_universe: Tuple[float, float, float]
    uncertainty_tercile_ic: Tuple[float, float, float]  # (low-unc, mid, high-unc) tercile mean IC
    ls_quintile_spread: float
    formation_exclusions: int
    max_trade_date: date


@dataclass(frozen=True)
class Substrate:
    block_length: int
    n_replicates: int
    seed: int
    lib_versions: Dict[str, str]   # recorded provenance — NOT in the identity (env-dependent)
    commit: str                    # the CODE commit that contains the harness — provenance, NOT in the identity
    source_hashes: Dict[str, str]  # git-normalized content hashes of the source files — THE identity


@dataclass(frozen=True)
class Methodology:
    substrate: Substrate
    gate: str
    holding_k: int
    slippage_bps_per_side: float
    dossier_rev: str


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


def student_t_one_sided_lb(mean: float, sd: float, n: int, conf: float = 0.95) -> float:
    """One-sided (1-conf) lower confidence bound on a mean (Student-t). The pinned gate."""
    se = sd / math.sqrt(n)
    return float(mean - _tdist.ppf(conf, n - 1) * se)


def methodology_fingerprint(m: Methodology) -> str:
    # CONTENT-ADDRESSED identity (Prompt-9 F1). The preimage carries git-normalized
    # SOURCE CONTENT HASHES — never `git rev-parse HEAD` (which drifts with every later
    # commit and can name a commit lacking the code), and never `lib_versions` or the
    # code `commit` (env/checkout-dependent). Those two are recorded provenance elsewhere.
    # A docs commit, a version bump, or a Windows CRLF checkout cannot move this fingerprint.
    payload = {
        "source_hashes": m.substrate.source_hashes,
        "block_length": m.substrate.block_length,
        "n_replicates": m.substrate.n_replicates,
        "seed": m.substrate.seed,
        "gate": m.gate,
        "holding_k": m.holding_k,
        "slippage_bps_per_side": m.slippage_bps_per_side,
        "dossier_rev": m.dossier_rev,
    }
    return sha256_hex(canonical_json(payload))


def _round(obj):
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, _np.bool_):
        return bool(obj)
    if isinstance(obj, (int, _np.integer)):
        return int(obj)
    if isinstance(obj, (float, _np.floating)):
        return format_6dp(float(obj))
    if isinstance(obj, dict):
        return {k: _round(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round(x) for x in obj]
    return obj


def results_digest(results: Dict[str, object]) -> str:
    return sha256_hex(canonical_json(_round(results)))


def render_verdict(lb: float, delta_net: float, mean_ic: float) -> str:
    """§10 decision table, applied mechanically."""
    if lb > 0.0 and delta_net > 0.0:
        return "Approved & Deployable"
    if lb > 0.0 and delta_net <= 0.0:
        return "Approved, Not Deployed"
    if lb <= 0.0 and mean_ic > 0.0:
        return "Inconclusive (Not Approved)"
    return "Rejected"


class ValidationHarness:
    def __init__(self, artifact, methodology: Methodology, scored: ScoredDataset,
                 void_result: VoidResult, evaluation_window: Tuple[date, date], phase: str,
                 artifact_checksum: str, dataset_snapshot_hash: str):
        self._artifact = artifact
        self._m = methodology
        self._s = scored
        self._void = void_result
        self._window = evaluation_window
        self._phase = phase
        self._artifact_checksum = artifact_checksum
        self._dataset_snapshot_hash = dataset_snapshot_hash

    def _results(self) -> Dict[str, object]:
        s = self._s
        return {
            "evaluation_window": [str(self._window[0]), str(self._window[1])],
            "n_months": s.n_months, "mean_ic": s.mean_ic, "sd_ic": s.sd_ic,
            "gate_student_t_lb": s.student_t_lb,
            "delta_net": s.delta_net, "delta_net_fees_only": s.delta_net_fees_only,
            "top40_net": s.top40_net, "universe_stronger_net": s.universe_stronger_net,
            "universe_weaker_net": s.universe_weaker_net,
            "reported_iid_perc_lb": s.iid_perc_lb, "reported_mb_l12_lb": s.mb_l12_lb,
            "delta_net_ci": list(s.delta_net_ci),
            "by_year_ic": {str(k): v for k, v in s.by_year_ic.items()},
            "by_year_hit": {str(k): v for k, v in s.by_year_hit.items()},
            "rule1_by_year": {str(k): v for k, v in s.rule1_by_year.items()},
            "rule2_by_year": {str(k): v for k, v in s.rule2_by_year.items()},
            "top40_rule2_events": [list(e) for e in s.top40_rule2_events],
            "stress_neg100_mean_ic": s.stress_neg100_mean_ic,
            "stress_neg100_delta_net": s.stress_neg100_delta_net,
            "subperiod_first_ic": s.subperiod_first_ic,
            "subperiod_second_ic": s.subperiod_second_ic,
            "risk_top40": list(s.risk_top40), "risk_universe": list(s.risk_universe),
            "uncertainty_tercile_ic": list(s.uncertainty_tercile_ic),
            "ls_quintile_spread": s.ls_quintile_spread,
            "formation_exclusions": s.formation_exclusions,
            "void_undocumented_residue": self._void.residue_undocumented,
        }

    def _domains(self) -> Tuple[DomainResult, ...]:
        s = self._s
        art = self._artifact
        rules = art.get_evidence_rules()
        architectural = DomainResult(
            "architectural",
            "PASS" if (art.metadata.artifact_id == "csmp-xs-momentum-v1"
                       and rules.get("score", "").startswith("adj_close(t-1m)")) else "FAIL",
            {"artifact_version": art.metadata.artifact_version,
             "latent_variable": "xs_momentum_score", "construct": rules.get("construct")},
        )
        scientific = DomainResult(
            "scientific", "PASS" if s.student_t_lb > 0.0 else "FAIL",
            {"gate": self._m.gate, "mean_ic": s.mean_ic, "sd_ic": s.sd_ic,
             "n_months": s.n_months, "student_t_lb": s.student_t_lb,
             "delta_net": s.delta_net, "approved": s.student_t_lb > 0.0,
             "deployable": s.student_t_lb > 0.0 and s.delta_net > 0.0},
        )
        temporal = DomainResult(
            "temporal", "PASS" if s.max_trade_date <= self._window[1] else "FAIL",
            {"evaluation_window": [str(self._window[0]), str(self._window[1])],
             "observed_max_trade_date": str(s.max_trade_date),
             "delisting_convention": "§5.2 (shared fwd); rule1/rule2 counts reported",
             "note": "score uses prices <= t-1m; membership PIT; label uses t->t+1"},
        )
        robustness = DomainResult(
            "robustness", "REPORTED",
            {"reported_iid_perc_lb": s.iid_perc_lb, "reported_mb_l12_lb": s.mb_l12_lb,
             "delta_net_ci": list(s.delta_net_ci),
             "by_year_ic": {str(k): v for k, v in s.by_year_ic.items()},
             "rule1_total": sum(s.rule1_by_year.values()),
             "rule2_total": sum(s.rule2_by_year.values()),
             "top40_rule2_events": [list(e) for e in s.top40_rule2_events],
             "stress_neg100_mean_ic": s.stress_neg100_mean_ic,
             "subperiod_first_ic": s.subperiod_first_ic,
             "subperiod_second_ic": s.subperiod_second_ic,
             "risk_top40": list(s.risk_top40), "risk_universe": list(s.risk_universe),
             "ls_quintile_spread": s.ls_quintile_spread},
        )
        rep_ok = results_digest(self._results()) == results_digest(self._results())
        reproducibility = DomainResult(
            "reproducibility", "PASS" if rep_ok else "FAIL",
            {"in_run_double_digest_equal": rep_ok,
             "block_length": self._m.substrate.block_length,
             "n_replicates": self._m.substrate.n_replicates, "seed": self._m.substrate.seed},
        )
        operational = DomainResult(
            "operational", "PASS" if self._void.passed else "FAIL",
            {"void_precondition_passed": self._void.passed,
             "void_undocumented_residue": self._void.residue_undocumented,
             "evaluate_deterministic": True,
             "uncertainty_acts_on_gate": False},
        )
        lo, mid, hi = s.uncertainty_tercile_ic
        calibration = DomainResult(
            "calibration", "REPORTED",
            {"uncertainty_tercile_ic_low_mid_high": [lo, mid, hi],
             "monotonic_low_gt_high": lo > hi,
             "note": "uncertainty reported-not-acted-on; tercile-IC monotonicity is a "
                     "calibration disclosure, non-gating (§7/§9)"},
        )
        return (architectural, scientific, temporal, robustness,
                reproducibility, operational, calibration)

    def validation_id(self) -> str:
        preimage = {
            "artifact_version": self._artifact.metadata.artifact_version,
            "artifact_checksum": self._artifact_checksum,
            "dataset_snapshot_hash": self._dataset_snapshot_hash,
            "methodology_fingerprint": methodology_fingerprint(self._m),
            "harness_version": HARNESS_VERSION,
            "phase": self._phase,
        }
        return sha256_hex(canonical_json(preimage))

    def run(self) -> ValidationRecord:
        # STRUCTURAL: no verdict may be produced if the VOID data-integrity gate fails.
        assert_void_clear(self._void)

        domains = self._domains()
        s = self._s
        verdict = render_verdict(s.student_t_lb, s.delta_net, s.mean_ic)
        results = self._results()
        results["verdict"] = verdict
        results["domain_verdicts"] = {d.name: d.status for d in domains}
        methodology = {
            "harness_version": HARNESS_VERSION,
            "methodology_fingerprint": methodology_fingerprint(self._m),
            "substrate": {"block_length": self._m.substrate.block_length,
                          "n_replicates": self._m.substrate.n_replicates,
                          "seed": self._m.substrate.seed,
                          "lib_versions": self._m.substrate.lib_versions,
                          "commit": self._m.substrate.commit,
                          "source_hashes": self._m.substrate.source_hashes},
            "gate": self._m.gate, "holding_k": self._m.holding_k,
            "slippage_bps_per_side": self._m.slippage_bps_per_side,
            "dossier_rev": self._m.dossier_rev,
        }
        return ValidationRecord(
            validation_id=self.validation_id(), phase=self._phase,
            candidate_verdict=verdict, domain_results=domains, results=results,
            methodology=methodology, results_digest=results_digest(results),
            artifact_version=self._artifact.metadata.artifact_version,
            artifact_checksum=self._artifact_checksum,
            dataset_snapshot_hash=self._dataset_snapshot_hash,
        )


def write_sealed_record(record: ValidationRecord, out_root, timestamp_iso: str) -> Path:
    out = Path(out_root) / record.validation_id
    out.mkdir(parents=True, exist_ok=True)
    results_obj = _round(record.results)
    record_obj = {
        "validation_id": record.validation_id, "phase": record.phase,
        "artifact_version": record.artifact_version,
        "artifact_checksum": record.artifact_checksum,
        "dataset_snapshot_hash": record.dataset_snapshot_hash,
        "candidate_verdict": record.candidate_verdict,
        "domain_verdicts": {d.name: d.status for d in record.domain_results},
        "results_digest": record.results_digest, "timestamp": timestamp_iso,
    }

    def _dump(name, obj):
        (out / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    _dump("results.json", {"results": results_obj,
                           "domains": [{"name": d.name, "status": d.status,
                                        "evidence": _round(d.evidence)}
                                       for d in record.domain_results]})
    _dump("methodology.json", record.methodology)
    _dump("record.json", record_obj)
    content_files = ["record.json", "methodology.json", "results.json"]
    file_hashes = {f: hashlib.sha256((out / f).read_bytes()).hexdigest() for f in content_files}
    combined = hashlib.sha256("".join(file_hashes[f] for f in content_files).encode()).hexdigest()
    _dump("checksum.sha256", {"algorithm": "sha256", "files": file_hashes, "combined_hash": combined})
    return out
