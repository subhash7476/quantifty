# Options-Wall — the entry gate tests a different "pin" than everything else in the system

Investigation 2026-09-09, following the question *"why did Nifty take no trades today?"*
Answer: it was locked out by the pin-proximity gate, on **1,649 of 1,649 snapshots**, using a
pin the rest of the platform does not use and the operator never sees.

This is a **companion to** `OPTIONS_WALL_SENSEX_CHURN_AUDIT_2026-09-09.md` and the exact
inverse of it: Sensex was armed continuously and churned; Nifty was never armed at all. Both
are defects in the same screen.

---

## 1. Nifty's gates, every snapshot, all session

Replayed all 1,649 Nifty chain snapshots from
`data/options/wall_chain_snapshots/2026-09-09.duckdb` through the production path
(`OptionsAnalytics.build_structural_snapshot(..., dealer_side="inferred")` →
`ChainScanner._farm_screen`). Farm rows produced: **0**, matching the live record exactly.

| gate | passed |
|---|---:|
| regime is Positive | 1,418 / 1,649 |
| **`\|spot − pin\| ≤ 0.5%` — as the entry gate computes pin** | **0 / 1,649** |
| `\|spot − pin\| ≤ 0.5%` — as the dashboard computes pin | **1,649 / 1,649** |
| `atm_iv − rv ≥ 2.0` | 1,649 / 1,649 |
| `credit > 0` | 1,649 / 1,649 |

**Every gate passed except the pin gate, and the pin gate failed on every single snapshot.**
Had it used the pin the dashboard displays, Nifty would have been armed on 1,418 snapshots —
regime-limited, like Sensex.

---

## 2. There are two different pins, and they never agree

**The dashboard / regime river** (`engine._regime_snapshot`, `engine.py:104`) uses
`wall_metrics.pin_candidates`, which ranks strikes by **combined unsigned gamma mass**:

```python
score = {k: abs(ce_mass.get(k, 0.0)) + abs(pe_mass.get(k, 0.0)) for k in strikes}
```

**The entry gate** (`ChainScanner._pin_strike`, `chain_scanner.py:291`) uses the **argmax of
signed dealer exposure**:

```python
dist = structural.gex.gamma_by_strike       # signed: sign x mass, per inferred dealer side
return max(dist, key=lambda s: dist[s])
```

These are not the same quantity. The first asks *where is gamma concentrated* — the standard
pin notion. The second asks *at which strike are dealers most net-long gamma*, which under
`dealer_side="inferred"` depends on per-contract side inference and has no reason to sit near
spot.

**The engine itself treats the signed argmax as a degraded fallback** — `engine.py:106` reaches
for it only when `pin_candidates` returns `None`:

```python
pin = pins["pin"]
if pin is None and dist:
    pin = max(dist, key=lambda s: dist[s])       # fallback only
```

**The entry gate uses that fallback as its primary definition.** That is the defect in one
line.

### Today's numbers

| | entry-gate pin | dashboard pin |
|---|---|---|
| Value | 23,700 on 1,566 of 1,649 snapshots | **23,500 on all 1,649** |
| Median \|spot − pin\| | **0.7878%** | **0.1126%** |
| Inside the 0.5% band | 0 / 1,649 | 1,649 / 1,649 |

Spot ranged 23,431.50–23,569.70 all session. The entry gate pinned to 23,700 — a strike spot
never reached — and stayed there.

---

## 3. It is systemic, not a today-only glitch — and it is not DTE-driven

Sampled every 10th snapshot across four sessions and both indices, front expiry only:

| session | index | DTE | snaps | entry-pin in band | dash-pin in band | pins agree |
|---|---|---:|---:|---:|---:|---:|
| 2026-09-04 | NIFTY | 4 | 78 | 85% | 100% | 4% |
| 2026-09-04 | SENSEX | 6 | 79 | 89% | 96% | 6% |
| 2026-09-07 | NIFTY | 1 | 156 | 21% | 100% | 1% |
| 2026-09-07 | SENSEX | 3 | 156 | **3%** | 43% | 6% |
| 2026-09-08 | NIFTY | 0 | 129 | 64% | 100% | 1% |
| 2026-09-08 | SENSEX | 2 | 129 | 22% | 82% | 11% |
| 2026-09-09 | NIFTY | 6 | 165 | **0%** | 100% | **0%** |
| 2026-09-09 | SENSEX | 1 | 166 | 32% | 100% | 0% |

Two things to take from this:

- **The two pins essentially never agree — 0–11% across all eight combinations.** The
  divergence is permanent and systemic, not an artifact of one chain.
- **The entry-gate pin's admit rate is erratic: 0%, 3%, 21%, 22%, 32%, 64%, 85%, 89%.**

**A prediction I stated and the data refuted:** I expected the divergence to be DTE-dependent
— hidden near expiry where gamma concentrates at ATM, biting at longer DTE. It is not.
Nifty went 85% at DTE 4, 21% at DTE 1, 64% at DTE 0, 0% at DTE 6. There is no monotone
relationship. The honest characterization is weaker and worse: **the pin-proximity gate admits
an essentially arbitrary fraction of the session, uncorrelated with anything an operator can
see.** It is not a tuned gate; it is a coin flip with a session-length memory.

This also means the prior days' farm rows (348 / 113 / 297 on 09-04 / 09-07 / 09-08) were not
evidence the gate worked — they were the coin landing the other way.

---

## 4. Why this matters more now, not less

The churn audit's fix (D) — demoting `regime_flip` from an exit to a no-new-entry condition —
is now applied. That changes the risk of "fixing" the pin gate, in both directions:

- **Before (D):** correcting the pin would have armed Nifty on ~1,418 snapshots and, under the
  old exit rule, produced exactly the Sensex churn pattern on a second index. Fixing the pin
  first would have made the day worse.
- **After (D):** an armed index takes roughly one position and holds it to TP / SL / time-stop.

So the ordering matters and it is already correct: **(D) first, pin second.** But the pin
change should still not ride along silently with the exit change — it materially alters which
indices trade at all, and it deserves its own decision and its own observation window.

---

## 5. Options

**A. Point `ChainScanner._pin_strike` at `wall_metrics.pin_candidates`.** Makes the entry gate
test the same pin the dashboard, the regime river and the engine's own primary path already
use. This is a **consistency fix, not a tuning change** — it does not invent a new definition,
it adopts the one the system already treats as authoritative. Keep the signed argmax as the
same fallback the engine uses when `pin_candidates` returns `None`.

  **Scope warning for whoever implements this: it is not a one-line change.**
  `ChainScanner._pin_conviction` (`chain_scanner.py:297`) computes its own conviction from
  `gamma_by_strike` — the same signed series — while `pin_candidates` already returns
  `conviction` and `margin` off the unsigned mass. Switching the pin without switching the
  conviction leaves the screen ranking on one basis and gating on another, which is how this
  defect arose in the first place. Whether the two conviction numbers currently disagree the
  way the two pins do is **unmeasured** — check it as part of the change, not after.

**B. Leave it, and widen `pin_band_pct` instead.** Rejected on the evidence: today's entry-gate
pin sat 0.79% from spot with spot never within 200 points of it, so the band would have to
widen past 0.8% to admit anything — and at that width it stops being a pin-proximity test at
all. Widening a band around the wrong centre is not a fix.

**C. Do nothing.** Defensible only as a deliberate "one index at a time" pilot stance. It
should then be recorded as a choice, because right now the platform behaves as though Nifty is
eligible — it renders a Nifty tab, computes a Nifty regime, and shows a Nifty pin 0.11% from
spot — while the entry gate has silently excluded it all session.

**Recommendation: (A), as a separate change, after (D) has been observed for at least one
session.** The two should not be evaluated in the same window.

---

## 6. Caveats

- Four sessions, two indices, front expiry only. The §3 table samples every 10th snapshot.
- §1 is a full-session replay (all 1,649 snapshots) and reproduces the live outcome exactly
  (0 farm rows), so the "0 / 1,649" figure is not a sampling artifact.
- No claim is made that arming Nifty would have been *profitable* today — only that the gate
  excluding it is not measuring what it purports to measure.
- The replay reconstructs `realized_vol` as a session constant (5.44) rather than recomputing
  it per cycle. This cannot change the conclusion: the IV−RV gate passed 1,649/1,649 with
  margin, and the pin gate failed 1,649/1,649 independently of RV.

## Reproduction

- Chains: `data/options/wall_chain_snapshots/{2026-09-04,07,08,09}.duckdb`
- Live farm-row counts: `wall_scan_results.duckdb` → `scan_results`, `screen='premium_farm'`
- Entry-gate pin: `ChainScanner._pin_strike` (`core/analytics/chain_scanner.py:291`)
- Dashboard pin: `wall_metrics.pin_candidates` (`core/analytics/wall_metrics.py:56`)
