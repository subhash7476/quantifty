# I-β — Dependency / Contamination Audit

**Date:** 2026-09-12 · **Authority:** operator ruling PTMS-2026-09-12 (I-β: "perform
dependency/contamination audit only; no new market-data read… do not infer contamination
merely from temporal overlap").
**Access level:** source inspection only. **No market data was read.** No window spent.

**Finding: no consumption channel exists. The overlap is temporal only.**
**Status recommendation: I-β is not established as contamination — but the audit cannot
close it alone. See §4.**

---

## 1. The question, as the operator framed it

Did either MSRP-fitted artifact — the frozen OLS coefficients (`build_forward_vol_artifact.py`,
register row I-6) or the bootstrap block length L (`derive_block_length.py`, row I-11), both
fitted on `NSE_INDEX|Nifty 50` over **2023-01-02 → 2025-12-31** — get consumed by the
intraday analog-path track through any of:

analogue construction · normalization · admissibility · K/threshold selection · labels ·
trading-rule formation?

## 2. Method

Source inspection of `scripts/analog_path/` (18 modules) and its frozen `config.json`:
import graph, every parameter's declared provenance, and targeted search for the MSRP
artifacts and for any volatility-derived quantity (`msrp`, `forward_vol`, `block_length`,
`realized_vol`, `bootstrap`, `vol`, `sigma`, `atr`, `vix`, `normal`, `scale`, `std`).

## 3. Channel-by-channel result

| Channel | Finding | Evidence |
|---|---|---|
| **Import graph** | **No dependency.** `scripts/analog_path/` imports nothing from `core.msi`, `scripts.msrp`, or any MSRP artifact. Its only non-stdlib imports are numpy/scipy/pandas/matplotlib and its own modules | Full import enumeration over all 18 modules |
| **Analogue construction** | Self-contained. `states.py` stacks sessions loaded "strictly from their own day files; the matrix is a pure" function of those bars. `matcher.py` selects nearest-K "from the morning-state matrix alone" | `states.py:3-11`, `matcher.py:42` |
| **Normalization** | **No volatility scaling of any kind.** Representations are `norm_price_path` and `interval_returns`, plus diagnostic State C ("linear detrend of State A… first and last elements are exactly 0"). Zero hits for vol/sigma/ATR/VIX in `states.py` or `matcher.py` | `config.json` `representations`, `state_c`; targeted search |
| **Admissibility** | Structural only: `min_bars: 360`, `min_morning_bars: 195`, first-bar label check. No fitted quantity | `config.json` `eligibility` |
| **K / threshold selection** | Declared constants, not fitted: `k_values [5,10,20,50]`, `return_matching_tolerance_pct 0.10` (operator decision 2026-09-09), `min_matched_group 5`, `return_bins_edges_pct` fixed | `config.json`, sealed as `cd3d5149…` |
| **Labels** | Outcome matrix "passed separately and is touched **only after selection**" | `matcher.py:11` |
| **Trading-rule formation** | No trading rule exists in the track — it produces forecasts and excursion statistics | Track scope |
| **Block bootstrap (the I-11 channel)** | **Independent.** `bootstrap_blocks_days: 5`, a fixed constant in the frozen config. `stats.py` states the intent explicitly: *"a moving-block bootstrap for CIs of the mean (blocks of 5 sessions) — **self-contained so this track carries no import**."* MSRP's L was neither imported nor referenced | `stats.py:4-5`, `config.py:73`, `config.json` `stats` |

**The I-11 channel is the one that mattered most and it is cleanly negative.** Both artifacts
compute a block length; the analog track's is a hard-coded 5 sessions, deliberately
self-contained, and the code says so in a comment written before this audit existed.

## 4. What this audit does and does not establish

**Establishes.** No code path carries an MSRP-fitted quantity into the analog-path track.
Per the operator's instruction, temporal overlap alone is not treated as contamination, and
after removing temporal overlap from consideration **nothing remains**.

**Does not establish.** Three limits, stated rather than papered over:

1. **Human-channel leakage is not auditable from source.** The MSRP work characterized the
   2023–2025 span (volatility level, autocorrelation structure). If a person who saw those
   results chose analog-path parameters, no grep can detect it. What is checkable and is
   checked: every analog-path parameter is declared in a config frozen at TRAIN
   (`cd3d5149…`, unchanged through HOLDOUT), and the two operator-set values carry dated
   decisions (AP-D4, the ±10 bp tolerance, both 2026-09-09).
2. **This audit covers the track as committed.** Deleted or untracked exploration is out of
   reach, the same limit the exposure register records generally.
3. **The audit is about *dependency*, not about whether the SEALED window is fresh.** Rows
   I-2, I-3 and I-6 still record that window as read at feature, signal and estimation
   level by *other* families. Whether that constitutes multiplicity for a directional
   construct is a governance question this audit does not answer.

**Recommendation (not a ruling).** I-β's *contamination* limb can be closed on this
evidence; its *multiplicity* limb cannot be closed by a dependency audit and should be
adjudicated separately. Analog-path SEALED remains blocked either way, since the operator
has also made it conditional on V1.

---

## 5. Collateral finding — the analog-path track already solved V1

While auditing, the track was found to contain **the repo's only recorded treatment of the
dual-grid seam**, in its frozen config:

```
"era_rule": "observed_bar_labeling",
"labeling_rule": "first bar stamped 09:16 -> end-labelled (vendor price rule);
                  09:15 -> start-labelled (native price rule); anything else -> excluded",
"close_rule":    "close of bar stamped 15:30 in vendor era / 15:29 in native and cas eras",
"era_boundaries": { "vendor_last": "2023-01-31", "native_from": "2023-03-01",
                    "cas_from": "2026-08-03" }
```

and in `data_layer.py`:

> *"end-labelled sessions: first bar 09:16 covers 09:15-09:16 … start-labelled sessions:
> first bar 09:15; the bar stamped t opens AT t. The operational era follows the OBSERVED
> first-bar stamp (operator decision 2026-09-09, AP-D4), **not the calendar date** … This
> admits the 20 Jan-2023 sessions whose provenance metadata disagreed with their actual bar
> labelling."*

Three consequences for P2:

1. **V1's semantic question has a candidate answer already on record** — pre-2023 vendor era
   is **end-labelled**, native era is **start-labelled**. This is an assertion in a frozen
   config, not an independent certification, but P2 should **verify and generalize it**
   rather than start from zero.
2. **AP-D4's mechanism is the right one store-wide**: resolve the era by the **observed
   first-bar stamp**, never by calendar date. It already handled 20 January-2023 sessions
   whose metadata disagreed with their labelling — a class the store map does not mention.
3. The deliberate `vendor_last 2023-01-31` → `native_from 2023-03-01` gap corroborates the
   independently measured finding that **2023-01-31 reverts to the 09:16 grid**.
