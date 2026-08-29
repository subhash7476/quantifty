# Sleeve Combination Matrix — SSF monthly cross-section

**Script-generated** — `scripts/signal_engine/combination/sleeve_pair_matrix.py`. Code commit `0b67a35`.

**What this is:** arithmetic on already-measured quantities from the built signal stores. No new data read, no sealed window touched — the same standing as `IVOL_COMPOSITE_CHECK_REPORT.md`. **Decision-support, not a gated read.**

**Fence proven:** every query filters `formation_date <= 2022-12-31`; the maximum formation date actually used across all sleeves is **2022-12-30**. SEALED (2023-01-01 → present) is untouched.

**Conventions:** per-formation Spearman rank IC vs `fwd_ret_1m`; MIN_NAMES=5; IR = |mean IC| / SD(IC); power projected at n\*=42 (one-sided, α=0.05). Forward returns come from ONE canonical source (`ivol/signals.duckdb`) for every sleeve, so all ICs are measured against identical returns.

**Sleeves in scope:** the six SSF **monthly** cross-sectional sleeves whose formation grids align exactly (71 common month-end formations in the fenced window). TS_BASIS is read from `ts_basis/ts_signals_monthly.duckdb` — the **registered monthly** grid, built by `build_ts_signals.py --source monthly`. The default `ts_signals.duckdb` is a weekly variant (349 fenced formations on a Friday grid) and is not the registered construction.


---

## 1. Standalone sleeves (own full fenced span: TRAIN + HOLDOUT)

| Sleeve | Formations | Span | Mean IC | SD(IC) | IR | t | Power @ n*=42 | Registered sign |
|---|--:|---|--:|--:|--:|--:|--:|---|
| CARRY | 71 | 2017-02-28 → 2022-12-30 | +0.0479 | 0.0799 | 0.5995 | +5.05 | 0.9852 | REGISTERED (v2 pre-reg, positive) |
| TS_BASIS | 71 | 2017-02-28 → 2022-12-30 | +0.0534 | 0.1031 | 0.5181 | +4.37 | 0.9512 | REGISTERED (pre-reg, positive) -- SEALED de-authorized (gate defect) |
| IVOL | 71 | 2017-02-28 → 2022-12-30 | -0.0420 | 0.1513 | 0.2777 | -2.34 | 0.5497 | REGISTERED (pre-reg, negative) -- FLIPPED on SEALED |
| SKEW | 71 | 2017-02-28 → 2022-12-30 | -0.0245 | 0.1165 | 0.2099 | -1.77 | 0.3795 | NONE -- two-sided registration; sign is a TRAIN reading |
| LAG | 71 | 2017-02-28 → 2022-12-30 | -0.0207 | 0.1357 | 0.1525 | -1.28 | 0.2505 | REGISTERED (pre-reg, positive) -- TRAIN came out NEGATIVE |
| TREND | 71 | 2017-02-28 → 2022-12-30 | +0.0180 | 0.1436 | 0.1251 | +1.05 | 0.1984 | REGISTERED (pre-reg, positive) |

---

## 2. Pairwise combination matrix

Sign alignment uses each sleeve's **registered** sign (SKEW has none — treated as `+1`, which is why its rows carry a sign-provenance warning in §2.1).

`Lift` = composite IR ÷ better standalone IR **on the same intersection**. **Lift ≤ 1.00 means the pair is worse than its own best leg.**

| Pair | Common form. | Mean names | ρ(signal) | ρ(IC) | IR a | IR b | Quadrature | IR composite | Lift | Composite power | Best-leg power |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| LAG + SKEW | 71 | 80 | -0.0780 | -0.0637 | 0.2108 | 0.2340 | 0.3149 | **0.3021** | **1.291** | 0.6104 | 0.4389 |
| TS_BASIS + IVOL | 71 | 145 | -0.0033 | +0.0460 | 0.5181 | 0.2423 | 0.5719 | **0.5304** | **1.024** | 0.9586 | 0.9512 |
| CARRY + TS_BASIS | 71 | 145 | +0.6172 | +0.5344 | 0.6657 | 0.5181 | 0.8435 | **0.6566** | **0.986** | 0.9944 | 0.9953 |
| CARRY + IVOL | 71 | 166 | -0.0358 | +0.0896 | 0.5995 | 0.2597 | 0.6533 | **0.5562** | **0.928** | 0.9713 | 0.9852 |
| TREND + IVOL | 71 | 154 | -0.1676 | -0.6122 | 0.1251 | 0.2846 | 0.3109 | **0.2354** | **0.827** | 0.4426 | 0.5672 |
| CARRY + TREND | 71 | 153 | -0.0391 | -0.2432 | 0.6510 | 0.1153 | 0.6612 | **0.4978** | **0.765** | 0.9367 | 0.9938 |
| TS_BASIS + TREND | 71 | 145 | -0.0135 | +0.0364 | 0.5222 | 0.1334 | 0.5389 | **0.3963** | **0.759** | 0.8107 | 0.9538 |
| IVOL + LAG | 71 | 145 | +0.3093 | +0.5210 | 0.2964 | 0.1525 | 0.3333 | **0.1980** | **0.668** | 0.3508 | 0.5964 |
| CARRY + SKEW | 71 | 88 | -0.6329 | -0.5085 | 0.3326 | 0.2099 | 0.3933 | **0.1621** | **0.488** | 0.2705 | 0.6825 |
| TS_BASIS + LAG | 71 | 137 | +0.0059 | -0.1114 | 0.5084 | 0.1651 | 0.5346 | **0.2164** | **0.426** | 0.3954 | 0.9446 |
| TS_BASIS + SKEW | 71 | 83 | -0.3970 | -0.4865 | 0.3765 | 0.2784 | 0.4683 | **0.1529** | **0.406** | 0.2514 | 0.7748 |
| CARRY + LAG | 71 | 144 | +0.0185 | +0.1947 | 0.6719 | 0.1396 | 0.6862 | **0.2231** | **0.332** | 0.4119 | 0.9958 |
| IVOL + SKEW | 71 | 88 | +0.0102 | +0.0305 | 0.2707 | 0.2099 | 0.3425 | **0.0883** | **0.326** | 0.1396 | 0.5319 |
| TREND + LAG | 71 | 145 | -0.8822 | -0.9530 | 0.1292 | 0.1525 | 0.1999 | **0.0318** | **0.208** | 0.0746 | 0.2505 |
| TREND + SKEW | 71 | 85 | +0.0925 | +0.1879 | 0.1813 | 0.2312 | 0.2938 | **0.0154** | **0.067** | 0.0610 | 0.4320 |

### 2.1 Sign-discipline check on the intersection

A composite is only testable if both legs' signs were pinned **before** the data was read. Where a leg's realized sign opposes its registration, or no sign was registered, building the composite requires a sign chosen from data — which has no valid confirmatory test available.

| Pair | realized sign a | realized sign b | Alignment valid? |
|---|--:|--:|---|
| CARRY + IVOL | +1 | -1 | YES |
| CARRY + LAG | +1 | -1 | NO — LAG: realized sign OPPOSES registration |
| CARRY + SKEW | +1 | -1 | NO — SKEW: no registered sign |
| CARRY + TREND | +1 | +1 | YES |
| CARRY + TS_BASIS | +1 | +1 | YES |
| IVOL + LAG | -1 | -1 | NO — LAG: realized sign OPPOSES registration |
| IVOL + SKEW | -1 | -1 | NO — SKEW: no registered sign |
| LAG + SKEW | -1 | -1 | NO — LAG: realized sign OPPOSES registration; SKEW: no registered sign |
| TREND + IVOL | +1 | -1 | YES |
| TREND + LAG | +1 | -1 | NO — LAG: realized sign OPPOSES registration |
| TREND + SKEW | +1 | -1 | NO — SKEW: no registered sign |
| TS_BASIS + IVOL | +1 | -1 | YES |
| TS_BASIS + LAG | +1 | -1 | NO — LAG: realized sign OPPOSES registration |
| TS_BASIS + SKEW | +1 | -1 | NO — SKEW: no registered sign |
| TS_BASIS + TREND | +1 | +1 | YES |

### 2.2 Reading notes

- **A sleeve's IR is not constant across rows.** Each pair is measured on its own intersection, and the intersections differ in width (mean names 80–166: the options-derived SKEW is scored on a narrower liquid subset than the futures sleeves). A sleeve re-measured on a narrower panel is a different measurement, not an inconsistency.
- **Low lift on a SKEW or LAG row is the sign-discipline problem showing up as arithmetic, not a bug.** The composite is built with each leg's *registered* sign. Where the realized IC sign opposes registration (LAG) or none was registered (SKEW), the two legs partially cancel and the composite collapses. Flipping the sign to rescue the number is precisely the post-hoc move §2.1 exists to forbid.
- **ρ(signal) and ρ(IC) can disagree sharply.** `CARRY + SKEW` measures ρ(signal) −0.6329 against ρ(IC) −0.5085; `IVOL + LAG` measures +0.3093 against +0.5210. The quantity that governs composite IR is ρ(IC) — whether the sleeves' monthly ICs move together — not whether their z-scores do.

---

## 3. Summary

- Pairs measured: **15**. Pairs whose composite beats its own best leg: **2**.
  - `LAG + SKEW` — lift 1.291, ρ(IC) -0.0637, composite IR 0.3021 vs best leg 0.2340, composite power 0.6104 vs best-leg power 0.4389
  - `TS_BASIS + IVOL` — lift 1.024, ρ(IC) +0.0460, composite IR 0.5304 vs best leg 0.5181, composite power 0.9586 vs best-leg power 0.9512

- ρ(IC) governs composite IR, not ρ(signal). Measured range: -0.9530 to +0.5344; ρ(signal) range -0.8822 to +0.6172.

- Pairs that BOTH beat their best leg AND pass the sign-discipline check: **1** — `TS_BASIS + IVOL`

---

## 4. Substrate defects found while building this report

Not part of the combination question; recorded because they were discovered here and affect anything that reads these stores.

1. **`data/signal_engine/carry/signals.duckdb` has `fwd_ret_1m` NULL in all 23,419 rows.** Both `run_train.py:262` and `run_net_spread.py:196` filter `fwd_ret_1m IS NOT NULL` against this store, so as it currently stands they have no rows to score (inferred from the column state, not from executing the runners). It will not self-heal: `build_carry.py:308-314` scopes the fill to the dates built in that same run, so an incremental refresh fills only the new month. The weekly store (`carry/weekly_signals.duckdb`, 566 formations) is populated. This report therefore sources returns from `ivol/signals.duckdb` for every sleeve.
2. **`data/signal_engine/ts_basis/ts_signals.duckdb` is the weekly rebuild, not the registered monthly sleeve.** `build_ts_signals.py:24` reads `carry/weekly_signals.duckdb`; the result is 349 fenced formations on a Friday grid, 35 of which are month-ends. The registered monthly TS Basis construction is not reconstructible from what is on disk.
3. **`fwd_ret_1m` disagrees between stores.** IVOL and LAG match exactly on all 17,406 common rows; TREND differs on **183** of them (~1.1%). Unreconciled.
