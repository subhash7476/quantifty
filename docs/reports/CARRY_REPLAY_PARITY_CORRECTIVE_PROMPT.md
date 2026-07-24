# Corrective Prompt — Carry Replay Parity: the TRAIN failure is `max_bars`, not the data path

**To:** DeepSeek. **From:** Claude (review). **Date:** 2026-07-24.

---

## 0. Verdict on the attempt

**The FAIL was real and correctly reported — good.** But the *diagnosis* is wrong, and the cause is
a **one-line harness bug in your own script**, not a driver, provider, or data-path defect.

`CARRY_REPLAY_IMPLEMENTATION_ATTEMPT.md` attributes it to "the TRAIN window's data path or driver
termination conditions." It is neither. **The replay infrastructure is correct and needs no further
debugging.**

---

## 1. Root cause — `replay_parity_check.py:451`

```python
max_bars=100000,  # Increased to ensure we cover all formations
```

The comment states the intent; the value defeats it. `max_bars` counts **bars**, not ticks or
formations — and one TRAIN tick serves ~180 bars across 229 symbols.

Measured directly against the real provider:

| Quantity | Value |
|---|--:|
| TRAIN symbols / trading days / formations | 229 / 1,173 / 58 |
| Bars needed for a **full** TRAIN replay | **209,997** (**2.1× the cap**) |
| Ticks reachable under `max_bars=100000` | 521 of 1,173 |
| Replay stops at | **2018-05-10** |
| **Formations reachable** | **26** ← your report says 26 |
| **Formations missed** | **32** ← your report says 32 |
| Last reached formation | 2018-04-30 |
| Bars needed for full **HOLDOUT** replay | **69,333** — *under* the cap |

**Both numbers reproduce exactly.** TRAIN needs 2.1× the cap and truncates; HOLDOUT fits underneath
it and completes. That is the entire asymmetry — nothing about TRAIN's data path differs.

Note also: HOLDOUT passed with only 1.4× headroom. It succeeded by luck, not by design.

---

## 2. The fix

Set `max_bars` so it cannot bind. Either is acceptable:

- `max_bars=None` — the calendar-driven provider now terminates naturally when the calendar
  exhausts, so no cap is needed; **or**
- a generous explicit bound (e.g. `500_000`) as a cheap safety net against an `advance_tick()`
  regression, which would otherwise loop forever.

**Prefer the explicit generous bound.** A regression in `advance_tick()` produces an infinite loop,
not a crash (measured: the driver replays a single date forever), and a bound converts that hang
into a terminating failure.

**Do not** hand-tune the cap to "just fit" TRAIN. That reintroduces the same class of bug the next
time the universe or window grows.

---

## 3. Re-run instructions

1. Fix line 451.
2. Re-run **both** windows from scratch. Do not reuse any cached result from the truncated run.
3. **Re-check §4.2 book identity after the fix, do not debug it separately.** The reported book
   differences are almost certainly a *downstream artifact* of the truncation — comparisons against
   32 formation dates the replay never reached cannot be meaningful. Treat §4.2 as unmeasured until
   §4.1 is clean.
4. All original constraints from `CARRY_REPLAY_PARITY_PROMPT.md` still stand unchanged: SEALED not
   read; constants (`GROSS_EXPOSURE = 10_000_000.0`, `SLIPPAGE_BP = 5`, 15 bp tolerance) not
   re-derived; production code imported not copied; `gate_pass` drives both verdict and exit code;
   two runs must be identical; no construction parameter touched.
5. State the §5 predictions again **before** the re-run.

---

## 4. Process note — worth internalising

The symptom (26/58 TRAIN, 24/24 HOLDOUT) contained the diagnosis. A window that fails while a
*shorter* window of the same code succeeds points at a **size-dependent limit**, not at logic — and
the only size-dependent knob in the harness is `max_bars`. Checking the arithmetic (`bars needed`
vs `cap`) takes one query and would have located this before it was written up as an infrastructure
problem.

The general form, and this track keeps meeting it: **when a failure is asymmetric across two
windows running identical code, suspect a bound, a cap, or a limit before suspecting the data.**

Everything else in the attempt — the harness structure, the parity hook, the date-set pre-check that
*caught* this — worked as designed. §4.1 did exactly the job it was put there to do.
