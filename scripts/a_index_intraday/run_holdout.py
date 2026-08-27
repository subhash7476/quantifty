"""A — HOLDOUT gate (frozen parameters, A_PHASE0_PRE_REGISTRATION.md §9).

One test on the frozen family book (w45 — the TRAIN-qualifying cell) over the
HOLDOUT fence 2019-01-01..2022-12-31, alpha 0.05, positive direction.
Report-only costs. SEALED files are never opened.

Usage: python scripts/a_index_intraday/run_holdout.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.a_index_intraday.common as cm  # noqa: E402

LEDGER = ROOT / "data" / "a_index_intraday" / "trial_ledger.jsonl"
REPORT = ROOT / "docs" / "reports" / "A_HOLDOUT_REPORT.md"

HOLDOUT_LO, HOLDOUT_HI = date(2019, 1, 1), date(2022, 12, 31)
FAMILY_BOOK = "w45"          # frozen: the TRAIN-qualifying cell
ALPHA = 0.05
NULL_ITERS = 1000


def main() -> int:
    t0 = time.time()
    rng = np.random.default_rng(cm.SEED)
    cell = cm.load_cell(HOLDOUT_LO, HOLDOUT_HI, FAMILY_BOOK)
    r = cm.returns_of(FAMILY_BOOK, cell["features"], cell["entry"],
                      cell["exit"], cell["fee"], cell["dates"])
    n = len(r)
    mean = float(np.mean(r))
    nw = cm.nw_t(r)
    a1 = cm.ac1(r)

    # sign-permutation null
    gross = (cell["exit"] / cell["entry"] - 1.0) * 1e4
    slip = np.asarray([cm.SLIP_BP[FAMILY_BOOK][cm.era_of(d)]
                       for d in cell["dates"]]) * 2.0
    null_s = np.empty(NULL_ITERS)
    for i in range(NULL_ITERS):
        perm = rng.integers(0, 2, size=n).astype(float) * 2.0 - 1.0
        null_s[i] = float(np.mean(perm * gross - perm * cm.BASIS_MEAN_BP
                                  - cell["fee"] - slip))
    p_sign = float(np.mean(null_s >= mean))

    # block-shift null (the TRAIN family-test null)
    dates = cell["dates"]
    months = sorted({(d.year, d.month) for d in dates})
    month_idx = {m: i for i, m in enumerate(months)}
    sess_month = np.asarray([month_idx[(d.year, d.month)] for d in dates])
    null_b = np.empty(NULL_ITERS)
    feats = cell["features"]
    for i in range(NULL_ITERS):
        perm = rng.permutation(len(months))
        shifted = feats[perm[sess_month]]
        fr = cm.returns_of(FAMILY_BOOK, shifted, cell["entry"],
                           cell["exit"], cell["fee"], dates)
        null_b[i] = float(np.mean(fr))
    p_shift = float(np.mean(null_b >= mean))

    passed = p_shift < ALPHA and mean > 0.0

    run_id = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with open(LEDGER, "a", encoding="utf-8") as lf:
        lf.write(json.dumps({"event": "run_start", "run_id": run_id,
                             "gate": "HOLDOUT", "seed": cm.SEED,
                             "prereg_sha": cm.PREREG_SHA,
                             "holdout_fence": [HOLDOUT_LO.isoformat(),
                                               HOLDOUT_HI.isoformat()],
                             "family_book": FAMILY_BOOK}) + "\n")
        lf.write(json.dumps({"run_id": run_id, "event": "holdout_registration",
                             "cell": FAMILY_BOOK, "alpha": ALPHA,
                             "direction": "positive",
                             "nulls": ["sign_permutation", "block_shift"]})
                 + "\n")
        lf.write(json.dumps({"run_id": run_id, "event": "holdout",
                             "cell": FAMILY_BOOK, "n": n,
                             "mean_net_bp": mean, "nw_t": nw, "ac1": a1,
                             "p_sign_permutation": p_sign,
                             "p_block_shift": p_shift,
                             "net_positive": mean > 0.0,
                             "pass": passed}) + "\n")

    lines = [
        "# A — HOLDOUT Gate Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')} · "
        f"runtime {time.time() - t0:.0f}s · prereg SHA-16 "
        f"`{cm.PREREG_SHA[:16]}` · seed {cm.SEED}",
        "",
        f"**HOLDOUT pass** — fence {HOLDOUT_LO} → {HOLDOUT_HI}; family book "
        f"**{FAMILY_BOOK}** (the TRAIN-qualifying cell); n = {n} "
        f"(invalid/skipped {cell['invalid']})",
        "",
        "| Quantity | Value |",
        "|---|---|",
        f"| Mean net bp | {mean:.2f} |",
        f"| NW t | {nw:.2f} |",
        f"| AC1 | {a1:.3f} |",
        f"| p (sign-permutation null) | {p_sign:.4f} |",
        f"| p (block-shift null) | {p_shift:.4f} |",
        f"| Net positive | {'yes' if mean > 0 else 'no'} |",
        f"| **Verdict (p < 0.05, positive)** | **{'PASS' if passed else 'FAIL'}** |",
        "",
        "Costs applied identically to TRAIN (report-only per §9); no parameter "
        "was changed.",
        "",
        "Ledger: `data/a_index_intraday/trial_ledger.jsonl` (append-only).",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"HOLDOUT: mean {mean:.3f} bp, p_sign {p_sign:.4f}, "
          f"p_shift {p_shift:.4f} -> {'PASS' if passed else 'FAIL'} -> {REPORT}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
