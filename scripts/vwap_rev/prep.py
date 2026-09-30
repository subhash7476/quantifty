"""VWAP-XREV step 0 (outcome-free): cache dense sessions, build PIT F&O membership."""
from __future__ import annotations

import sys
import time

from scripts.vwap_rev import common as C
from scripts.vwap_rev import universe as U


def main() -> None:
    sessions = C.regular_sessions()
    print(f"regular sessions: {len(sessions)} ({sessions[0][0]} .. {sessions[-1][0]})")
    present = {}
    t0 = time.time()
    for i, (d, p) in enumerate(sessions):
        s = C.cached_session(d, p)
        present[d] = [str(x) for x in s["symbols"]]
        if i % 100 == 0:
            print(i, d, len(s["symbols"]), f"{time.time()-t0:.0f}s", flush=True)
    mem = U.build_membership(present)
    U.save(mem)
    print("agreement with certified ISD PIT:", U.agreement_with_certified(mem))
    n = [len(v) for v in mem.values()]
    print("F&O members/session min/median/max:", min(n), sorted(n)[len(n)//2], max(n))


if __name__ == "__main__":
    sys.exit(main())
