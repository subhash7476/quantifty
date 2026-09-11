"""backfill_fo_1m fetches only runs of sessions on which a name has no 1m row at all.

The fetcher upserts and resets is_synthetic, so a run that spanned a session the
name already has would rewrite marked bars.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.cas.backfill_fo_1m import plan_runs  # noqa: E402

S = [date(2026, 8, 6), date(2026, 8, 7), date(2026, 8, 10), date(2026, 8, 11), date(2026, 8, 12)]


def test_runs_break_at_sessions_the_name_already_has():
    absent = {S[0]: {"K1"}, S[1]: {"K1", "K2"}, S[2]: {"K2"}, S[4]: {"K1"}}
    assert plan_runs(absent, S) == {
        (S[0], S[1]): ["K1"],          # spans the weekend only through 08-07, which K1 lacks
        (S[1], S[2]): ["K2"],
        (S[4], S[4]): ["K1"],          # 08-10 and 08-11 are present for K1, so not refetched
    }


def test_names_sharing_a_run_are_fetched_together():
    absent = {S[2]: {"K2", "K1"}, S[3]: {"K1", "K2"}}
    assert plan_runs(absent, S) == {(S[2], S[3]): ["K1", "K2"]}
