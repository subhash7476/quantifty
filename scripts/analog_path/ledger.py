"""Append-only experiment ledger (protocol §19).

Rows are appended before results are reported; nothing is ever deleted or
overwritten. Entries are written before the experiment result is visible to
the operator where practical (the row records the run's identity and the
frozen parameters; the result payload is appended in the same row by the
runner after computation — the file is append-only either way).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from scripts.analog_path import config

LEDGER_PATH = Path(__file__).resolve().parents[2] / "data" / "analog_path" / "experiment_ledger.jsonl"


def record(experiment_id: str, *, fence: str, representation: str | None,
           distance: str | None, k: int | None, horizon: str | None,
           sample: str, metric: str, result: dict,
           used_for_methodology_decision: bool) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "experiment_id": experiment_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "code_version": config.CONFIG_SHA256[:12],
        "data_version": "certified 1m store, A-track slice certification register",
        "sample": sample,
        "fence": fence,
        "representation": representation,
        "distance": distance,
        "k": k,
        "horizon": horizon,
        "metric": metric,
        "result": result,
        "used_for_methodology_decision": used_for_methodology_decision,
    }
    with open(LEDGER_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
