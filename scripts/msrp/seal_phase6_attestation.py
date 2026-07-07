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
