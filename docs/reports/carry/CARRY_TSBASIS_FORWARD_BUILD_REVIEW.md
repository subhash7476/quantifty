# Forward-PAPER Build Review — Carry + TS Basis (Pieces 1–3)

**Generated:** 2026-07-26
**Reviews:** commits `2462e7e` + `0e15f78` on `main` (worktree `F:\Nifty`).
**Against:** the corrected work plan in `CARRY_TSBASIS_PAPER_PLAN.md` §3.
**Verdict:** **DO NOT RUN. Two blockers, one of which can corrupt the production facts DB
and void the parity gate.** Architecture (keep LoopDriver) was followed; the data plumbing was not.

Files reviewed: `scripts/carry_refresh_facts.py`, `scripts/carry_forward_runner.py`,
`scripts/signal_engine/carry/publish_facts.py` (diff), `scripts/signal_engine/ts_basis/publish_facts.py`,
`core/database/providers/daily_bhavcopy.py`, and the consumed
`scripts/signal_engine/carry/build_carry.py` + `neutralize.py`.

---

## BLOCKER 1 — the monthly construction is gone; `--forward` runs the WEEKLY builder

The frozen, validated Carry construction is **monthly** (last trading day of each month).
The `build_carry.py` and `neutralize.py` now on `main` are the **weekly cadence-decay variants**
(merged via `e0618ed`):

- `build_carry.py:40` — `"""Weekly formation dates: last trading day of each ISO week."""`,
  grid `PARTITION BY year, week` (`build_carry.py:45`). No monthly/weekly toggle exists.
- `build_carry.py:26` and `neutralize.py:19` — both write/read
  **`weekly_signals.duckdb`**, not `signals.duckdb`.

`publish_facts.py --forward` (`main()`) calls `build_carry.main()` then `neutralize.main()`,
then `_publish()` — but `_publish` reads `SIG_DB = …/signals.duckdb` (`publish_facts.py:34`),
the **old monthly** store. The result is a broken pipeline with two failure modes, both bad:

- **As wired (path mismatch):** `build_carry` regenerates `weekly_signals.duckdb`; `_publish`
  reads the stale monthly `signals.duckdb` (still ending 2026-07-20) → **0 new formations
  appended, forever.** This is a **silent no-op** — the exact failure Piece 1 was written to
  prevent, relocated one layer down. `carry_refresh_facts.py` reports success anyway (see HIGH-1).
- **If someone "fixes" the mismatch** to read `weekly_signals.duckdb`: the monthly
  `facts.duckdb` gets **weekly** formations appended (`INSERT OR REPLACE`, `publish_facts.py`),
  corrupting the production facts table, **voiding the +0.0 bp parity gate and the frozen
  construction** — precisely the guarantee `CARRY_TSBASIS_PAPER_PLAN.md` §2 said must be protected.

The frozen monthly builder is **no longer runnable from the repo**; the monthly `signals.duckdb`
(126 formations) survives only as a stale artifact from before `e0618ed`.

**Fix:** restore a monthly build path (a `--monthly`/`--weekly` flag on `build_carry`, or a
separate frozen monthly builder) writing to `signals.duckdb`, and make `publish_facts` and
`build_carry`/`neutralize` agree on the store. Re-run the parity gate after.

---

## BLOCKER 2 — the spurious-formation bug (§1.4) is NOT fixed

Piece 1's explicit requirement (`CARRY_TSBASIS_PAPER_PLAN.md` §1.4, §3): *"emit formations
**only** on genuine month-end formation dates and never on 'last available date.'"*

`publish_facts._publish(forward=True)` emits every formation `build_carry` produces that is
`not in existing_dates` (`publish_facts.py`, `if forward and fdate in existing_dates: continue`).
There is **no genuine-month-end filter.** The mid-month spurious `2026-07-20` (DTE 8) remains in
the facts, and forward mode would emit new spurious "last trading day so far this month"
formations exactly as the original bug did. A forward runner **would rebalance a real book on a
fake formation date.**

**Fix:** the formation grid must be anchored to calendar month-end (the last trading day of a
*completed* month), not the last available bhavcopy date. Do not emit the current month's
formation until the month's true formation date has passed.

---

## HIGH-1 — staleness guard reports success on a no-op

`carry_refresh_facts.main()` returns `1` ("refreshed") whenever `publish_facts` exits 0, even if
**zero** new formations were added (`carry_refresh_facts.py:92-94` prints new/old max but does not
compare them or fail on equality). Combined with BLOCKER 1, the operator gets a green "Refresh
complete" while nothing advances. The loud-failure path (`return 2`) fires only when *bhavcopy*
hasn't advanced — not when the publish itself is a no-op.

Also `_has_formation_passed` is `today > max_facts` (`carry_refresh_facts.py:58`) — true on almost
every day, so it does not actually detect a crossed month-end boundary; it is a staleness proxy,
not the boundary check §1.4 asked for.

**Fix:** fail loudly (non-zero) when `today` is past a genuine month-end formation date and
`MAX(formation_date)` has not advanced to include it. Success must require a real new formation.

---

## HIGH-2 — Piece 2 acceptance criterion (parity re-verification) not met

`CARRY_TSBASIS_PAPER_PLAN.md` §3 Piece 2 acceptance: *"re-run the parity check against the forward
path and confirm it still reproduces research at +0.0 bp."* The runner **asserts** parity in its
docstring (`carry_forward_runner.py:5`, "parity-verified at +0.0 bp") but nothing re-runs it.

The runner is *not* byte-identical to the replay path: `carry_forward_runner.py:199-201` runs
`while True:` and pokes `driver._state = driver._state.__class__.RUNNING` to re-loop a
**completed** driver each poll. `carry_paper_replay.py` runs the driver **once** over a bounded
window. Whether `LoopDriver` supports being restarted this way — dedup, provider cursor, state
machine — is unverified. This restart loop is the one genuinely new mechanism and it is exactly
where a forward/replay divergence would hide.

*(Withdrawn on inspection: the three separate `ReplayClock` instances at
`carry_forward_runner.py:99/190` mirror `carry_paper_replay.py:175/179/200` — same pattern, not a
new defect. Not a finding.)*

**Fix:** add a bounded forward-vs-replay parity harness over a historical span and gate the runner
on +0.0 bp, before any live-paper start. Verify the restart-loop against `LoopDriver`'s contract.

---

## HIGH-3 — TS Basis shadow sleeve cannot produce forward evidence

The stated rationale (`publish_facts.py:8-9`): *"forward paper is the only path that can ever
re-qualify it."* But nothing generates **new** `z_ts` going forward:

- `ts_basis/publish_facts.py` is full-rebuild only (no `--forward`) and reads the **static**
  `ts_signals.duckdb` produced by the research-window `build_ts_signals.py`.
- There is no forward TS-Basis signal build (no forward z_ts construction analogous to a monthly
  carry refresh).

So the shadow book is frozen at its research formations and **can never accumulate a forward-paper
observation** — the exact thing the shadow sleeve exists to produce. Piece 3 as built is a
one-shot historical publish, not a forward sleeve.

**Fix:** Piece 3 needs the same forward-build + forward-facts path as Carry (once BLOCKER 1 gives
a template), including a genuine forward z_ts construction.

---

## MEDIUM — semantic mislabel (accepted footgun) and schema claim

`ts_facts` stores raw `z_ts` in a column named `z_carry_neut` (`ts_basis/publish_facts.py:82`).
Hook reuse is **verified safe** — `CarryRebalancerHook` selects only
`underlying, z_carry_neut, quintile, eligible` (`carry_rebalancer.py:456`), and the dropped
`sector`/`z_carry` columns are never queried. So "same schema" is loose (two columns dropped) but
not breaking. The mislabel is an audit footgun: anyone reading `ts_facts` sees `z_carry_neut` and
infers neutralized carry. Add a comment/column note or rename with a hook alias.

---

## What was done right (stated for balance)

- **LoopDriver was retained** — the central architectural correction from §2 was followed; the
  bespoke-scheduler proposal was correctly rejected.
- **Books are isolated** by distinct `run_id` in `production.duckdb` — reasonable.
- **Hook reuse** for TS Basis works at the column level (verified, not assumed).
- `daily_bhavcopy.refresh_if_exhausted()` is a clean seam for forward polling.

---

## Bottom line

The **architecture** is right; the **data pipeline is not runnable and is unsafe to run.**
BLOCKER 1 alone means a forward refresh either silently does nothing or corrupts the production
facts DB and voids the parity gate. BLOCKER 2 means even a working refresh would trade a real
book on fake dates. Neither the Carry forward path nor the TS Basis shadow sleeve can currently
produce a valid forward observation. Fix BLOCKER 1 and 2, meet the Piece 2 parity re-check, then
re-review before any live-paper start.
