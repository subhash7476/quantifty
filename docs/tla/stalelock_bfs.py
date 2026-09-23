"""Explicit-state BFS mirror of docs/tla/StaleLock.tla (TLC unavailable: Java 8)."""
from collections import deque
from itertools import product

PIDS = (1, 2)
MAX_TIME, MAX_SPAWNS, TOL = 4, 4, 1
NOLOCK = (0, 0, 0, 0)  # pid, mtime, start, inc


def run(mode, atomic):
    # state: now, alive, started, inc, pc, lock, spawns  (tuples indexed pid-1)
    init = (1, (False,) * 2, (0,) * 2, (0,) * 2, ("done",) * 2, NOLOCK, 0)

    def lock_alive(s):
        now, alive, started, inc, pc, lock, spawns = s
        if lock == NOLOCK or not alive[lock[0] - 1]:
            return False
        st = started[lock[0] - 1]
        return st <= lock[1] + TOL if mode == "mtime" else st == lock[2]

    def upd(t, i, v):
        return t[:i] + (v,) + t[i + 1:]

    def nexts(s):
        now, alive, started, inc, pc, lock, spawns = s
        if now < MAX_TIME:
            yield "Tick", (now + 1, alive, started, inc, pc, lock, spawns)
        for p in PIDS:
            i = p - 1
            for holder in (True, False):
                if not alive[i] and spawns < MAX_SPAWNS and now > started[i]:
                    yield (f"Spawn({p},{'holder' if holder else 'other'})",
                           (now, upd(alive, i, True), upd(started, i, now),
                            upd(inc, i, spawns + 1),
                            upd(pc, i, "idle" if holder else "done"), lock, spawns + 1))
            write = (p, now, started[i], inc[i])
            if not atomic and alive[i] and pc[i] == "idle":
                if lock_alive(s):
                    yield f"Check({p})=refuse", (now, upd(alive, i, False), started, inc,
                                                 upd(pc, i, "done"), lock, spawns)
                else:
                    yield f"Check({p})=stale", (now, alive, started, inc,
                                                upd(pc, i, "checked"), lock, spawns)
            if not atomic and alive[i] and pc[i] == "checked":
                yield f"WriteLock({p})", (now, alive, started, inc,
                                          upd(pc, i, "holding"), write, spawns)
            if atomic and alive[i] and pc[i] == "idle":
                if lock_alive(s):
                    yield f"Acquire({p})=refuse", (now, upd(alive, i, False), started, inc,
                                                   upd(pc, i, "done"), lock, spawns)
                else:
                    yield f"Acquire({p})=write", (now, alive, started, inc,
                                                  upd(pc, i, "holding"), write, spawns)
            if alive[i] and pc[i] == "holding":
                yield f"Release({p})", (now, upd(alive, i, False), started, inc,
                                        upd(pc, i, "done"),
                                        NOLOCK if lock[0] == p else lock, spawns)
            if alive[i]:
                yield f"Crash({p})", (now, upd(alive, i, False), started, inc,
                                      upd(pc, i, "done"), lock, spawns)

    def no_false_adoption(s):
        return not lock_alive(s) or s[3][s[5][0] - 1] == s[5][3]

    def mutex(s):
        now, alive, started, inc, pc, lock, spawns = s
        return not all(alive[i] and pc[i] == "holding" for i in (0, 1))

    invs = {"NoFalseAdoption": no_false_adoption, "MutualExclusion": mutex}
    parent = {init: None}
    q, found = deque([init]), {}
    while q:
        s = q.popleft()
        for name, f in invs.items():
            if name not in found and not f(s):
                trace, cur = [], s
                while parent[cur] is not None:
                    act, prev = parent[cur]
                    trace.append(act)
                    cur = prev
                found[name] = trace[::-1]
        for act, t in nexts(s):
            if t not in parent:
                parent[t] = (act, s)
                q.append(t)
    return len(parent), found


for mode, atomic in product(("mtime", "stamp"), (False, True)):
    n, found = run(mode, atomic)
    print(f"\nMode={mode} Atomic={atomic}: {n} states")
    for inv in ("NoFalseAdoption", "MutualExclusion"):
        tr = found.get(inv)
        print(f"  {inv}: " + ("HOLDS" if tr is None else "VIOLATED  " + " -> ".join(tr)))
