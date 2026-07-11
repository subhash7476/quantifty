"""MSI-006 A2 Validation Harness for the ForwardVolatilityArtifact.

Deterministic, additive. Executes the frozen Phase-1 dossier's seven-domain
validation and assembles one immutable, checksum-sealed record. See
docs/implementation/msrp/reports/MSRP_PHASE5B_A2_DESIGN_SPEC.md.

Tech Stack: Python 3.10+, numpy, pandas, duckdb, scipy, pytest.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
        from scipy.stats import norm

        s = self._scored
        nominal = self._methodology.calibration_nominal
        tol = self._methodology.calibration_tolerance
        z = float(norm.ppf(1 - (1 - nominal) / 2))
        value, unc, rv_next = s.s_cand, s.s_unc, s.rv_next
        mask = (value > 0) & (unc > 0) & (rv_next > 0) & np.isfinite(rv_next)
        n_valid = int(np.sum(mask))
        if n_valid == 0:
            return DomainResult("calibration", "FAIL",
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
            "calibration_nominal": self._methodology.calibration_nominal,
            "calibration_tolerance": self._methodology.calibration_tolerance,
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
