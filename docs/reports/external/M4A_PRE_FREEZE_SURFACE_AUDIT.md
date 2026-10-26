# M4a — Pre-Freeze Surface & Protocol Audit

**Date:** 2026-10-01 · **Target:** `M4A_LEVEL_CONTROLLED_PROTOCOL_v1.0.md` (DRAFT, not frozen)
**Scope:** pre-freeze audit only. **No forward outcome, P&L, confirmation statistic, or fresh-outcome read.**
Surface inspection is meta/feature-level (coverage, span, CA, sessions); one synthetic math check (no market data).

## Verdict: **BLOCKED**

The single fresh cross-sectional candidate named in the protocol — the **vendor N100 1m store** — is **not fresh** and
**cannot be provenance-certified**. No other fresh cross-sectional equity surface exists, so the level-controlled M4a
confirmation is blocked pending a genuinely new surface. Four surface blockers, plus two required protocol-text fixes.

---

## 1. Vendor N100 1m candidate — surface audit

| Item | Finding | Status |
|---|---|---|
| **Unread?** | **NO.** The same vendor bundle (Nifty50+Next50, 100 CSVs, **89.2 M rows, 2015-02-02 → 2025-08-06**) was read at **signal** level by the MRLC archive test — OOS 2015-02→2022-12 and overlap 2023-01→2025-08 (`MRLC_ARCHIVE_TEST_2026-08-31.md`; register E-3; ledger MRLC detail; `data/mrlc_test/archive_candles.duckdb`). Our store's kept rows = **89,238,540** — an exact match. Per **GR-1.2/GR-1.3** the observations are spent. | **BLOCKER** |
| **Provenance** | Vendor, **undocumented aggregation**: `DATA_STORE_MAP.md` — "Unknown", "Vendor (unknown agg)", "Vendor 1m bar provenance undocumented". Only cross-checks are ISD **G7e** (tick alignment) and **G7f** (782 CA seams, fabricated=0). No ingest spec. | **BLOCKER** |
| **Entity coverage / PIT** | **Survivorship-shaped near-present list.** 100 files (1 unresolved); only **82/100 present by 2015-02-05**, **15 start ≥2016**, entry dates vary (ADANIENSOL 2015-07-31; RELIANCE/ABB etc. from 2015-02-02). Names delisted since 2015 are absent. Matches `PTMS_N100_INTENDED_EXPERIMENT_AUDIT`: "only 56 of that day's 100 PIT members have a file". Not a PIT universe. | **BLOCKER** |
| **Date span** | 2015-02-02 → 2025-08-06 (all files end 2025-08-06); 2,481–2,605 sessions/file. | PASS (span) |
| **CA treatment** | **Adjusted / internally continuous** (MRLC verified RELIANCE 2024-10-28 ex-date; ISD G7f 782 seams, fabricated=0). Daily `r` from adjusted OHLC is safe. | PASS |
| **Session completeness** | Quarantines: **28** invalid-OHLC sessions, **29** short sessions, **100** subminute sessions, **truncated tail 2025-03-05**. Direct probe: bars/session median 375 but **min 55–60**, max 378–388; timestamps run to **19:29** (out-of-hours residual bars). Store not clean. | PASS w/ pinned filters |
| **1m→daily construction (protocol §8.4)** | Feasible: OHLC present; bars **start-labelled** modal 09:15…15:29 (`modal_first_minute`=555, `modal_last_minute`=929); daily H/L/C derivable. Volume units unknown (not needed for range). Requires the explicit regular-session filter + quarantine handling. | PASS w/ caveats |

**Blockers:** (1) already read at signal level; (2) provenance uncertifiable; (3) survivorship-shaped non-PIT universe;
(4) known incompleteness/defects. The protocol's §8.2 line "Unread (only RELIANCE read)" is **factually false**.

**Consequence.** With the vendor surface blocked, **no fresh cross-sectional equity surface remains** — equity EOD 2023+
(R-11 spent), equity 1m 2023+ (E-1/E-2/E-3 spent), futures EOD (spent). The only genuinely unread surfaces are
**single-series** VIX (V-0b 1m 2022-2026; V-0c EOD 2010-2025). Those can support at best a **time-series** version of the
design (no cross-section, no date-FE identification) — a material downgrade requiring a separate decision.

---

## 2. Protocol items checkable outcome-free

| Protocol item | Audit | Status |
|---|---|---|
| §3.1 daily range `(H−L)/C_{s−1}` | Computable; consistent with data; adjusted view / adjusted store | PASS |
| §3.2 simple-mean ATR 10/60 | Feature-only; 60-session warmup feasible | PASS |
| §3.3–3.4 `a,b,x`, `y=log(F_h/ATR10)` | Feature-only; definition internally consistent | PASS |
| §4.3 knots q10…q90 = −3.792 … −2.814 | Reproduce from the dev panel; **record exact finite-filtered population at freeze** | PASS (minor) |
| VIF(x \| flexible a) ≈ 1.57 | From `x ~ cubic(a)` **without** date FE / pinned basis; **recompute with the pinned spline + date FE at freeze** | PASS (minor) |
| §4.4 date FE | Feasible (3,166 sessions) | PASS |
| §7.1 within-(date,`a`-decile) rank | Feasible; median 41 names/(date,decile) | PASS |
| §7.2 decile-dummy robustness | Feasible — **but see §3** (identity fails there) | PASS w/ text fix |
| §10 two-way cluster (entity×date) | Kernel exists in `scripts/vwap_rev/stats.py` | PASS |
| §11 family = 2 cells, Holm | Arithmetic consistent | PASS |
| §12 MDE = 2.49·SE | `z₀.₉₅+z₀.₈₀ = 2.4866`; formula correct | PASS |
| §13 missingness/attrition | Feasible; accounting identity implementable | PASS |
| §14 CA/PIT rules | CA rule correct; **PIT rule inapplicable to a non-PIT fixed list** | PASS w/ surface block |
| §15 closure mapping | Consistent with ledger C4–C9 vocabulary | PASS |
| §18 checklist item 1 (fresh surface) | **Cannot be closed** — vendor blocked | **BLOCKER** |

---

## 3. Mathematical audit — is `β = −γ` exact as written?

**Model B (protocol):** `y = α_t + f(a) + γ b + ε`.
**Model X (proposed):** `y = α_t + f(a) + β x + ε`, with `x = a − b`, i.e. `= α_t + [f(a)+β a] − β b`.

The identity `β = −γ` is **exact iff the control space of `f` contains the linear function `a`** (so `f(a)+βa` is itself an
admissible `f`). A **natural cubic spline contains `1` and `a`** (linear functions have zero second derivative, satisfying the
natural boundary condition). Hence:

- **Pinned spline `f`:** `β = −γ` is **exactly true** (not merely "near-identical"). Synthetic check (20 k rows, spline 6 df):
  `γ = −0.29882764`, `β = 0.29882764`, `|β − (−γ)| = 4.4e-15`.
- **§7.2 within-date decile dummies:** `a ∉ span(step functions)`, so `f(a)+βa` is **not** a step function; the X-form adds an
  uncontrolled within-bin linear-in-`a` term. The identity **fails**: `γ = −0.28760`, `β = 0.30054`, diff `0.0129` (≈4.5 %).

**Finding:** the protocol's wording — *"algebraically exact when `f` is linear in `a`; numerically near-identical under the
flexible `f`"* — is **not mathematically exact**. It **understates** the primary case (exact for the pinned spline) and
**overstates** the decile case (where it is false). **Required fix:** state that `β = −γ` is exact for any control space
containing the linear term (the pinned natural spline qualifies); and in §7.2 report the coefficient of the regressor
actually used rather than asserting `β = −γ`. This is a **prose/estimand-language correction**, not a mechanism or
estimator change. Severity: must-fix before freeze; not itself a surface blocker.

---

## 4. Verdict and exact blockers

**BLOCKED.**

1. **Surface not unread** — vendor N100 1m (2015-02→2025-08, 89.2 M rows) read at signal level by the MRLC archive test
   (E-3; ledger; identical row count to `archive_candles.duckdb`); GR-1.2/GR-1.3 apply. Protocol §8.2 is false.
2. **Provenance uncertifiable** — vendor, undocumented aggregation (DATA_STORE_MAP: "Unknown").
3. **Survivorship / non-PIT** — 82/100 files at 2015-02-05, 15 start ≥2016; delisted names absent.
4. **Known defects** — 28 invalid-OHLC + 29 short + 100 subminute sessions; truncated tail 2025-03-05; out-of-hours bars.
5. **Protocol text** — `β = −γ` claim not exact as written (fix §4.2/§5; scope §7.2).

**Required to unblock:** a genuinely fresh, provenance-certified surface that is either (a) cross-sectional equity 1m/EOD
with PIT membership, or (b) an operator decision to run the **single-series VIX** design (V-0b/V-0c) with its
non-cross-sectional identification and a register row written before the read. Until then, the protocol cannot be frozen
and no confirmation is possible. No outcome was read, nothing frozen, no Vault/ledger edit.
