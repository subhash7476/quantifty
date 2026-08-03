# TS Basis Filter — SD / Breadth / Marginal-Value Probe (Implementer Prompt)

**Status:** Implementer prompt. No RFA declaration, no construct code, no sealed read.
**Author role split:** this prompt is authored for review; DeepSeek implements the harness and
generates the report. Claude reviews the output, does not code it.
**Depends on:** `TS_BASIS_FILTER_PROTOCOL.md` §0 (FROZEN economic hypothesis, `rank_ic` metric,
three gates as admission criteria) and `TS_BASIS_FILTER_PROTOCOL_REVIEW.md`.

---

## 0. Purpose (one paragraph)

Measure, on the **already-burned TRAIN+HOLDOUT window (2016-02-11 → 2022-12-31)**, the quantities
the `rank_ic` RFA will need for a filtered TS Basis Daily construct: mean rank-IC (**diagnostic
only**), `sd_IC`, effective breadth `N_eff`, formation count `n`, and average names per formation —
for the base construct and under the three admission gates (G1 regime, G2 OI-confirm, G3 expiry),
**both individually and jointly**, and with the **marginal contribution of each gate** isolated via
a drop-column ablation. This probe reads **no data after 2022-12-31**. The preserved 876-formation
sealed window is not touched.

## 1. The fence (hard requirement)

- The harness MUST hard-stop at `2022-12-31`. Reuse/mirror `scripts/osc/sd_probe.py::_assert_fence`:
  assert `max(formation_date) <= 2022-12-31` on every panel before any statistic is computed;
  raise and exit non-zero otherwise.
- A test MUST prove the fence fires (a synthetic 2023 row raises).

## 2. Base construct — pin these exactly

**2.1 Signal.** The frozen TS Basis Daily signal as built by
`scripts/signal_engine/ts_basis_daily/build_ts_basis_daily.py` (`LOOKBACK_ROWS = 252` trailing
rows, MIN_OBS 12, winsorized ±3). **Resolve the store/column against the actual artifact**:
CLAUDE.md and the reauthorization assessment reference `ts_signals.duckdb` (`z_ts`); the filter
protocol §3.1 references `ts_facts.duckdb` (`z_carry_neut`). Confirm which store/column the daily
build actually writes, use that, and **state the resolved name in the report**. Do not guess.

**2.2 Cross-section.** The **full eligible daily universe** — every underlying with a non-null
signal on the formation date. **NOT top-5 per side.** `rank_ic` requires the whole cross-section;
the top-5 subject in protocol §3.1 belongs to the retired hit-rate framing and is not used here.
State this departure explicitly in the report.

**2.3 Forward return.** Underlying **`NSE_EQ` spot** return (equities do not expire). Compute two
horizons and report both:
- **Primary: H = 1 trading day, close→close** (non-overlapping; feeds the headline `sd_IC`).
- **Robustness: H = 5 trading days, close→close** (overlapping ⇒ Newey–West lag-5 t, and report
  AC₁ of the IC series).
The horizon that ultimately feeds the RFA is an operator decision made *after* seeing both; the
report must not pick one silently.

**2.4 Rank IC.** Per formation date, Spearman rank correlation between `z_ts` and forward return
across the eligible cross-section. Require a minimum cross-section size per formation
(`MIN_NAMES = 20`); formations below it are dropped and counted. Reuse
`scripts/osc/sd_probe.py::_ic_series` / `_newey_west` conventions so the IC-series statistics
(mean, sd, NW-t, AC₁) match prior gates exactly.

**2.5 N_eff.** Effective breadth of the eligible **names** cross-section, computed with the same
participation-ratio / eigenvalue estimator OSC uses (`sd_probe.py::run`, the
`np.linalg.eigvalsh` block): `N_eff = (Σλ)² / Σλ²` of the forward-return correlation matrix, plus
the PC1 variance share. Report both. (Equity names are expected far less correlated than option
cells — this probe measures whether that expectation holds.)

## 3. The three admission gates — pin the rules

Each gate is a **hard admission criterion** (exclusion), per §0. No down-weighting (IC-invisible).

**G1 — regime admission (formation level).** Admit formation `t` iff `vix_t ≤ k · vix_med_t`, where
`vix_med_t` = 252-session rolling median of India VIX ending at `t` (min 60 obs), India VIX from
the 1d index store. **Primary `k = 1.5`.** Report sensitivity at `k ∈ {1.25, 1.5, 2.0}` but the
primary is 1.5 (the frozen construct pins one `k` *before* the RFA — it is NOT chosen from the
probe's best-looking value; state this).

**G2 — OI-confirmation admission (name level).** Admit name `i` at `t` iff
`sign(OI_change_i,t) == sign(z_ts_i,t)` (OI building in the signal's direction). Use the near-month
futures contract per underlying from `futures_bhavcopy`; **resolve `chg_in_oi` vs. computed
`open_int_t − open_int_{t−1}` against the store** and state which was used and its coverage. Names
lacking OI data are dropped and counted (report the coverage cost separately from the gate's
sign-filter effect — these are different losses).

**G3 — expiry admission (formation level).** Reject formation `t` iff the execution date `t+1` is a
monthly stock-futures expiry day, OR `t` is within 1 session before that expiry. Expiry calendar
from `futures_bhavcopy` `expiry_dt` (primary: monthly stock-futures expiry — the names are stock
futures).

## 4. Configurations — base, leave-one-in, full, drop-column

Compute every statistic in §2 for **all eight** configurations:

| # | Config | Purpose |
|---|---|---|
| 1 | Base (no gate) | Reference |
| 2 | G1 only | leave-one-in (marginal in isolation) |
| 3 | G2 only | leave-one-in |
| 4 | G3 only | leave-one-in |
| 5 | G1+G2+G3 (full) | the joint construct that would feed the RFA |
| 6 | G2+G3 (drop G1) | **G1's marginal contribution on top of the others** |
| 7 | G1+G3 (drop G2) | **G2's marginal contribution on top of the others** |
| 8 | G1+G2 (drop G3) | **G3's marginal contribution on top of the others** |

## 5. Power reporting — the "earning its place" test

For every configuration, using `scripts/rfa/power.py::power_at` and `::n_required` (two-sided,
target power 0.80):

- **(a) Fixed-δ power** — hold δ at the **base** measured mean IC across all eight configs. This
  isolates the *pure n/breadth cost* of each gate: any power drop here is the gate spending `n`
  (G1/G3) or inflating `sd_IC` (G2) with no credit for its claimed IC lift.
- **(b) Own-δ power** — use each config's own measured mean IC. This shows the *net* effect
  including the claimed IC lift. **Label loudly as in-sample / diagnostic / optimistic** — this δ
  is on burned data and is NOT the RFA anchor.
- Report `n_required` at each config's `sd_IC` for δ ∈ {0.015, 0.020, 0.029} (the OSC feasibility
  ladder) so the reader sees the sd-driven requirement independent of the burned δ.

**Marginal-value verdict table (the deliverable the operator asked for).** For each gate, from the
drop-column pair (full vs. full-minus-gate):

| Gate | Δn | Δsd_IC | Δ fixed-δ power | Δ own-δ power | Earns its place? |
|---|---|---|---|---|---|

"Earns its place" = the gate's own-δ power contribution (does its IC lift outweigh its n/breadth
cost, config 5 vs. its drop-column) is positive **and** it is not merely riding one regime. A gate
that is flat or negative on Δ own-δ power is a **remove** recommendation, stated plainly.

## 6. Gate Stability — the regime-consistency table (required output)

The §5 power/marginal tables tell you whether a gate *helps*. They do not tell you whether it
helps *consistently*. A gate that earns its place only because of one regime (e.g. COVID 2020) is
a different animal from one that earns its place in six environments — and only the latter
survives a regime the book has not seen. This section forces the distinction.

**Regime classification (pinned — no tuning):**

| Regime | Definition | Span on the probe window (2016-02-11 → 2022-12-31) |
|---|---|---|
| Bull | Nifty 50 (1d store) closes above its 252-session SMA at `t` | data-driven |
| Bear | Nifty 50 closes at or below its 252-session SMA at `t` | data-driven |
| High VIX | `vix_t > vix_med_t` (the G1 rule's own boundary at k=1.0) | data-driven |
| Low VIX | `vix_t ≤ vix_med_t` | data-driven |
| Pre-COVID | calendar | 2016-02-11 → 2019-12-31 |
| COVID | calendar | 2020-01-01 → 2021-12-31 |
| Post-COVID | calendar | 2022-01-01 → 2022-12-31 |

Every formation `t` is tagged with all four dimensions (bull/bear, high/low VIX, and its calendar
bucket); a formation belongs to both a market regime and a VIX regime. Report `n` per regime cell
so small-cell regimes are visible, never hidden.

**The required table** — for each gate, the **per-regime marginal contribution** measured on the
drop-column pair (full vs. full-minus-gate), as Δ mean IC (in IC points) and Δ fixed-δ power:

| Gate | Bull | Bear | High VIX | Low VIX | Pre-COVID | COVID | Post-COVID | Consistency | Verdict |
|---|---|---|---|---|---|---|---|---|---|

- **Cell value** = the gate's marginal ΔIC (or Δ power) **within that regime only** — the drop-column
  pair recomputed on the regime's formations. A blank/"—" marks a regime with too few formations
  (`n < 20`); count blanks, do not silently fill them.
- **Consistency** = the fraction of non-blank regime cells where the gate's ΔIC > 0, stated as
  `k/m`. Report **concentration** alongside it: the largest single regime's share of the gate's
  total positive ΔIC across the window. This is the "riding one regime" test.
- **Verdict rule (pre-specified):** a gate is **stability-clear** only if (i) ΔIC > 0 in a majority
  of non-blank regime cells, AND (ii) no single regime accounts for > 50% of its total positive
  ΔIC, AND (iii) it is not negative in ≥ 2 non-blank regimes. A gate that fails any of these is
  **regime-dependent** — flag it as such even if §5's overall marginal table says it earns its
  place. A COVID-only gate is exactly the outcome this table exists to catch (the Nifty–BankNifty
  pair research found 54% of its profit in COVID 2020; G1's stress evidence is likewise ~one
  event). Report this table for the base signal too (all cells = 0 by construction) so the reader
  sees the regime mix of the window itself.

## 7. Pre-registered predictions (state BEFORE running; report held/failed)

Log these as directional predictions before executing (repo discipline — falsifiable prediction
before the run):
- **P1:** G2 raises `sd_IC` vs. base (fewer names ⇒ noisier per-formation IC).
- **P2:** G1 and G3 lower `n` vs. base; G2 leaves `n` unchanged (drops names, not formations).
- **P3:** base `N_eff` for equity names is a materially larger fraction of avg-names than OSC's
  option-cell `N_eff ≈ 1.9` (equities less correlated than option cells) — quantify.
- **P4:** at fixed δ, every gate's power is ≤ base (gates cannot add power except via IC lift).
- **P5 (the real question):** at own δ, at least one gate fails to beat its drop-column — i.e. the
  probe is expected to recommend removing at least one gate. (Falsified if all three earn their
  place.)
- **P6 (stability, §6):** at least one gate that passes §5's marginal table is **not
  stability-clear** — it fails majority-of-regimes, single-regime concentration, or ≥2 negative
  cells. The prime suspect is **G1**: its stress evidence is ~one event (COVID in HOLDOUT), so it
  is the most likely to ride one regime. (Falsified if every §5-passing gate is also
  stability-clear.)

## 8. Deliverables

1. `scripts/ts_basis_filter/sd_probe.py` — the harness (fence-guarded; reuses `rfa/power.py` and
   `osc/sd_probe.py` estimators; no hand-tuned constants beyond those pinned above).
2. `docs/reports/TS_BASIS_FILTER_SD_PROBE_REPORT.md` — **script-generated, zero hand-edited
   numbers**: the §2 statistics × §4 configs, §5 power/marginal tables, **§6 Gate Stability
   regime-consistency table** (with `n` per regime cell and the consistency/concentration
   verdicts), §7 predictions held/failed, and the resolved store/column/OI-source names from
   §2.1/§3.2.
3. `tests/ts_basis_filter/test_sd_probe.py` — fence test (§1), IC-sign/rank-invariance sanity,
   drop-column bookkeeping (config 5 names ⊆ config 6/7/8 as expected), OI-coverage accounting,
   and a stability-table bookkeeping check (every formation tagged with a non-blank regime cell on
   at least one dimension; blanks only where `n < 20`).

## 9. What this probe is NOT

- NOT an RFA declaration (that follows, declared on the **filtered** `n`/`sd_IC`, δ defended
  independently — never the burned mean, never the sealed +0.077).
- NOT a construct/harness for trading, and NOT a sealed read.
- NOT authority to freeze the window ledger or reverse the 2026-08-01 research-only decision — both
  remain open and downstream of this measurement.
