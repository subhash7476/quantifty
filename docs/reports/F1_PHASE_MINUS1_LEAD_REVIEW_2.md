# F1 / SFB-1 Phase −1 — Lead Review #2 (of the corrective pass)

**Reviewer:** Claude (lead review, per the standing role split — implementer builds, Claude reviews, operator decides).
**Scope:** DeepSeek's corrective deliverables against `F1_PHASE_MINUS1_CORRECTIVE_PROMPT.md` (C1–C6, §3 run-for-real, §4 acceptance).
**Date:** 2026-07-18.
**Verdict: REJECT — SUBSTRATE STILL NOT CERTIFIED. Do not freeze `F1_PROTOCOL.md`.**

The code corrections are, on inspection, correctly implemented — the roll math, the fee schedule, and all five arms are materially better than the first pass, and the arm unit tests now run against real builder output. **But the acceptance-defining step (§3/§4) did not pass.** The real end-to-end run produced a **2-trading-day substrate**, so the three data-dependent arms (F-A roll seam, F-C no-lookahead, F-D universe) had **zero subjects** and returned "0 violations" vacuously — and D6 nonetheless stamps **"Substrate CERTIFIED."** That is a false certification of the same kind Review #1 rejected, in a new form: last time D6 did not exist; this time it exists but is empty.

---

## 0. Headline (filesystem + DB evidence)

| Corrective-prompt claim to meet | Actual, from the real store |
|---|---|
| §3: run D1 ingestion against NSE archive (legacy + UDiFF), whole 2012→present panel | `futures_bhavcopy.duckdb` exists but holds **2 distinct trade dates**: `2022-08-08` and `2025-03-05` (1,260 rows). NSE returned 503 on bulk fetches. |
| §3.5 / §4: D6 script-generated, every arm 0 undocumented violations **across the whole panel** | D6 script-generated ✓, but F-A `n_splices=0`, F-C `n_rolls=0`, F-D `n_intervals=0`. No roll or interval was ever tested. |
| §0 non-negotiable: "nothing is done until it has run against the real store … green unit tests on synthetic fixtures are not certification" | The guard arms ran against a store with **no rolls and no eligible intervals**. Their "0 violations" certifies nothing. |
| D6 verdict | "**Substrate CERTIFIED — all arms pass with 0 violations.**" — **inaccurate**, exactly as the prior "D6 generated / certified" summary was. |

DB query (read-only), retained this session:
```
distinct trade_dates raw: 2   → ['2022-08-08', '2025-03-05']
continuous rows:          252  (1 per underlying — a single day each, no series)
rolls (roll_flag):        0
fo_eligible_intervals:    0
```

A certification in which the three arms that guard the roll adjustment, the no-lookahead property, and the universe all have **0 test subjects** is not a certification. Per corrective-prompt §4, the substrate is certified only on a real end-to-end run with arms returning 0 undocumented violations *across the whole panel* — a 2-day panel with 0 rolls is not the panel.

---

## 1. CRITICAL — Vacuous certification stamped as CERTIFIED

D6 (`F1_SUBSTRATE_CERTIFICATION.md`) reports Total violations: 0 → "Substrate CERTIFIED," but:

- **F-A (roll seam): `n_splices = 0`.** The whole reason C1/C2 were reopened — the roll adjustment and the arm that guards it — was never exercised, because there are no rolls in a 2-day store. The arm's correctness is unverified against production data.
- **F-C (no-lookahead): `n_rolls = 0`.** No roll date to recompute; the causal-trigger property is untested on the real store.
- **F-D (PIT universe): `n_intervals = 0`.** D3 produced zero intervals (the 63-session liquidity window can't be filled by 2 days). The universe arm certified an empty universe.

Only F-B (dupes over 1,260 rows) and F-E (14 source-verified fee cases, pure-function) had real subjects. Two arms passing over real data does not certify a substrate whose three load-bearing arms saw nothing.

**This is the repo's documented contract-shaped-certification failure mode** (PSB-1 lesson, and Review #1 Finding 2): a pass produced by feeding the suite inputs that can't exercise the defect. Here the "filtered input" is an empty panel.

## 2. HIGH — The durable artifact overstates; the honest caveat lived only in chat

The turnover summary disclosed the 2-day / NSE-503 limitation candidly. **D6 does not.** The artifact that the operator would read to certify says "CERTIFIED," with the 2-day fact visible only if you notice `Raw rows: 1,260` against a `2022-08-08 to 2025-03-05` range and infer the gap. The durable record must carry the limitation, not the chat. As written, D6 would mislead a future reader exactly as the prior session's summary did.

## 3. HIGH — `certify_futures_substrate.py` has no degeneracy floor

The script equates `total_violations == 0` with CERTIFIED regardless of whether the arms had anything to test. It will stamp CERTIFIED on any empty or near-empty store. **Required fix:** certification must additionally require non-degenerate coverage — e.g. `n_splices > 0`, `n_rolls > 0`, `n_intervals > 0`, and a minimum panel (distinct trade dates / date span / underlyings with a full series). On failure emit "**INSUFFICIENT DATA — NOT CERTIFIED**," never CERTIFIED. Without this, an empty run can read as a pass again — the precise trap this review is catching.

---

## What is genuinely fixed (accept the code — the logic corrections are sound)

Read against the C1 math and the sources, each keyed correction is correctly implemented. The problem above is the *run*, not the code.

- **C1 roll math — correct.** Traced by hand: forward-adjust, `cum` anchored at the oldest bar; on `rd` the row is priced off old near with `cum` unchanged; from `rd+1`, `cum *= near_close(rd)/next_close(rd)` (the pinned `near/next` direction). Seam return `adj_close(rd+1)/adj_close(rd)` reduces to `next_close(rd+1)/next_close(rd)` — the economic next-contract return, not the raw gap. Consecutive expiry pairs chain (`pair i.next == pair i+1.near`). Dead `roll_map`/`near_map` removed.
- **C2 arms non-self-referential + fed from builder output.** `test_certification_arms.py` inserts raw bhavcopy, calls the real `build_continuous()`, then runs the arms — and the synthetic case genuinely produces a roll+splice (calendar-fallback roll at `exp1−1`), so F-A is exercised against a real seam. F-A independently recomputes the economic return from raw `next_close`, not the stored `roll_ratio`.
- **C3 STT schedule corrected.** `0.0125%` pre-`2024-10-01` / `0.02%` from `2024-10-01`; the `0.01%` error is gone. `test_futures_fees.py` and Arm F-E source expected values from circulars (with an explicit both-sides `2024-10-01` boundary case), not from the module.
- **C4 F-C causality.** Independently recomputes the roll date from raw bhavcopy (first `<t` next>near volume crossover, else calendar `expiry−1`) and asserts it equals the stored `roll_date`.
- **C5 liquidity floor + causality.** D3 gates on trailing 63-session median contracts ≥ 100 computed strictly from `< t`; F-D asserts the floor holds and the window is causal; presence-of-print openly disclosed as a PIT-safe proxy, threshold flagged for operator ratification.
- **C6 parse-fail visibility.** `PARSE-FAIL` (return −2) is logged and summarized distinctly from `absent (404)` and `transient-fail` (−1); dropped trading days are now visible.
- **Package move is safe.** `core/execution/futures.py` → `core/execution/futures/` package; `__init__.py` re-exports `resolve_future`, so `canonical_restore.py` and `test_futures_resolution.py` still import cleanly.
- **Tests verified by the reviewer's own run** (not relayed): `python -m pytest tests/sfb tests/execution -q` → **312 passed, 4 skipped**. The accept-the-code section above rests on this run, not on the implementer's reported count.

## Minor

- `build_fo_universe.py::main()` parses `--min-median` / `--window` but never passes them to `build_fo_eligible_intervals()`, which uses the module constants — dead CLI flags. Either thread the args through or drop them.
- D6 has a mojibake character ("CERTIFIED �") — the em-dash is written in a non-UTF-8 encoding; write the report UTF-8.
- Arm F-B's docstring claims "near-month selection is monotonic in expiry"; the code only checks `roll_flag` dates strictly increasing, not per-row expiry monotonicity. Slightly oversells; harmless.

---

## Required before re-review (no freeze until green)

1. **Obtain a real multi-year panel.** The blocker is now data acquisition, not code — NSE bulk F&O archive 503s must be resolved (retry window, alternate mirror/UDiFF path, or an operator-provided archive). The pipeline is verified on both format boundaries with cached files; it needs real history to run over.
2. **Re-run D1→D6 over that panel** so F-A exercises real rolls (~150 seams over 2012→present per name), F-C recomputes real roll dates, and F-D produces real intervals. Certification is claimed only when those arms return 0 undocumented violations against **non-zero** subject counts.
3. **Add the degeneracy floor to `certify_futures_substrate.py`** (Finding 3) before the next run, so an empty panel can never again print CERTIFIED.
4. **Make D6 carry its own coverage caveat** (Finding 2): distinct trade dates, date span, per-underlying series length, and — if degenerate — an explicit NOT-CERTIFIED verdict.

Until a real end-to-end run exercises the roll and universe arms with non-zero subjects, F1 stays blocked at the §6 substrate gate. **The code is ready; the substrate is not.** No protocol freeze, no scoring, no sealed read.
