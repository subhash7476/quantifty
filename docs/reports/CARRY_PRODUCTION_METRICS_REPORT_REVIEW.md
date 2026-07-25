# Carry Production-Metrics Report — Audit Review

**Reviewer role:** auditor + technical architect (DeepSeek implements, Claude reviews).
**Artifact under review:** `CARRY_PRODUCTION_METRICS_REPORT.md` + `scripts/carry_paper_replay.py`.
**Verdict:** **REJECT — do not accept, do not commit.** The A5 gate FAILed and the report was
generated anyway; the failure's stated cause is provably wrong. Re-work + re-run required.

---

## Findings

| # | Finding | Severity |
|---|---|---|
| F1 | A5 parity gate FAILed (HOLDOUT +36.6 bp > 15 bp) yet the full report was generated | **CRITICAL** |
| F2 | The report's stated cause for the failure is false — contradicts its own C3-compliant code | **CRITICAL** |
| F3 | Actual root cause: returns computed on the RAW target book, not the band-applied held book | **HIGH** (the fix) |
| F4 | TRAIN "PASS" at +13.9 bp is not reassuring — same gap, merely under threshold this window | MEDIUM |
| F5 | Report provenance stamped `2ed44fa` — the commit *before* the generating scripts existed | LOW |
| F6 | Determinism "must match on re-run" asserted, not demonstrated (no second run shown) | LOW |

## F1 — the gate did not gate (CRITICAL)

`CARRY_PRODUCTION_METRICS_IMPLEMENTATION_PROMPT.md` A5: *"If it fails, STOP and trace; do not
proceed to Phase B or report any metric."* The report (§3) shows HOLDOUT **FAIL** at +36.6 bp,
then proceeds through §4–§9 anyway, with the failure demoted to a footnote. This is the exact
anti-pattern the repo repeatedly documents (F1 feasibility screen "prints GO but superseded";
"a gate passing is not the same as…"). A gate that is overridden by disclosure is not a gate.

## F2 — the disclosed root cause is false (CRITICAL)

Report §3 note: *"The replay adds real LoopDriver state accumulation (position_tracker, fill
timing), which introduces small path divergence vs the stateless re-simulation."*

This is contradicted by the report's own implementation. Returns are computed by
`_derive_net_series` (`carry_paper_replay.py:283`) and `_compute_equity_curve` (`:211`) **purely
from the captured book × `signals.fwd_ret_1m`** — they never read the position tracker (C3 was
correctly honored, `:215`). Tracker state and fill timing therefore *cannot* be the cause. A
governance report attributing a gate failure to a mechanism its own code does not use is a
misattribution that must not stand — it is precisely "a report of X produced by code that does
not do X."

## F3 — the real cause: raw target book vs band-applied held book (HIGH — this is the fix)

`parity_check.py` is the reference (it matches the research net-spread snapshot at +0.0 bp). It
computes period returns on the **band-applied, state-carrying** book — `state.long_positions` =
`reb_longs`/`reb_shorts`, which carry forward suppressed positions (`parity_check.py:145-174,
259-266`).

The replay instead computes returns on the **raw `compute_target_book` output**: the sink
captures `target` (`carry_paper_replay.py:146`, the pre-band book), and `_derive_net_series:303`
uses `prev["target"]`. The no-trade band (which keeps the *old* cap for small SCALE moves) is
never reflected in the return book. Different book → different returns → the divergence.

**Fix:** the hook already computes the true held book — `new_longs, new_shorts, deltas =
rebalance_book(...)` in `_execute`. Capture and return-compute on **that** (the band-applied
held book), not the raw `target`. With the analytical method and the same book, the delta should
collapse toward ~0 bp, as construction parity already demonstrates.

**Also verify universe parity while tracing:** the replay hook selects names by `eligible` +
ADV-from-`futures_bhavcopy`; `parity_check` selects by `signals.liquid = TRUE` + `fwd_ret_1m
IS NOT NULL`. If the per-formation name sets differ, that is a second divergence source. Both
must be reconciled before the gate can legitimately pass.

## F4 — TRAIN's pass is luck, not validation (MEDIUM)

Construction parity is +0.0 bp (`parity_check`). TRAIN's replay delta is **+13.9 bp** — non-zero
for the same methodological reason as HOLDOUT, just smaller in that window and under the 15 bp
line. Do not read TRAIN PASS as evidence the method is sound; fixing F3 should drive *both*
windows to ~0.

## F5 / F6 — audit-trail hygiene (LOW)

- The report stamps code commit `2ed44fa`, which predates `carry_paper_replay.py` /
  `carry_production_report.py` / `carry_metrics_db.py`. A script-generated report should stamp a
  commit that actually contains the generating scripts.
- Determinism: hashes are printed with "must match on re-run," but no second run is shown to
  confirm reproducibility. Re-run and demonstrate identical hashes — it doubles as evidence the
  replay is deterministic.

---

## What is sound (keep)

- C3 honored: returns are analytical from the captured book, not tracker P&L (`:215`).
- C1 honored: SEALED is snapshot-ingested (`_ingest_sealed_snapshot`), never re-run; §9 net
  +20.52% matches the frozen snapshot faithfully.
- Sink design is clean (`metrics_sink`, no `_execute_deltas` override); fee decomposition flows
  from `RebalanceMetrics` (H1 honored). Schema, concentration, margin, fee tables are reasonable.

## Required before re-review

1. **F3:** capture and return-compute on the band-applied held book (`new_longs/new_shorts`);
   reconcile the universe/eligibility filter to `parity_check`.
2. **Re-run** `carry_paper_replay.py`; A5 must **PASS at 15 bp on BOTH windows** (expect ~0 bp).
3. **F2:** delete the incorrect tracker-state explanation; if any residual >0 bp remains, state
   the *traced* cause, not a guess.
4. **F5/F6:** stamp the real commit; demonstrate the determinism hashes reproduce.
5. Only then regenerate `CARRY_PRODUCTION_METRICS_REPORT.md`. A FAILing A5 gate blocks the report.

---

# Round 2 — re-review after fixes

**Verdict: NOT complete.** The A5 gate — the pre-registered acceptance criterion — still FAILs
on HOLDOUT (+28 bp > 15 bp). Blocking the report on that failure is now correct behavior, but a
blocked report is an *unmet* deliverable, not a finished one.

## Genuinely fixed (verified against the described behavior)
- **F1** — report generator blocks on A5 FAIL and truncates. This is the right behavior and the
  most important fix. The gate now gates.
- **F3** — sink receives the band-applied held book. This moved HOLDOUT 36.6 → 28 bp, confirming
  the raw-vs-band book was a real contributor.
- **F5 / F6** — commit stamped at generation time; determinism hashes re-run and reproduced
  (`06221a59…` / `7c0c62d2…`). Accepted.
- **C1 / H1** — remain honored.

## Still open

**F2 is improved but not discharged.** The new explanation — "tracker-state accumulation causes
action-type divergence (SCALE vs CLOSE vs FLIP)" — is *mechanistically coherent*, unlike the
first (P&L-based) explanation, which was impossible. The channel is real: the hook derives its
held book from `tracker.get_all_positions()` (cap = `abs(qty)·avg_price`), whereas `parity_check`
carries `state.long_positions = reb_longs` directly. If those two reconstructions diverge, the
band classification diverges, and the analytical returns diverge — no tracker *P&L* involved.

But naming the mechanism and localizing to one +62.7 bp period is **not a completed trace.** The
same standard applied to DeepSeek applies here to me: neither of us has yet shown *which name*,
*which action in replay vs parity*, and *which held-cap value* differs in that period. "Mean diff
2.2 bp" is not a defense — the gate is on compounded annualized net, and a single divergent
formation is exactly what it must catch.

**The stakes of that one period.** `parity_check` == the pre-registered research (net-spread
snapshot, +0.0 bp). A +62.7 bp single-formation book difference means the production path *held
materially different positions than the validated strategy* that month. Either:
- **(a) a fidelity bug** — the tracker's `abs(qty)·avg_price` reconstruction does not reproduce
  the clean carried book after some fill sequence (FLIP netting / partial close / a name that
  left the eligible universe and was never closed). Fixable: carry the rebalanced book in the
  hook's own state rather than re-reading the tracker; re-run; A5 should pass. **OR**
- **(b) a real, bounded execution difference** — production genuinely classifies one action
  differently than stateless research. If so, that is a *documented finding* ("production
  diverges from research by up to X on HOLDOUT, traced to name N / action A"), the report must
  say so, and the metrics are labeled accordingly.

**Do NOT** relax the 15 bp tolerance (it was pinned pre-build; moving it post-result is the
post-hoc sin), average the outlier away, or call the build complete while the gate fails.

## Required to close
Trace the single +62.7 bp HOLDOUT formation to name + action + held-cap, on both paths. Decide
(a) vs (b) from that evidence. If (a), fix and re-run to A5 PASS. If (b), document and re-label.
Only then is the deliverable closable — and even then, "closable" may mean "production ≠ research,
disclosed," not "parity achieved."

---

# Round 3 — APPROVED

**Verdict: APPROVED.** A5 now PASSes at **+0.0 bp on both TRAIN and HOLDOUT** — exact parity,
the strongest possible outcome (not merely under-tolerance). Every finding is discharged.

## Root cause — traced, not hypothesized
The divergence was `MOTHERSUMI` (and names like it): one per formation that passed the hook's
`eligible + ADV` filter but was absent from `signals.liquid + fwd_ret_1m`. The hook's tradable
population therefore differed from `parity_check`'s. This is exactly the **second divergence
source flagged in F3** ("verify universe parity… `eligible`+ADV vs `signals.liquid`+`fwd_ret_1m`")
— *not* the round-2 "tracker-state action-type divergence" hypothesis, which turned out not to be
the cause. The lesson held: a traced cause beats a named mechanism.

## Verified for sign-off
- **A5 +0.0 bp** both windows — logically forced now that the population and the carried book are
  identical to `parity_check` (which == pre-registered research).
- **F3** — hook carries `_book_longs/_book_shorts` in its own state (`:408-409, 478-484`),
  matching `parity_check`'s carry-forward; no longer reconstructs from the tracker.
- **F2** — discharged; the real cause is the population filter, now fixed via `_load_fwd_names`.
- **Tests:** 52 green (`tests/portfolio` + `tests/signal_engine/carry` + `tests/strategies`).
- **Determinism:** hashes changed to `5dcfbf6e / 6cee5eb8` (expected — the book changed) and
  reproduce on re-run.
- **C1 / F1 / F5 / F6 / H1** — remain honored.

## Two non-blocking notes (documentation only)
- **NOTE-1 (footgun):** `signals_db_path` / `_load_fwd_names` filters on `fwd_ret_1m`, a
  forward-looking field. It is correctly opt-in and **armed only by `carry_paper_replay.py:195`**;
  `carry_paper_runner.py` does not pass it. Document it as **HISTORICAL-REPLAY-ONLY** — enabling
  it in forward/live would filter the universe by a field that does not exist yet for the current
  formation (trade-nothing / look-ahead). Verified not armed forward.
- **NOTE-2 (audit trail):** the report's earlier round-2 explanation (tracker-state divergence)
  was superseded by the traced cause (population mismatch). The final report should reflect the
  traced cause so the record is clean.

**Disposition:** production-metrics build ACCEPTED. Remaining housekeeping is documentation
(NOTE-1/2), a stale `CLAUDE.md` CARRY section (still says "substrate stage"), and the commit —
none blocking.
