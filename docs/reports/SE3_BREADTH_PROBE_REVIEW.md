# SE-3 Breadth Probe — Lead Review (Round 1)

**Reviewer:** Claude (review only, per standing role split)
**Implementer:** DeepSeek V4
**Date:** 2026-08-05
**Reviewed:** `scripts/se3/breadth_probe.py`, `tests/se3/test_breadth_probe.py`,
`docs/reports/SE3_BREADTH_PROBE_REPORT.md`
**Against:** `docs/reports/SE3_BREADTH_PROBE_PROMPT.md`

---

## Verdict

**Implementation ACCEPTED. Measurement NOT yet accepted — one corrective run required
before the ladder reading may be used.**

The implementation is faithful to the prompt on every pinned point I checked. **The defect
is in the prompt, not the code.** §3.9 pinned a same-day IC construction that this
repository has already diagnosed as contaminated in an almost identical setting, and §1.4
("no tuning") correctly prevented the implementer from deviating from it. The implementer
did the right thing; I specified the wrong thing.

The consequence is narrow but it lands on the one number the probe exists to produce.

---

## CRITICAL-1 — The IC is measured in the contaminated same-day form. `sd_IC` is therefore unconfirmed.

### The mechanism

`scripts/se3/breadth_probe.py:659-671` computes, per `(date, name)`:

```
richness_A = residual of IV_t on rv_t      # IV_t is inverted from settle V_t
dh_return  = (V_{t+1} - V_t) - Delta_t * (F_{t+1} - F_t)
```

`V_t` enters the **signal with a positive sign** (a higher settle inverts to a higher IV,
hence higher measured richness) and the **return with a negative sign**. Any noise in
`V_t` — settle bounce, a stale print, a wide bid-ask struck at one side — therefore
induces a **mechanically negative** correlation between richness and forward return,
independent of any real effect.

### This is a known defect in this repo, with a known remedy

`CLAUDE.md` §OSC records the identical finding on the index option surface:

| OSC measurement | Value |
|---|---|
| Same-day IC (contaminated) | **−0.0615**, t = −8.49 |
| Bounce-artifact contribution | **−0.0813** — larger than the measurement, sign-reversing |
| Skip-a-day IC (clean level) | **+0.0198**, sd 0.2068 |

The remedy already exists and is already tested: the D-2 **double-lag** construction in
`scripts/osc/regime_diagnostic.py`, with tests in `tests/osc/test_regime_diagnostic.py`.

### Why SE-3's numbers are consistent with the artifact dominating

SE-3's `mean_IC = −0.1298` at `t = −14.64` is **more than twice OSC's contaminated
magnitude**. That is the direction you would predict: single-stock option chains are
thinner than NIFTY's, with wider spreads and staler settles, so the bounce term should be
*larger* here, not smaller. A genuine daily cross-sectional rank IC of −0.13 would be
extraordinary — roughly 4× CB-N50's TRAIN +0.059 and 8× OSC's honest within-moneyness
+0.0167. **The prior strongly favours artifact over discovery.**

The implementer's note that `mean_IC` must not become the δ anchor is correct and
sufficient for §7/§8. **But it does not dispose of this finding**, because the probe's
entire purpose is `sd_IC`, and `sd_IC` is computed from the same contaminated series. The
open question is not "is the mean wrong" (it is) but **"is the dispersion affected?"**

That is not answerable from the current run. A roughly constant artifact shifts the mean
and leaves `sd` intact; an artifact that scales with spread and liquidity conditions —
which widen in stress — inflates `sd`. Both are plausible and they imply different ladder
readings.

### P5 is now uninformative

P5 ("`mean_IC` for variant A is negative") is recorded HELD. It cannot count as evidence:
the contaminated estimator returns a negative sign **by construction**, so P5 was
unfalsifiable as written. This weakens the "10/10 HELD" summary — it is 9 informative
predictions and one that could not have failed. Not the implementer's error; P5 was mine.

### Required corrective run

Re-run with the **skip-a-day (double-lag)** construction — richness at `t`, delta-hedged
return over `t+1 → t+2` — and report `sd_IC` **side by side** with the same-day value for
both variants. Everything else stays pinned. Same burned window, no new data, **no purity
cost.**

### How much movement would actually change the answer

Worth stating before the re-run so the result cannot be read post-hoc. Ladder boundaries at
`ncp_req = 2.802`:

| Reading | n | √n | Green iff `sd_IC` ≤ | Amber iff ≤ | Red-amber iff ≤ |
|---|---|---|---|---|---|
| Permissive | 1,701 | 41.24 | **0.2207** | 0.2943 | 0.4267 |
| Strict | 495 | 22.25 | **0.1191** | 0.1588 | 0.2303 |

Measured `sd_IC(A) = 0.1938`. So:

- **Permissive (n=1,701):** Green survives until `sd_IC` exceeds 0.2207 — headroom of
  **+13.9%** over the measured value. For calibration, OSC's *clean* skip-a-day `sd` was
  0.2068, which would still be Green here.
- **Strict (n=495):** already Red-amber, and would need `sd_IC ≤ 0.1588` (a **−18.1%**
  move) to reach Amber. A correction that *raises* `sd` cannot change this rung until
  0.2303.

**The likely outcome is that the reported verdict survives the fix.** That is a reason to
run the check cheaply, not a reason to skip it — "probably robust" is not a measurement,
and this is the number the eventual RFA declaration inherits.

---

## MEDIUM-1 — P9's attrition rate understates leg-level attrition

`breadth_probe.py:1003` computes:

```
pairing_attr = pairing_dropped / (stock_after_iv + pairing_dropped)
```

`pairing_dropped` increments only when an entire `(date, name)` unit fails — missing
forward at `t+1` (line 652), or **neither** leg pairing (line 669). A cell that fails to
pair individually hits `continue` at line 663 and is **never counted**: if the call leg
vanishes but the put survives, the name stays in the panel and nothing is recorded as
attrition.

So the reported **0.1%** is the rate at which *names* drop out, not the rate at which
*cells* fail to pair. The prompt's §3.7 asked for the cell-level rate, and explicitly said
why: *"cells that fail to trade on `t+1` do not fail at random."*

**Impact: reporting only.** The IC and breadth computations are unaffected — the surviving
leg is a legitimate observation. But P9 is currently answering a different and much easier
question than the one asked, and the near-zero value invites a false read that
single-stock chains pair almost perfectly. Add a separate leg-level counter and report
both.

---

## MINOR-1 — `N_eff = 5.9` is plausibly biased upward by the same bounce noise

The breadth panel is built from `dh_return_scaled`, which carries the `V_t` noise term.
That noise is largely **idiosyncratic per name**, so it dilutes cross-name correlation:
`rho_bar` is pushed down and `N_eff` up. The measured `rho_bar = 0.150 → N_eff = 5.9` may
therefore flatter true effective breadth.

I verified the arithmetic is internally consistent: `N_eff = N / (1 + (N−1)·0.150) = 5.9`
implies `N ≈ 43.6`, which matches the reported ~44 names and the demeaned artifact value
of 44.1. **The formula is implemented correctly** — this is a bias in the input panel, not
an error in the computation.

The skip-a-day re-run does not fix this (the noise is in the return, not the lag). Record
it as a stated direction of bias: **5.9 is an upper estimate.** It does not threaten the
headline conclusion, which is that breadth sits between OSC's 1.9 and nominal ~45 — that
survives a downward correction comfortably.

---

## What I checked and found correct

| Prompt requirement | Status |
|---|---|
| §1.1 fence `2023-01-02 → 2025-12-31`, both legs | Held; min/max reported per source |
| §1.2 warmup from inside the fence | Held; first formation date computed, not hardcoded |
| §1.7 Black-76 imported from `scripts/osc/sd_probe.py`, not reimplemented | Held |
| §3.4 traded filter at `t` (`contracts > 0 AND open_int > 0`) | Held |
| **traded filter re-applied at `t+1`** | **Held** — line 640 keys the lookup off `stock_traded`, not the raw frame. This was my primary suspicion given the 0.1% attrition; it is clean. Settle prices for untraded strikes never enter a return. |
| §3.1 MCWB month-`M` → month-`M+1` application | Held, tested (4 tests) |
| §3.1 `DUMMY*` exclusion, `TMPV` guard | Held |
| §3.5 roll-day return exclusion | Held, tested (2 tests) |
| §3.10 raw `N_eff` as headline, demeaned labelled as artifact | Held — warning text present verbatim at line 929 |
| §5 ladder via `power.n_required`, both `n`, not hardcoded | Held |
| Read-only, nothing written under `data/` | Held |

The "Green permissive / Red-amber strict" split is exactly the outcome §5 pre-registered as
likely, and reporting it as a split rather than picking one is correct.

---

## Disposition

1. **Run the skip-a-day corrective** (CRITICAL-1). Report `sd_IC` same-day vs skip-a-day,
   both variants, against the boundary table above.
2. **Add the leg-level pairing counter** (MEDIUM-1) and report both rates.
3. **Record the `N_eff` upward-bias direction** (MINOR-1) in the report — one sentence, no
   re-run.
4. Do not change any other pinned parameter. Do not re-read any window.
5. The ladder reading stands as **provisional** until (1) lands.

**Nothing here touches the preserved windows.** The 1,701-date index-option window and the
2021–2022 joint-clean stock window remain untouched, as the report confirms.
