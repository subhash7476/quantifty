# Implementer Prompt — Carry Full-Path Replay Parity (TRAIN + HOLDOUT)

**To:** DeepSeek (implementer). **From:** Claude (prompt + review).
**Date issued:** 2026-07-24. **Branch:** `infra/backtest-bootstrap`.

---

## 0. What you are being asked to do, in one sentence

Run the **real production path** — `LoopDriver(Mode.REPLAY)` → `DailyBhavcopyProvider` →
`CarryRebalancerHook` → `ExecutionHandler` → `PaperBroker` — over TRAIN and HOLDOUT, and prove it
reproduces the research net quintile spread within the **pre-existing 15 bp tolerance**.

This closes `CARRY_IMPLEMENTATION_BRIDGE.md` §5 **as originally worded**. §5 required "run the
production path through `LoopDriver` in backtest mode." What passed previously
(`CARRY_PARITY_REPORT.md`, +0.0 bp) was construction parity via a **direct call** to
`compute_target_book` — the driver loop was never involved. The replay path only became usable on
2026-07-24 (`CARRY_REPLAY_FIX_REVIEW.md`).

---

## 1. Read these first — do not start from this prompt alone

| File | Why |
|---|---|
| `scripts/signal_engine/carry/parity_check.py` | **The template.** You are adding an arm to this comparison, not inventing one. |
| `docs/reports/CARRY_IMPLEMENTATION_BRIDGE.md` §5, §5.1, §5.2, §5.3, §8 | The gate's rules, the fee decision, the SEALED rule, and the three bugs that faked a PASS |
| `docs/reports/CARRY_REPLAY_INFRA_TEST_REPORT.md` | The defect that blocked this until today |
| `docs/reports/CARRY_REPLAY_FIX_REVIEW.md` | What was fixed, what is still open |
| `core/execution/portfolio/carry_rebalancer.py` | `CarryRebalancerHook`, `compute_target_book` |
| `scripts/carry_integration_check.py` | Working example of wiring the hook to a real handler |

---

## 2. Hard constraints — violating any of these invalidates the run

1. **SEALED IS NOT RUN.** TRAIN `2016-03-31 → 2020-12-31` and HOLDOUT `2021-01-01 → 2022-12-31`
   only. SEALED parity follows **by construction** (bridge §5.2). Do not read, load, or iterate the
   2023+ window. Do not modify or execute `run_sealed.py` — it is a frozen provenance artifact.
2. **No construction changes.** Signal, sign, quintile rule, neutralization, ADV cap, no-trade band
   and fee model are frozen (§8). If production diverges from research, **the plumbing is wrong, not
   the construction.** All three §5.3 bugs were wiring. Do not "tune" anything toward agreement.
3. **Import production code; never copy it.** §5.3's worst finding was a parity gate that verified a
   *local copy* of the construction logic while the real module stayed buggy. Import
   `compute_target_book` / `CarryRebalancerHook` from `core.execution.portfolio.carry_rebalancer`.
   No re-implementations, no "simplified for the harness" variants.
4. **Reuse `parity_check.py`'s constants exactly** — `GROSS_EXPOSURE = 10_000_000.0`,
   `SLIPPAGE_BP = 5`, tolerance `abs(delta_bp) < 15`. Do not re-derive, re-tune, or widen them.
   Tolerance exists for float ordering and fill timing — **it must never absorb a fee or
   construction gap** (§5.1 pt 4).
5. **Pin the parity gross; do NOT size via `NseMarginEngine`.** The harness runs at
   research-identical gross so any residual delta is pure path divergence, not a margin-model
   difference. Margin sizing is a PAPER concern and is already closed.
6. **Do not fix the open items** listed in `CARRY_REPLAY_FIX_REVIEW.md` §2.3 / §2.6.1
   (`DuckDBMarketDataProvider`, the vacuous provider-test assertion). Out of scope. Mention if you
   trip over them; do not touch them.

---

## 3. Design — what to build

Create `scripts/signal_engine/carry/replay_parity_check.py`.

**The core idea: change only how the book is produced. Keep everything downstream identical.**

`parity_check.py`'s `_simulate_production()` builds each formation date's book by calling
`compute_target_book(...)` directly. Your new arm must obtain the book **from a real driver replay
instead** — then feed it through the **same** return / fee / slippage / annualization math, the same
research arm, and the same tolerance.

Concretely:

- Construct a real `LoopDriver(Mode.REPLAY)` with `DailyBhavcopyProvider` over the window, a real
  `ExecutionHandler` + `PaperBroker`, and a real `CarryRebalancerHook` — the production wiring.
- Inject a **parity gross-exposure policy** returning `GROSS_EXPOSURE` (Rs 1 Cr), not
  `paper_gross_exposure_policy`, and not margin-derived sizing. Read how
  `gross_exposure_policy` is injected in `carry_rebalancer.py` and follow it.
- As the replay runs, record for each formation date on which the hook fires: the **date** and the
  resulting **target book** (symbol → signed weight/notional).
- Feed those recorded books into the *same* downstream computation `_simulate_production` uses.
  **Refactor `parity_check.py` to share that math rather than duplicating it** — a copy would
  reintroduce exactly the §5.3 failure. If sharing requires extracting a helper, extract it and
  leave `parity_check.py` importing the same helper, then re-run `parity_check.py` to prove it still
  reports +0.0 bp.

**Why compare books rather than realized PnL:** the §5 gate asks whether the production path
*constructs the research book on the research dates*. The returns math is shared and already
validated; re-deriving returns from fills would change the metric and make any delta
uninterpretable. Keep the metric fixed; vary only the path.

---

## 4. Run these two pre-checks BEFORE computing any net spread

Both are cheap and both isolate plumbing from construction. **Report them even if they pass.**

**4.1 Rebalance-date set identity.** Collect the set of dates the hook actually fired on during the
replay. It must equal **exactly** the set of research formation dates in the window (58 in TRAIN).
Report `missing` and `extra` explicitly.

This is the highest-probability failure. A formation date that is not a trading day in the bhavcopy
calendar, or an off-by-one on the roll, means the hook never fires that month — a silently skipped
rebalance that drifts the net spread. **If this check fails, stop and report; do not proceed to net
spread.**

**4.2 Per-date book identity.** For each formation date, compare the driver-produced target book
against the book `compute_target_book` yields directly (the `parity_check.py` arm). Report the count
of dates where the symbol sets or weights differ, with one worked example of any difference.

If 4.1 and 4.2 are both clean, the net spread is a formality. If the net spread then diverges anyway,
the cause is downstream of construction — say so rather than adjusting anything.

---

## 5. State predictions before you run

Repo convention (`.claude/rules/common/testing.md`): for research and audit scripts, the discipline
is a **falsifiable prediction stated before the run.** Write these into the report *before* the
results section, and do not revise them afterward:

1. The rebalance-date set will/won't match the 58 TRAIN formation dates exactly.
2. Per-date books will/won't be identical to the direct-call arm.
3. The net-spread delta will fall within/outside 15 bp on each window.

If a prediction is wrong, **say so plainly in the report.** A wrong prediction that is disclosed is
a finding; a quietly revised one is a fabrication.

---

## 6. Verdict logic — the specific trap to avoid

`parity_check.py`'s original verdict logic **computed the parity delta, printed it, and then ignored
it** — `all_pass` was wired only to `net > 0`, so the script could print a `**FAIL**` row and
`GATE VERDICT: PASS` on the same page (§5.3 bug 1).

Your script must:

- Compute `gate_pass = dates_match AND books_match AND parity_within_tol_all_windows`.
- Use that **same** variable for the printed verdict **and** the process exit code.
- Never hand-write a verdict, footnote, or explanation into the report. **The report is
  script-generated; every number in it comes from the run.** No hand-edited values, no `PASS*` with
  an asterisk excusing a failure.

---

## 7. Determinism

Run the whole thing **twice** and assert the outputs are identical. "Same inputs → byte-identical
orders, in backtest and live" is the §7 non-negotiable, and a replay that isn't reproducible cannot
support a parity claim. Report both runs' key figures.

---

## 8. Deliverables

1. `scripts/signal_engine/carry/replay_parity_check.py` — permanent, committed, re-runnable. Not a
   throwaway.
2. `docs/reports/CARRY_REPLAY_PARITY_REPORT.md` — **fully script-generated**, containing: setup and
   constants used, §5 predictions, §4.1 date-set result, §4.2 book-identity result, per-window
   gross/net/fee-drag/delta-bp table against research, determinism result, and the verdict.
3. Confirmation that `parity_check.py` still reports **+0.0 bp** after any shared-helper refactor.
4. Full test suite still green (`tests/runtime tests/database tests/portfolio tests/strategies`;
   780 passing as of commit `06aa49d`).

---

## 9. Acceptance criteria

| # | Criterion |
|---|---|
| 1 | Rebalance-date set == research formation dates, both windows |
| 2 | Per-date target books identical to the direct-call arm |
| 3 | Net-spread delta within 15 bp, TRAIN **and** HOLDOUT |
| 4 | `gate_pass` drives both the printed verdict and the exit code |
| 5 | Two runs produce identical output |
| 6 | `parity_check.py` still +0.0 bp; 780 tests still green |
| 7 | SEALED untouched; no construction parameter changed |

---

## 10. If it fails

**A FAIL is a perfectly good outcome of this run** — it is what the gate is for, and it is cheaper
now than after LIVE capital. Do not try to make it pass.

Report the divergence with the smallest reproducing case you can isolate (one formation date, one
symbol, expected vs actual). Do not adjust tolerance, gross, fees, or any construction parameter to
close a gap. Fix plumbing only, and if you fix something, re-run **both** arms from scratch and say
what you changed.

**Do not trust your own green run.** Every round of this track has found the previous round wrong by
re-measuring rather than re-reading — including a "GATE D PASS" that was not real. Before reporting
PASS, re-run the script fresh and confirm the numbers reproduce.
