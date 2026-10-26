# M4a-LC — Compression → Expansion, Level-Controlled — Research Protocol v1.0 (DRAFT — NOT FROZEN)

**Status:** DRAFT for review. **NOT frozen. NOT implemented. No outcome computed. No fresh/holdout surface read.**
**Branch / worktree:** `research/m4a-compression-expansion` in `F:\Nifty_m4a`.
**Design authority:** `M4A_FINAL_MECHANISM_ADJUDICATION.md` (Decision **A** — same mechanism, level confound removed);
`M4A_COMPRESSION_EXPANSION_DESIGN_INVENTORY.md`; `M4A_LEVEL_CONTROLLED_ADVERSARIAL_REVIEW.md`.
**Predecessor (retired construct):** `M4A_COMPRESSION_EXPANSION_PROTOCOL.md` v1.0 (cohort contrast, high-state comparator,
trailing-median outcome) — its comparator and its outcome are **retired** and do not reappear here (§16).
**Governing vocabulary:** closure ledger C0–C9; GR-1 spent-window rules; exposure register.
**No RFA is created** (§12 reports the MDE instead; the existing RFA metrics do not express a within-panel regression).
**The Vault mechanism map and the closure ledger are not modified.**

**Outcome-free design numbers used below** (from the hashed BKV dev panel, feature-level only, no forward quantity):
evaluable name-days 1,310,347; entities 508; dates 3,166; `sd(a)=0.394`, `sd(b)=0.317`, `sd(x)=0.253`; `corr(a,b)=0.767`;
`corr(a,x)=0.597`; `R²( x ~ cubic(a) ) = 0.364` ⇒ **VIF(x | flexible a) ≈ 1.57**; `a` quantiles
q10/q25/q50/q75/q90 = −3.792 / −3.570 / −3.318 / −3.057 / −2.814; median 41 names per (date, `a`-decile).

---

## 1. Research Question

> **Does unusually low recent realised range — measured relative to the instrument's own longer-run range state —
> predict subsequent range expansion, after controlling for the current level of realised range?**

The estimand is a **realised-dispersion** relationship. It is **not** a return, direction, or trading question; there is no
position, no cost model, and no profit claim (§5, §15).

Sub-questions the design must adjudicate:

1. Is the incremental effect of the compression term **positive** (compression precedes expansion) once the current level
   is controlled flexibly?
2. Does that effect survive a **fitted persistence null** that uses the level's own recent history (§6)?
3. Is it visible **within level** (design-based, nonparametric, threshold-free, §7)?

---

## 2. Mechanism Definition

**M4a, as fixed by the Vault and the adjudication:** *periods of unusually low realised range are followed by expansion.*

- **Compression** is inherently **relative**: recent short-run range is low **relative to the instrument's own longer-run
  range state**. Its native variable is the **term structure of realised range**, `x = log(ATR10/ATR60)`: `x<0` = recent
  range contracted below the longer baseline (compression); `x>0` = recent range expanded above it.
- **Expansion** is a rise in realised range **relative to the current level** — not a high level per se. The output is a
  forward realised-range change (§3).
- The mechanism is **symmetric**: no sign, no break direction, no entry. (The Vault's "direction resolved by the break" is
  an M3a execution question and is out of scope here; §16 refuses it.)

The adjudication (Decision A) holds that controlling for the level **does not change the hypothesis** — it removes the
confound (the predecessor was ~76 % level by percentile) that prevented identification. This protocol therefore estimates
the mechanism's native variable with the level held fixed.

---

## 3. Exact Variables

All quantities below are functions of information **at or before the close of session `t`**, except the forward window.
Sessions are **regular trading sessions** of the instrument's calendar.

### 3.1 Daily range (pinned)

```
r_s  = (H_s − L_s) / C_{s−1}
```

- `H_s, L_s, C_s` = adjusted high, low, close of session `s`; `C_{s−1}` = the close of the **previous session in the
  calendar**. If `s−1` has no valid row, `r_s` is missing (never imputed).
- **The gap term is deliberately excluded** (no `|H−C_{s−1}|`): the mechanism is high–low realised range, and including the
  gap would import directional/break information that belongs to M3a. This is also the predecessor's definition, so the
  redesign changes only the identification, not the mechanism.

### 3.2 ATR (pinned)

```
ATR_n(s) = mean( r_{s−n+1} … r_s )        (simple arithmetic mean; no Wilder smoothing)
```

- **Simple mean, not Wilder's recursive ATR.** Justification: a simple mean is a transparent, non-recursive linear window
  with no initialisation convention, making the term-structure interpretation exact and removing one arbitrary degree of
  freedom. It is the estimator the inventory specified and the characterization used.
- Fast `n_f = 10`, slow `n_s = 60` sessions. **These are pinned, not tuned** — fixed by the adjudication and the
  predecessor, chosen as a "recent 2-week vs recent quarter" contrast. No other (fast, slow) pair is evaluated in the
  primary family; one declared robustness pair (§7.4) is disclosure only. A ratio whose slow term is 0 is missing.

### 3.3 Signal, level, and control variables

```
a_t = log ATR10(t)                     (current short-run level)
b_t = log ATR60(t)                     (current longer-run level)
x_t = a_t − b_t = log(ATR10/ATR60)     (compression; low = compressed)      # reported as the mechanism variable
```

`a_t` is the **level control**; `b_t` is the **longer-run term** whose incremental content, given `a_t`, *is* the
compression effect (§4).

### 3.4 Forward range and the outcome (pinned; predecessor outcome retired)

```
F_h(t) = mean( r_{t+1} … r_{t+h} )                               (forward mean daily range, h ∈ {5, 20})
y_h(t) = log( F_h(t) / ATR10(t) ) = log F_h(t) − a_t            (log expansion from the current level)
```

- `y_h` is **level-neutral by construction**: it divides each instrument by its own current short-run range, so a name with
  a high or low volatility level is compared to itself. Under pure level-persistence `y_h ≈ 0`; **expansion ⇒ `y_h > 0`**.
- Log makes the statistic scale-free and symmetric; `F_h` uses the **same** `r_s` as the ATRs, so there is no basis
  mismatch.
- **No trailing-median denominator, no percentile threshold anywhere in the primary model.**

### 3.5 Validity

A row is **valid** iff adjusted open, high, low, close, and volume are present and `>0`, and `C_{s−1}` is valid. Windows are
**strict and complete**: `x` needs valid rows on `t−59 … t`; `y_h` needs valid rows on `t+1 … t+h`; otherwise the
observation is missing and **dropped** (never imputed, never forward-filled). See §13–§14.

---

## 4. Identification Strategy

### 4.1 The confound and the fix

The retired construct contrasted a low-`x` cohort against its complement **without holding the level fixed**; because
`x` and `a` are strongly related (percentile collinearity 0.757; log `corr(a,x)=0.597`) and forward range tracks the level,
that contrast was predominantly a level/persistence test. The fix is to estimate the effect of the **longer-run term `b_t`
given a flexible control for the current level `a_t`**, within date.

### 4.2 Why the estimator uses `b` (not `x`) on the right-hand side

`x = a − b` contains `a`, and the outcome `y = logF − a` also contains `a`. If a flexible control `f(a)` does not absorb
`a` exactly, residual `a` in the regressor can mechanically correlate with residual `a` in the outcome and bias `β`.
Estimating the **separated form**

```
y_h = α_t + f(a_t) + γ_h · b_t + ε          (primary)
```

avoids placing `a` inside the treatment. The mechanism's coefficient is the equivalent `β_h = −γ_h` (algebraically exact
when `f` is linear in `a`; numerically near-identical under the flexible `f`). **H1: `β_h > 0` ⟺ `γ_h < 0`** (a *higher*
longer-run range, holding the current level, predicts *higher* forward expansion).

### 4.3 The level control `f(log ATR10)` (pinned functional form)

- **Primary `f`:** a **natural cubic spline in `a`** with **five interior knots fixed at the pooled design-panel `a`
  quantiles q10, q25, q50, q75, q90 = −3.792, −3.570, −3.318, −3.057, −2.814** (6 basis functions incl. the linear term).
  Natural (linear) tails. The knots are a function of the **feature distribution only**, computed once on the design surface
  and **frozen before any outcome**; they are applied unchanged to any confirmation surface.
- Why spline-in-logs and not a decile dummy set: logs are the scale on which the level/persistence relationship is
  approximately smooth, and a spline keeps within-bin variation of `a` (hence of `x`) available to identify `γ` rather than
  absorbing it. Measured over-control is modest: a cubic in `a` explains 36.4 % of `var(x)` (VIF ≈ 1.57), so ample residual
  treatment variation remains.
- **Pre-declared robustness `f`:** within-date deciles of `a` (dummies). If `γ`'s sign or significance depends on the
  functional form, the result is reported as form-sensitive (§6, §15).

### 4.4 Date fixed effects `α_t`

Session fixed effects (equivalently, within-date demeaning). Justification: the market-wide volatility regime is the
dominant common factor; `α_t` removes it and makes the identifying variation **cross-sectional within a session** — the
correct counterfactual is "on the same day, among names at the same level, does relative compression predict expansion?"
`α_t` also absorbs any date-level data-quality artefact common to all names.

### 4.5 What is *not* controlled, and why

- **Entity fixed effects are not used in the primary model.** The mechanism is a within-state, cross-sectional prediction;
  entity FE would remove all between-name level variation and condition on the entity's own average, which is not the
  question. An entity-demeaned model is a declared, report-only robustness (§7.4).
- **No matching.** Hard matching on the level was rejected by the adversarial review (over-control, collider/Berkson,
  regression-to-the-mean). The control is a **joint flexible regression**, not a matched contrast.

---

## 5. Primary Estimand

For `h ∈ {5, 20}`, the primary estimand is the **incremental longer-run-range coefficient**

```
γ_h  = coefficient on b_t in     y_h(t) = α_t + f(a_t) + γ_h b_t + ε
```

reported as the mechanism effect **`β_h = −γ_h`**, with

```
H0: β_h ≤ 0        (no incremental compression effect)
H1: β_h > 0        (compression ⇒ expansion, beyond the current level)         one-sided, α = 0.05
```

**Interpretation and units.** `β_h > 0` means: among names at the same current short-run level and on the same date, a
**lower** `x = a − b` (more compression) is associated with a **larger** `y_h` (more forward expansion). Report `β_h`
together with (i) the effect per 1 SD of `x` (`β_h · sd(x)`, using the frozen design-panel `sd(x)=0.253`), and (ii) the
implied forward-range change for a halving of the ratio (`x → x − log 2`).

**What it is not.** Not a return, not a sign, not an entry/exit, not a cost-adjusted quantity. A positive `β_h` answers
only the mechanism question in §1.

---

## 6. Persistence Null

**The fitted persistence null is binding, not decorative.** Because `b_t` is a rolling mean of the level and forward range
persists, `γ` could be generic serial dependence rather than a compression effect. A cell is classified as supported only
if it survives the persistence controls below.

### 6.1 Primary null (within-model)

`H0: γ_h = 0` in the primary model, whose `α_t` and `f(a_t)` already absorb the current level and the market regime. This
is the baseline "level-only" null.

### 6.2 Augmented null (level-history control)

```
y_h = α_t + f(a_t) + Σ_{k ∈ K} g_k( a_{t−k} ) + γ_h b_t + ε        K = {5, 20}
```

with each `g_k` a natural cubic spline. This admits a fitted persistence forecast from the level's own trajectory, so `γ`
must add information **beyond the level and its recent path**. **Pre-declared:** a cell is supported only if `β_h > 0` with
Holm-adjusted `p < 0.05` in the primary model **and** `β_h > 0` with one-sided `p < 0.05` in the augmented model. If the
primary is significant but the augmented is not, the finding is recorded as **"not incremental beyond level dynamics"**
(a null for the mechanism).

### 6.3 Fitted-forecast check (report-only)

Fit the no-`b` model `M0 = α_t + f(a_t) + Σ g_k(a_{t−k})` and `M1 = M0 + γ b_t` on a pre-registered **blocked
cross-validation** (blocks of length `2h+1` sessions to respect overlap). Report the incremental out-of-sample `R²` from
adding `b_t`. This is disclosure; the gate is §6.1–§6.2.

---

## 7. Design-Based Robustness

All robustness is **pre-declared**; none can change a label except by the stated rule, and none is a rescue.

### 7.1 Within-level nonparametric contrast (threshold-free)

Within each (date, decile-of-`a`) cell, compute the **Spearman rank correlation** between `b_t` (or equivalently `x_t`, with
the sign flipped) and `y_h`. This is nonparametric in both regressor and outcome and holds the level fixed by construction;
it uses **no percentile cut on the signal**. Test the mean within-cell rank correlation `> 0` by a date-clustered t or a
within-date permutation. Cells hold a median of 41 names (§ header), so this is well-powered. *Pre-declared:* the primary
cell's rank-correlation sign must agree with `β_h`.

### 7.2 Within-date level-decile regression

Replace the spline `f(a)` with within-date `a`-decile dummies and re-estimate `γ`. Must retain sign and significance.

### 7.3 Nonlinearity / tail shape (report-only)

Replace the linear `γ b_t` by a **spline in `x_t`** and report the fitted shape and the average slope over the lower tail of
`x`. Because the mechanism concerns *unusually low* range, a linear average effect could dilute a tail effect; this
diagnostic shows whether the association is concentrated at low `x`. It is **report-only** and gates nothing (no threshold
is introduced into the decision).

### 7.4 Declared report-only variants (cannot change a label)

Entity-demeaned model; alternative ATR pair `(n_f, n_s) = (5, 20)`; `y` using `E_vol = sqrt(mean r²)` instead of range;
non-overlapping formation sampling (every `h`-th session); by-year stability; winsorization of `y` at the 0.1/99.9
percentiles. All unadjusted, all disclosure.

---

## 8. Universe and Data Rules

### 8.1 Design/development surface (spent — GR-1.4 only)

- `equity_bhavcopy_adjusted` via the hashed BKV-1 dev snapshot (PIT top-200 by trailing-6-month median turnover, monthly
  rebalance; membership on `t` = the last rebalance **strictly before `t`**; entity grain; recycled tickers and ISIN
  re-issues via `symbol_entity_intervals`; regular-session calendar rule as in BKV-1).
- **Span 2012-01-02 → 2022-12-30.** This window is **signal-spent** (register Q-1…Q-3, G-S1, MRLC E-3, N200 Q-4, BKV-1
  Q-7; GR-1.3). It is used **only to pin `f`, the knots, the lag set, the aggregation rules, and the MDE scale** — all of
  which are **features of the regressors, not of the outcome** — and to run a **GR-1.4 non-confirmatory** development pass.
  It **cannot confirm anything** and no development result is called a confirmation.

### 8.2 Confirmation surface (fresh — required; operator decision)

Any confirmation must use a **genuinely unread** surface, registered **before** the read (register §5–§6). **The 2023+
equity EOD surface is NOT usable as confirmation** (R-11: signal-spent; Q-6 reserved). Candidate surfaces, in order of
fidelity to the cross-sectional design:

| Candidate | Span | Names | Status | Fidelity / requirement |
|---|---|---|---|---|
| **Vendor N100 1m store** (`.../candles/1m_vendor/`) | 2015-02-02 → 2025-08-06 | 101 non-RELIANCE names (V-1 covers only RELIANCE) | **Unread** (only RELIANCE read) | **Primary candidate** — preserves the cross-section; **requires provenance certification** and a pinned 1m→daily aggregation (§8.4) |
| **India VIX 1m** (canonical, V-0b) | 2022-01-03 → 2026-09-11 | 1 series | **Unread**, value-verified 99.98 % | Single-series fallback; time-series form of the model (no cross-section); weaker |
| **India VIX EOD vendor CSV** (V-0c) | 2010-01-04 → 2025-06-05 | 1 series | **Unread** | Single-series fallback as above |

- **Multiple testing across surfaces is forbidden:** the operator chooses **one** confirmation surface and records the
  choice + register row before the read. No second fresh surface may be substituted after a result.
- If the chosen candidate is the vendor store and it **cannot be certified**, the operator must either choose a
  single-series candidate (accepting the weaker design) or decline to confirm. **This is the principal open pre-freeze
  decision (§18).**

### 8.3 PIT membership

Design surface: PIT top-200 as §8.1. A fresh candidate with a fixed name set (vendor N100) uses **all names present on the
date with a valid window** rather than PIT turnover membership (that universe is unavailable for the vendor names); this is
declared as a fixed-N100 slice, clustered by entity. A single-series candidate has no membership rule. The membership rule
in force is stated on every result block.

### 8.4 Aggregation for a 1m-derived daily surface (pinned, if used)

For the vendor store (pre-CAS era, all dates < 2026-08-03): session = the regular continuous window per
`core/market/session_schedule.py` (09:15–15:30 pre-CAS); daily `H`/`L` = max/min of the 1m `H`/`L` over valid bars; daily
`C` = last valid 1m close; `C_{s−1}` = the previous session's daily `C`. Exclude `is_synthetic = TRUE` bars (post-CAS only,
not applicable to this store). A session with no valid bars is missing. The store is already corporate-action adjusted; a
continuity check (no unexplained >25 % single-session close ratio) is run and reported.

---

## 9. Temporal / Fresh-Surface Rules

| Stage | Surface | Role |
|---|---|---|
| **DEVELOPMENT** | design surface (spent, §8.1) | GR-1.4 non-confirmatory; pins `f`, knots, lag set, aggregation, MDE scale; takes **no** confirmatory decision |
| **CONFIRMATION** | one fresh surface (§8.2), one-shot | the only stage that can confirm; read **after** freeze and after a register row; never re-read |

- **No pooling** of the development and confirmation stages, and no pooling of surfaces.
- If the fresh surface is large, in-surface splits (e.g. a within-surface VAL/HOLDOUT) may be pre-registered **before** the
  read; otherwise the whole surface is read once. Default: **one-shot on the whole fresh surface**.
- The design surface's 2012–2022 dates and a fresh 2015–2025 vendor surface overlap in calendar time but are **different
  surfaces**; per register §1 (window-scoping), the vendor surface is unread and the overlap is not a leak.
- **No use of the 2023-01-02 → present equity EOD window**, and no use of any window recorded as spent at signal level.

---

## 10. Statistical Inference

- **Estimator:** OLS of §5/§6 on the full evaluable cross-section (all name-days, not a cohort). Date FE via within-date
  demeaning; splines as pinned.
- **Dependence:** residuals are correlated (i) within entity across overlapping `h`-day forward windows, and (ii) across
  entities within a date. **Primary:** **two-way cluster-robust variance (entity × date)** with the finite-sample
  Cameron–Gelbach–Miller intersection correction (the harness's `event_contrast_cluster` kernel). **Robustness:** entity
  clustering with **Newey–West lag `h`** (the BKV `nw_gap_test` kernel). Report both; a sign flip of significance between
  them is investigated and disclosed.
- **One-sided** p-values for `H1: β_h > 0` (equivalently `γ_h < 0`), Student-t with the appropriate cluster df.
- **Overlapping horizons:** handled by the entity NW lag `h` / entity cluster; additionally the §7.4 non-overlapping
  subsample is reported.
- No bootstrap is used for the gate; a block bootstrap CI (block `h+1`) is report-only for the headline cells.

---

## 11. Multiple Testing

- **Primary family: 2 cells** = `h ∈ {5, 20}` for the primary model `y_h = α_t + f(a_t) + γ_h b_t`.
- **Holm** at one-sided `α = 0.05` over the 2 cells. Report raw and Holm-adjusted p per cell.
- The **persistence-null** condition (§6.2), the **design-based robustness** (§7.1–§7.2), and every §7.4 variant are
  **gating conditions / disclosures, not additional primary cells**, and are **not** multiplicity-inflated.
- No threshold, window, or comparator search is part of the family; adding one after the fact is a refused rescue (§16).

---

## 12. MDE

- **No RFA.** Report the **minimum detectable effect** per cell at one-sided `α = 0.05`, 80 % power:
  `MDE80_h = (z₀.₉₅ + z₀.₈₀) · SE(β_h)` (≈ `2.49 · SE`).
- Report `MDE80` in three units: (i) raw `β_h` (per unit `x`), (ii) per 1 SD of `x` (`· sd(x)`), and (iii) as the forward
  range change implied by a halving of the ratio. Report the **observed** `SE` and the design effect of the level control
  (the measured VIF ≈ 1.57), so the reader sees the cost of controlling for the level.
- **Pre-run statement (falsifiable):** with ~1.3 M name-days, 508 entities and 3,166 dates, the SE is expected to be small
  enough to detect a modest incremental effect; if the observed `MDE80` is large relative to any plausible range-expansion
  elasticity, a null is reported **as a limitation against that MDE**, never as a mechanism disproof.

---

## 13. Missingness / Attrition

- **Listwise deletion only.** A name-day enters the regression iff `a`, `b`, and (for the cell) `y_h` are all defined under
  §3.5. No imputation, no forward-fill, no truncation.
- **Attrition reporting:** per cell, report `n` formed, `n` resolved, `n` dropped for missing lookback, `n` dropped for
  missing forward window, and `n` excluded by stage/containment. Accounting identity
  `formed = resolved + dropped_lookback + dropped_forward + excluded` must hold exactly (verified independently, §17).
- **Pre-declared robustness:** (i) a missingness indicator regressed on `a`, `b`, `date` to test that missingness is not
  differential in the treatment; (ii) re-estimation on the subsample with a **longest common lookback** (drop the first 60
  sessions of each entity after any gap) to confirm stability. If missingness is differential in `b` at `p<0.05`, the result
  is reported as potentially selection-affected.
- **Survivorship:** PIT membership for the design surface; the fixed-N100 slice includes delisted names only while present
  (a terminal-window rule may drop late entries — counted). No backward projection of a current list.

---

## 14. Corporate Actions and PIT Rules

- **Design surface:** adjusted OHLCV from `equity_bhavcopy_adjusted` (entity-grain, time-aware, ISIN-prefix linkage;
  certified by the PSB-1 four-arm suite). **Never** join the 1m store to bhavcopy across a CA (different price bases).
- **1m-derived fresh surface:** the store is already CA-adjusted; aggregate within a session; the daily `r_s` is a ratio of
  adjusted quantities within the same series, so a CA in `(t, t+h]` does not distort `y_h`. Run the continuity check (§8.4).
- **PIT membership:** on session `t`, membership = the last rebalance **strictly before `t`** (design surface). Recycled
  tickers/ISIN re-issues resolved by entity, not symbol.
- **Exclusions:** no `is_synthetic = TRUE` bar; no special/short session (design surface uses the BKV regular-session
  rule); index-like series (VIX) carry no volume constraint. A CA event inside `[t−59, t+h]` is **not** excluded by default
  because the adjusted series is continuous; a §7.4 report-only exclusion of CA-spanning windows is provided as a check.
- **Entity-grain rule (load-bearing):** all adjustments and joins are at entity level; a symbol-level "clean name" test is
  known to fail on renamed tickers and must not be used.

---

## 15. Closure Mapping

Mapped **before** any result, to the ledger's C0–C9 vocabulary. Every label is quoted **construct-scoped**.

| Label | Condition (first match) |
|---|---|
| **C4** | a defect trigger fires: frozen-file hash mismatch; an independent-verification disagreement beyond tolerance; an accounting-identity failure |
| **C5** | the pre-registered criterion was tested and **not supported**: no cell satisfies §5 **and** §6.2. Quoted **"C5, construct-scoped"**; M4a stays open as a mechanism |
| **C6** | ≥ 1 cell supported on the **fresh** confirmation surface (β>0, Holm `p<α`, sign-robust in §7.1–§7.2, survives §6.2): **mechanism characterization confirmed at construct scope; no economic gate applies** (there is no tradeable expression) |
| **C7 / C8** | **unreachable by construction** — they require an economic (P&L) gate, which this mechanism test does not have. Stated, not pursued. |
| **Development-stage result** | never a confirmation: reported as **GR-1.4 non-confirmatory**; a positive development result only *justifies* the fresh read (it is C6-pending), a negative one stops (§16) or is C5 if the operator declines to read fresh |

**Mechanism-level effect (proposed, not applied here):** a supported C6 on the fresh surface would move M4a from
**C (adjacent, untested cleanly)** toward **B (tested, with documented scope limits)** — a characterization only. The Vault
map and ledger are **not** edited by this protocol or its run.

---

## 16. Refused Rescues

The following are refused in advance:

1. Reintroducing a **percentile threshold** on the signal or a **high-state comparator**; reusing the **trailing-median
   outcome**.
2. Changing `n_f`, `n_s`, `h`, the outcome definition, the `f` basis/knots, the lag set `K`, the universe, the weighting,
   or the estimator **after** seeing a result.
3. **Matching** on the level as a primary or rescue design; dropping the level control.
4. Dropping the **persistence-null** condition (§6.2) to convert a level/persistence result into a compression result.
5. Promoting a §7.4 variant, a subgroup, a single year, a single horizon, or a single name.
6. Any **directional / return / trading** arm, any cost model, any sign test; the mechanism is symmetric by construction.
7. Reading the **2023+ equity EOD** window, re-reading the design surface as confirmation, pooling stages, or substituting a
   second fresh surface after a result.
8. Re-labelling a failed confirmation as C6; calling a development result a confirmation; **creating an RFA** to override
   the MDE.

---

## 17. Reproducibility

```bash
# (concept; not implemented here)
git worktree ... research/m4a-compression-expansion           # F:\Nifty_m4a
python -m scripts.m4a_level_controlled.build_panel            # hashed snapshot, fence asserted
python -m scripts.m4a_level_controlled.design_diagnostics     # OUTCOME-FREE: knots, VIF, occupancy, missingness
python -m pytest tests/m4a_level_controlled -q                # unit + governance + synthetic end-to-end
python -m scripts.m4a_level_controlled.freeze                 # only after §18 is clear and before any outcome
python -m scripts.m4a_level_controlled.run_stage DEVELOPMENT  # GR-1.4 non-confirmatory
python -m scripts.m4a_level_controlled.verify_independent DEVELOPMENT
python -m scripts.m4a_level_controlled.run_stage CONFIRMATION # one-shot, fresh surface, register row first
python -m scripts.m4a_level_controlled.verify_independent CONFIRMATION
python -m scripts.m4a_level_controlled.classify
```

- **Determinism:** seeded bootstrap/permutation; every regressor is a function of prior sessions; the frozen spline knots,
  lag set, and seeds are written into the freeze record.
- **Independent verification (pre-declared, disagreement STOPs the run):** VP1 pure-SQL re-derivation of `a`, `b`, `y`, the
  design matrix, and the coefficient/SE; VP2 raw as-traded loops on a seeded sample (scale-free quantities) skipping
  CA-spanning events; VP3 the γ estimate vs a pure-Python/statsmodels re-fit; VP4 accounting/uniqueness; VP5 price-basis
  (adjusted = raw on CA-free entities; CA rebuild agreement).
- **Causality tests:** perturbing all prices after `t` leaves `a_t`, `b_t`, `x_t` unchanged; perturbing `t` changes them.
- **Freeze record:** hashes of panel + all modules + the protocol JSON; `outcomes_computed_before_freeze: false`.

---

## 18. Pre-Freeze Checklist

Not freezable until every item is closed and recorded:

- [ ] **Fresh confirmation surface chosen** and (if vendor N100) **provenance-certified**; **exposure-register row written
  before the read** (register §8). *Principal open item.*
- [ ] Exact **1m→daily aggregation rules** (§8.4) pinned in the protocol JSON if a 1m-derived surface is used.
- [ ] `f` basis and the **five interior knots frozen** from the design panel (values above; re-hashed at freeze).
- [ ] Lag set `K = {5, 20}` and the spline form of `g_k` frozen.
- [ ] Primary family = 2 cells; Holm; the §6.2 / §7.1–§7.2 gating conditions written as code constants asserted by a test.
- [ ] Outcome-free design diagnostics run and hashed (knots, VIF, per-(date,decile) occupancy, missingness, MDE scale).
- [ ] Missingness accounting identity and the two §13 robustness checks implemented and tested.
- [ ] Independent verifier VP1–VP5 implemented; synthetic end-to-end dry run green; tamper test fails the verifier.
- [ ] **No outcome read** in development before freeze; design surface confirmed still fenced at 2022-12-30.
- [ ] Closure mapping (§15) and refused rescues (§16) transcribed verbatim into the protocol JSON and asserted by tests.
- [ ] MDE reporting units (§12) implemented.
- [ ] Operator sign-off on: the fresh surface, the retired comparator/outcome, the one-sided family, and the development
  stage's GR-1.4 status.

---

**END — DRAFT v1.0. NOT FROZEN. Do not run.**
