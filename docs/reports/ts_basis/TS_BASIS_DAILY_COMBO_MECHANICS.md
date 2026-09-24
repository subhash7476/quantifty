# TS Basis Daily Combo — How It Works

**Companion to:** `TS_BASIS_DAILY_COMBO_SPEC.md` (definition) and
`TS_BASIS_DAILY_COMBO_BUILD_REPORT.md` (implementation evidence).
**Status note:** the combo is a 59-day, in-sample-filtered observation on a
research-only sleeve. Paper is its confirmatory surface — nothing here promotes it.

---

## 1. The two filters and why they combine

**F1 — Recovery (`basis_reverting`, in-repo).** Basis is assumed persistent
(TS Basis bets a wide basis keeps outperforming within the month). When a
|z|>0.7 dislocation is already shrinking day-on-day
(`dbasis1 × sign(z) ≤ 0`), the persistence thesis is locally broken — the move
already happened. Validation (TRAIN/VAL/HOLDOUT, pre-July): rejecting reverting
names lifted HOLDOUT quintile spread +5.75pp, 10/10 sectors consistent, ~20% of
strong-z flagged. In Jul–Sep paper window: ~15% of legs flagged (20.6% full-history).

**F2 — Conviction (|z_ts| > 0.7).** The sleeve's own TRAIN terciles put edge in the
strong zone (<0.30 weak / 0.30–0.70 mid / >0.70 strong). Quintile legs always
contain weak names (tails of the middle distribution on low-dispersion days);
F2 cuts them. Jul–Sep: keeps ~82% of legs on average — but only ~25% on
compression days (e.g. 09-24 monthly expiry: 158/210 names |z|≤0.7).

**Why AND, not either:** F1 removes stale edge (shrinking dislocations), F2 removes
thin edge (weak dislocations). Either alone keeps one noise type: conviction-only
still trades strong-but-reverting names; recovery-only still trades weak names.
Jul–Sep gross: unfiltered +11.70% → recovery +14.12% → conviction +24.57% →
**combo +33.32%**. Costs run opposite (turnover 0.48 → 0.64 → 0.51 → 0.72
one-way); net of the ~13 bps/day-per-unit-turnover drag: ≈ +6 / +6 / +24 / +30 bps/day.

## 2. Evidence recap (59 formations, 2026-07-01 → 2026-09-22, equal-weight legs)

| Variant | Comp | JUL | AUG | SEP | Long leg | Short leg |
|---|---|---|---|---|---|---|
| Unfiltered (42L/42S) | +11.70% | +7.7% | +4.0% | −0.3% | +4.68% | −6.33% |
| Combo (~26L/29S) | +33.32% | +25.5% | +5.8% | +0.4% | +20.04% | −9.97% |

(Short-leg negative = shorts profitable.) Supertrend(10,3) gating was also tried on
the same window: +8.93%, worse than unfiltered — trend-chasing adds churn without
pay here. A high-vol exclusion was tried: +11.10%, no effect. All variants reported;
m≈6 with no α — the combo is the best hypothesis, not a finding.

## 3. Concentration autopsy (read before sizing anything)

- **July is the result:** 25.5pp of 33.3pp; combo ran 100 bps/day in July vs 17 after.
- **Best days ran skeletal long legs:** 07-30 +3.59% on **2 longs**, 07-08 +3.54%
  on 5, 07-31 +1.43% on 3. Ex-best-day still +28.7%, so not one fluke — but a
  2-stock leg is stock-picking, not a factor book.
- **Worst days are contained:** 09-18 −0.84%, 08-31/09-01 −0.47% each.
- Paper legs will look like this by rule: 9–30 longs/day observed range. Anyone
  supervising should expect single-name days and judge them as drawn, not as faults.

## 4. Live behavior to watch (first paper weeks)

1. **Pass rates:** ~26L/29S normal; <15/side on compression days (expiry weeks).
   Persistent <10-leg books outside expiry weeks = regime change, report it.
2. **Turnover:** ~0.7 one-way expected (reverting flag flickers). Sustained >0.85
   with flat gross = the filter churning without pay — the Supertrend failure mode.
3. **Fee drag:** ~18–19 bps/day at current churn; gross must clear ~2× drag to
   matter. Track net, not gross.
4. **Leg asymmetry:** combo keeps more shorts than longs on average (29.4 vs 26.4).
   A persistent long-leg drought in a rally = the documented concentration
   property, not a data fault — unless legs hit zero (spec §4 hold rules).

## 5. What would validate or kill it

- **Validate:** 1–2 forward months matching backtest pass rates/turnover with net
  > 0 after the ~18 bps/day drag, on frozen rules (0.7, reverting definition,
  quintile legs — no re-tuning).
- **Kill:** forward net ≤ 0 over a full expiry cycle (~1 month covers compression
  + normal), or turnover persistently above backtest with no gross to cover it.
- **Never:** re-tuning thresholds on paper P&L and re-reading the same window.
  The next parameter change starts a new pre-registration with a fresh window.
