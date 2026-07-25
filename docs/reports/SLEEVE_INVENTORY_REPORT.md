# Sleeve Work Inventory — excluding Carry & Trend

**Generated:** 2026-07-25
**Scope:** All Signal Engine sleeve work **other than** Carry (sleeve #1) and Trend (sleeve #2). Covers Skew, Flow, and any other sleeve names appearing in the repo.
**Method:** Full-repo search across `docs/`, `scripts/`, `governance/`, `core/`, `tests/`, and `data/`.

---

## Critical upfront finding

**CLAUDE.md is stale regarding the Signal Engine.** It states *"No signal code exists"* and describes the strategy layer as *"intentionally unimplemented — greenfield,"* and lists Skew as only mentioned in the design doc. In reality there is a full Skew implementation (pre-reg + RFA declaration + 4 scripts + a TRAIN read that FAILED), a Flow RFA declaration that was ABANDONED, and `core/strategies/` contains `carry_strategy.py` + `knowledge_signal_source.py`. Treat the CARRY section of CLAUDE.md as historical, not current.

All six RFA declaration files in `governance/rfa/declarations/`: `carry.py`, `trend.py`, **`skew.py`**, **`flow.py`**, **`o1_vrp.py`** (plus `__init__.py`).

---

## 1. SKEW sleeve — the most-developed non-Carry/Trend sleeve

**Stage:** Pre-registration DRAFT → RFA declaration frozen → code implemented (4 scripts) → TRAIN read taken → **TRAIN FAILED (terminal).**

### Artifacts

| File | Purpose |
|---|---|
| `docs/reports/SKEW_PHASE0_PRE_REGISTRATION.md` | Phase-0 pre-registration, **DRAFT, unfrozen** |
| `governance/rfa/declarations/skew.py` | Frozen RFA declaration |
| `scripts/signal_engine/skew/build_skew.py` | §3 signal construction from option chain (`skew = iv_25d_pe - iv_25d_ce` at line 304) |
| `scripts/signal_engine/skew/volatility.py` | Black-76 IV inversion + delta-to-strike |
| `scripts/signal_engine/skew/neutralize.py` | §4 beta + sector neutralization (OLS) |
| `scripts/signal_engine/skew/run_train.py` | §6 TRAIN read → report generator |
| `docs/reports/SKEW_TRAIN_REPORT.md` | Script-generated TRAIN report — **FAIL** |
| `data/signal_engine/skew/signals.duckdb` | Built signal store (**untracked in git**) |

All 7 tracked files landed in a single commit: `da3e3ba` *"feat(skew): pre-reg, RFA declaration, build, TRAIN — §9 gate 2 FAIL (IC -0.018, t=-1.15, net -10.3%)"* (2026-07-23).

### What the declaration contained (`skew.py`)
- `name="SKEW"`, `methodology_version="2.0.0"`, `metric="rank_ic"`, **`test_type="two_sided"`**, `cadence="monthly"`, `n_available=42`
- delta `[0.020, 0.045]`, SD `[0.10, 0.18]`
- **Two-sided test is the headline design choice** — the sign is deliberately NOT pre-committed (the "explicit lesson from v1-Carry, where a one-sided bet on an ambiguous sign burned a whole registration"). TRAIN establishes existence *and* reveals the sign.
- Signal: risk-reversal skew = `IV(25Δ put) − IV(25Δ call)` (pinned, no post-hoc switch to the Xing ATM-smirk variant). Provenance cites Xing–Zhang–Zhao 2010, An–Ang–Bali–Cakici 2014, Bali–Hovakimian.
- Universe: narrower than Carry/Trend — liquid options subset (~top 50–100 by 20-day option turnover).

### TRAIN result (`SKEW_TRAIN_REPORT.md`) — **FAIL, terminal**
- TRAIN period 2016-07-01 → 2020-12-31, 54 formations, 4901 signal-return pairs
- **Mean IC −0.0183, SD 0.1172, t = −1.1505, p = 0.255 (two-sided, NOT significant)** → existence test FAIL
- Sign read NEGATIVE (steep put skew → lower returns); report notes this is OPPOSITE to the TRAIN-direction literature alignment
- Net Q5−Q1 = **−10.31% annualized** (gross −0.83%, fee drag 45.2 bp/yr at 0.8 turnover) → net-spread test FAIL
- IC SD 0.1172 inside `[0.10, 0.18]` → the only test that PASSED
- Pre-registered predictions: P1 REJECTED, P4 REJECTED, P2 PENDING HOLDOUT, P3 NOT TESTED
- Verdict (`SKEW_TRAIN_REPORT.md:65`): *"FAIL — do not proceed to HOLDOUT"*

### What does NOT exist for Skew
- **No `SKEW_RFA.md` report** — `scripts/rfa/run_rfa.py` writes to `docs/reports/{name}_RFA.md`, and `SKEW_RFA.md` is absent. The pre-reg §5 hand-computes the optimistic-corner power (~0.83 → PROCEED), but the gate report was never generated/saved. (By contrast `CARRY_RFA.md` and `TREND_RFA.md` both exist.)
- No `SKEW_HOLDOUT_REPORT.md`, no `SKEW_SEALED_REPORT.md` (TRAIN failed, so the walk-forward stopped)
- No `tests/signal_engine/skew/` directory — the pre-reg §8 planned it; never created
- No lead-review doc, no substrate-certification spec, no `core/strategies/skew_strategy.py`
- Methodology gap self-flagged at `SKEW_TRAIN_REPORT.md:91`: Prediction 3 (neutralization survives) was *"NOT TESTED (z_skew_neut used directly; raw vs neutralized comparison not computed)"*

### One-line summary
Skew was fully built out to a TRAIN read on a two-sided risk-reversal construct; it failed both the existence test (p=0.255) and the net-spread test (−10.31%/yr) and is stopped at TRAIN — no HOLDOUT, no sealed read, no tests, no composite wiring.

---

## 2. FLOW sleeve — RFA-declared, then ABANDONED by the gate

**Stage:** RFA declaration frozen → gate verdict ABANDON (dispositive). **No code, no TRAIN read, no tests.**

### Artifacts

| File | Purpose |
|---|---|
| `governance/rfa/declarations/flow.py` | Frozen RFA declaration (SHA-256 `d7a54cfb…`) |
| `docs/reports/FLOW_RFA.md` | Gate report — **VERDICT: ABANDON** |
| `docs/reports/SIGNAL_ENGINE_DESIGN.md` §2.2 (lines 88-143) | The "respecced, then ABANDONED" correction narrative |

Landed in commit `18641ba` *"feat(rfa): FLOW ABANDON — gate's first live kill, independently verified."*

### What the declaration contained (`flow.py`)
- `name="FLOW"`, `methodology_version="2.0.0"`, `metric="rank_ic"`, **`test_type="one_sided"`**, `cadence="monthly"`, `n_available=42`
- delta `[0.015, 0.030]`, SD `[0.10, 0.18]`
- **Direction committed: NEGATIVE rank-IC** (crowding reversal). "Short high pressure, long low pressure." Sign committed at declaration, cannot flip after TRAIN.
- Signal: per-name futures OI dynamics (signed ΔOI vs ΔP → long buildup / short buildup / long unwinding / short covering), accumulated pressure mean-reverts. Argued on Stein 2009, Jegadeesh 1990, Lehmann 1990.
- Band deliberately set **below Carry's** `[0.020, 0.045]` for three stated reasons (no participant attribution; heavily-mined retail heuristic; monthly reversal structurally weaker than weekly).

### Why it was ABANDONED (`FLOW_RFA.md`)
- **Max achievable power 0.6053** at the optimistic corner (δ=0.030, SD=0.10, n=42) — below the 0.80 hurdle.
- Formations required for 0.80: **71 optimistic / 241 central / 892 pessimistic**, against **42 available**.
- Futures history cannot predate 2016 (SFB-1/F1 lockdown), so n* cannot be raised — the calendar lever is exhausted.
- Independently reproduced from `scripts/rfa/power.py`.

### History (the respec story, `SIGNAL_ENGINE_DESIGN.md` §2.2)
The original Flow was *"informed positioning"* based on participant-wise OI (FII/DII/Client/Pro). A live NSE file was fetched (`fao_participant_oi_20072026.csv`) and found to contain **exactly four aggregate rows with no per-underlying breakdown** — so it cannot rank names cross-sectionally and the informed-flow economics do not transfer. It was respecced to per-name aggregate OI from `futures_bhavcopy.open_int`/`chg_in_oi` (no ingest needed, 100% populated), then killed by the gate on the weaker economics. **Flow receives no TRAIN read** — cost was one declaration file, zero data reads.

### Significance
Described as *"the gate's first real kill, and it worked exactly as designed"* — the first time the RFA gate fired on a live construct rather than in retrospect. The engine therefore became the **3-sleeve case** (Carry+Trend+Skew, central composite power ≈ 0.75, below the 0.80 hurdle that must now be cleared empirically by the composite).

### What does NOT exist for Flow
- No `scripts/signal_engine/flow/` directory, no code at all
- No pre-registration doc (Flow went straight to RFA declaration per `SIGNAL_ENGINE_DESIGN.md` §8 step 1)
- No TRAIN report, no tests
- `SIGNAL_ENGINE_DESIGN.md` §3 build-order line 159: *"Not built, not read, no successor authorized by this outcome."*

### One-line summary
Flow was specced as informed-positioning, respecced to per-name OI crowding/reversal after NSE's participant-OI file turned out to be aggregate-only, then killed by the RFA gate at max power 0.6053 before any data was touched — the gate's first live kill.

---

## 3. Other sleeve names — all mentioned-only / parked

These appear in `docs/reports/SIGNAL_ENGINE_DESIGN.md` only. **None has any artifact beyond the mention** (no pre-reg, no declaration, no code, no tests).

| Sleeve name | Where mentioned | Stage | Notes |
|---|---|---|---|
| **Basis-momentum** (Boons–Prado 2019) | `SIGNAL_ENGINE_DESIGN.md:70` ("✅ (later) — Multi-expiry per name is in FUTSTK bhavcopy — free add") and line 230 ("Additional sleeves considered and parked") | Mentioned-only | Also referenced in `CARRY_DATA_GAP_AUDIT.md:59` as a "free later add." `data/signal_engine/ts_basis/ts_signals.duckdb` (2.6 MB) exists on disk but **has no scripts and no doc references anywhere** — an orphan artifact, not a built sleeve. |
| **Short-term reversal** | `SIGNAL_ENGINE_DESIGN.md:231` | Mentioned-only (parked) | No signal-engine artifact. (Note: short-term reversal was a PSB-1 *cash-equity* candidate C1, but that is a different, closed battery — not a signal-engine sleeve.) |
| **Betting-against-beta / low-vol** | `SIGNAL_ENGINE_DESIGN.md:231` | Mentioned-only (parked) | No artifact. (PSB-1 C5 was a cash-equity low-vol candidate; closed, not a signal-engine sleeve.) |
| **Dealer-gamma (GEX) intraday regime** | `SIGNAL_ENGINE_DESIGN.md:231` | Mentioned-only (parked) | GEX exists as a *display metric* in `core/analytics/options_analytics.py` (options dashboard), but is **not** wired as a signal-engine sleeve. `SIGNAL_ENGINE_DESIGN.md:84` reserves GEX/VRP/term-structure for a "later index increment." |

---

## 4. VRP / O1 — a separate index-options track (NOT a v1 signal-engine sleeve)

Included for completeness because the search terms (VRP, variance risk premium, risk reversal) overlap. This is **not** one of the four SSF cross-sectional sleeves — it belongs to a different research lineage in `docs/reports/OPTIONS_STRATEGY_RESEARCH.md` (candidates O1/O2/O3).

| File | Purpose |
|---|---|
| `governance/rfa/declarations/o1_vrp.py` | O1 declaration — `metric="per_trade_pnl"`, weekly, n=380, delta `[0.002, 0.005]`, SD `[0.025, 0.060]` |
| `docs/reports/O1_RFA.md` | Gate report — prints PROCEED but **withdrawn** |
| `docs/reports/RFA_GATE_O1_REVIEW.md` | §1 documents the withdrawal finding |

**Status: WITHDRAWN 2026-07-21.** The PROCEED verdict was an artifact of a crossed optimistic corner: delta was derived from SD via a Sharpe translation (coupled bands), but the gate assumed independence and evaluated (δ_hi, SD_lo) → implied annualized Sharpe 1.442, above the declaration's own ceiling of 1.0. Read coherently, both endpoints sit at Sharpe ≈ 0.59 → max power ≈ 0.49 → ABANDON. The declaration file is preserved unedited so its digest still verifies; **no successor authorized.**

---

## 5. Coverage matrix — what exists vs. what is mentioned-only

| Sleeve | Pre-reg | RFA decl | RFA report | Code | Tests | TRAIN | HOLDOUT | SEALED | core/ wiring |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Skew** | DRAFT | yes | **no** | yes (4 scripts) | **no** | **FAIL** | no | no | no |
| **Flow** | no | yes | yes (ABANDON) | no | no | no | no | no | no |
| O1/VRP* | — | yes | yes (WITHDRAWN) | no | no | no | no | no | no |
| Basis-momentum | no | no | no | no | no | no | no | no | no |
| Short-term reversal | no | no | no | no | no | no | no | no | no |
| BAB / low-vol | no | no | no | no | no | no | no | no | no |
| Dealer-gamma (GEX) | no | no | no | no (display metric only) | no | no | no | no | no |

\* O1/VRP is a separate index-options track, not an engine sleeve.

*(Carry and Trend are excluded from this report by scope. For reference: both have pre-reg + RFA declaration + RFA report + code; Carry has tests, TRAIN, and SEALED; Trend has TRAIN.)*

---

## 6. Key findings with exact locations

- **Skew TRAIN FAIL verdict** — `docs/reports/SKEW_TRAIN_REPORT.md:65` — *"**TRAIN verdict:** **FAIL** — do not proceed to HOLDOUT"*. Headline numbers at lines 13-18 (Mean IC −0.0183, SD 0.1172, n 54, t −1.1505, p 2.551e-01) and line 43 (Net −10.31% annualized).
- **Skew two-sided design rationale** — `docs/reports/SKEW_PHASE0_PRE_REGISTRATION.md:11-23` (§1) and `governance/rfa/declarations/skew.py:7` (`test_type="two_sided"`).
- **Skew signal construction (risk-reversal pinned)** — `docs/reports/SKEW_PHASE0_PRE_REGISTRATION.md:43-44`, implemented at `scripts/signal_engine/skew/build_skew.py:304`.
- **Flow ABANDON verdict** — `docs/reports/FLOW_RFA.md:3` (*"VERDICT: ABANDON"*) and line 17 (max achievable power 0.6053); formations table at lines 31-36.
- **Flow declaration (frozen)** — `governance/rfa/declarations/flow.py:3-13` (name, metric, one-sided, bands); SHA-256 `d7a54cfb…` recorded at `FLOW_RFA.md:6`.
- **Flow respec + ABANDON narrative** — `docs/reports/SIGNAL_ENGINE_DESIGN.md:88-143` (§2.2); struck-through build-order entry at line 159.
- **Sleeve composition table (authoritative)** — `docs/reports/SIGNAL_ENGINE_DESIGN.md:42-54` (Carry, Trend, ~~Flow~~, Skew); parked sleeves at lines 230-231.
- **O1/VRP withdrawal** — `docs/reports/O1_RFA.md:3-9` (withdrawal banner); detailed in `docs/reports/RFA_GATE_O1_REVIEW.md` §1.

---

## 7. Flagged unexplained artifact

`data/signal_engine/ts_basis/ts_signals.duckdb` (2.6 MB) exists on disk but has **zero** script references and **zero** doc references anywhere in the repo (confirmed via grep across `*.py` and `*.md`). It is untracked. It is not associated with any declared sleeve and may be an ad-hoc/exploratory build artifact. Flagged for completeness — the files do not substantiate a "ts_basis sleeve."

---

## Bottom line

Beyond Carry/Trend, only **Skew** received real build work — and it is dead at TRAIN (p=0.255, net −10.3%/yr, no HOLDOUT, no tests, no composite wiring, missing its own RFA gate report). **Flow** died at the RFA gate before touching any data (the gate's first live kill). Every other sleeve name (Basis-momentum, Short-term reversal, BAB/low-vol, Dealer-gamma) is mentioned-only in `SIGNAL_ENGINE_DESIGN.md` with zero artifacts. The engine is effectively Carry+Trend standing; the 0.80 composite-power hurdle must clear empirically after the next TRAIN reads.
