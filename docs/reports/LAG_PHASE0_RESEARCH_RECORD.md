# LAG — Lead-Lag Information Diffusion: Phase 0 Research Record

**Document type:** Sleeve research record (Phase 0 — the candidate brainstorm, the structural bet behind it, and the free-arithmetic pre-screen that gates it before any pre-registration freeze).

**Status:** Phase 0 **DRAFT, UNFROZEN — pre-RFA, pre-freeze.** No data read taken. No sealed window touched. Not authorized to proceed; this record exists to decide whether `LAG_PHASE0_PRE_REGISTRATION.md` is worth writing.

**Date:** 2026-07-25

**Origin:** Operator prompt: *"design a new sleeve, which can be paired with Carry and Trend to reach >0.80."* Two premises in that prompt were corrected during investigation (§1.1, §1.2); LAG is the resulting proposal.

**Roles (standing):** Implementation party: TBD at freeze. Lead Reviewer: TBD. Decisions: Operator.

---

## 1. Why this candidate, why now

### 1.1 Premise correction — Trend is not available to pair with

The operator prompt assumed a "Carry + Trend" base. **Trend failed §9 gate 2 at TRAIN** (`TREND_TRAIN_REPORT.md:129-135`): mean IC +0.0219 (correct sign) with t=1.13, **p=0.131** (not significant), net spread **−4.06%/yr**, second-half IC decayed to −0.0097. Trend's own §11 (`TREND_PHASE0_PRE_REGISTRATION.md:221`) states *"If (1) or (3) fails, Trend is not a viable sleeve,"* and §9 line 183 states *"no successor is auto-authorized."* Skew also failed TRAIN (p=0.255, net −10.3%/yr). Flow was killed at the RFA gate (max power 0.6053). **The engine is at 1 surviving sleeve (Carry), not 2.** Any new sleeve pairs with Carry alone in the first instance.

### 1.2 Premise correction — the data does not reach 2010 for any sleeve substrate

| Substrate | Earliest | Monthly formations available |
|---|---|---|
| SSF / stock futures (FUTSTK bhavcopy) | **2016-02-11** | ~125 |
| Stock & index options bhavcopy | 2016-02-11 | ~125 |
| Cash equity daily (adjusted view) | ~2012 | ~168 |
| Daily index (Nifty 50 / Bank Nifty / India VIX) | 2012-02-21 | ~168 |
| 1-min equities | 2024-10-17 | n/a (intraday) |

Every Signal Engine sleeve trades **futures**, so it is capped at **2016-02-11 → ~125 monthly formations**. The "2010 → 2026" window does not exist for the substrate the engine consumes.

### 1.3 The wall (documented, not opinion)

`ncp = (δ/SD)·√n`. Power 0.80 at IC ~0.03 / SD ~0.2 needs **~350 monthly formations (~29 years)**. The longest futures window holds ~125. Cadence cancels — weekly ×4 formations ÷ √4 per-formation Sharpe = no net gain (CLAUDE.md RFA section; `RFA_RETROSPECTIVE.md`). This is the documented finding that killed PSB-1 C5, PSB-2 C2, SFB-1/F1, Flow, Skew, and Trend.

### 1.4 The design answer — attack the Sharpe axis, not the calendar axis

The accumulated finding names exactly two escapes from the wall: (a) a longer calendar window (exhausted at 2016 for futures), or (b) **a genuinely higher Sharpe.** Every prior sleeve attacked (a) implicitly or died on signal quality. **LAG attacks (b) directly** — its thesis is a structural argument for why one specific anomaly should deliver a *higher* per-formation signal-to-noise in this market than the ~0.03 baseline that killed the others.

This is also the explicit guardrail: LAG is **not** fitted to clear 0.80. It is a declared, falsifiable bet that India's market structure enlarges a named anomaly. If the bet is wrong, TRAIN kills it honestly.

---

## 2. The candidate — LAG thesis

**One line:** In a high-friction, retail-heavy market like NSE, information diffuses *slowly and asymmetrically* along the sector graph — sector **leaders** (high attention, high liquidity) move first; **laggards** catch up with a measurable delay. Rank laggards by their *predicted catch-up*; long the under-reactors, short the over-reactors.

**Economic foundation:** Hou–Moskowitz (2006, *Review of Financial Studies*, "Market Frictions, Price Delay, and the Cross-Section of Expected Returns") priced **price delay** as one of the most robust anomalies in US data, and — critically for this thesis — **its magnitude scales with market frictions.** India's frictions are structurally larger than the US (retail dominance, thinner mid/small names within the SSF universe, concentrated analyst/attention coverage, higher transaction costs historically). The structural prediction: **India's delay premium should be larger than the US literature's ~0.03 IC baseline.** That is the load-bearing bet, and it is falsifiable on the first TRAIN read.

**Why the sector graph is the secret weapon:** US anomaly research largely ranks names in a flat cross-section. India has tight sector clusters (financials, IT, energy, metals, autos), and information diffusion is a *network* phenomenon — it flows along sector linkages, not uniformly. The G2-R sector classification is certified (0 unclassified names). LAG uses that structure as a first-class input, which is the part most prior candidates ignored.

---

## 3. Differentiation from the dead sleeves

| Sleeve (status) | What it ranked | LAG ranks |
|---|---|---|
| Carry (survived) | futures-vs-spot residual basis (financing / cost-of-carry) | **cross-name information timing** — orthogonal economic driver |
| Trend (dead, p=0.131) | own-name past return (directional autocorrelation) | **residual after sector-leader's lead return** (cross-autocorrelation, not own-name autocorrelation) |
| Skew (dead, p=0.255) | option-implied pessimism | **cash-market microstructure delay** — no options dependency |
| Flow (dead, RFA kill) | OI crowding / positioning | **neither positioning nor sentiment — pure diffusion speed** |

The cleanest distinction is from Trend: Trend asked "does this name's *own* past return predict its future return?" LAG asks "does the *sector leader's* past return predict this name's future return, after this name's own return is removed?" These are statistically distinct objects (cross- vs auto-correlation), and the risk that LAG collapses into "momentum in disguise" is a real, disclosed threat (§7).

---

## 4. The Sharpe-axis bet, stated as a falsifiable prediction

| Claim | Falsification |
|---|---|
| India's delay premium delivers cross-sectional rank-IC **≥ 0.04** on TRAIN | TRAIN returns IC < 0.04 → the structural bet is wrong; the candidate dies on the same arithmetic as Trend, honestly. |
| The anomaly is *not* subsumed by own-name momentum | LAG-IC after residualizing against Trend's signal stays ≥ 60% of raw LAG-IC, same sign → otherwise it is momentum in disguise and dies. |
| LAG adds breadth to the composite | LAG/Carry TRAIN-IC correlation < 0.3 → otherwise it is not a new sleeve regardless of its standalone IC. |

The first row is the load-bearing one. Everything else is hygiene.

---

## 5. Free RFA pre-screen (no data touched — pure arithmetic)

Convention (matching Carry/Trend/Skew/Flow declarations + `scripts/rfa/power.py`): `metric="rank_ic"`, noncentral-t, one-sided α = 0.05, `n* = 42` monthly formations — the **sealed projection window** 2023-01 → 2026-07, *not* the full ~125-formation history. (The gate convention is that n* is always the sealed window: the full history is split TRAIN/HOLDOUT/SEALED, and power is projected against the confirmatory sealed portion — see `governance/rfa/declarations/{trend,flow}.py`, both of which use n* = 31 / 42 sealed, not ~125.)

**Correction note:** an earlier draft of this section used a non-conventional SD band `[0.16, 0.20]` and the full-window `n = 125`, producing a "razor-thin central case" framing. That was wrong on two counts: the SD band must match the other sleeves (`[0.10, 0.18]` — identical substrate, cadence, and cross-section size, so no defensible reason to differ), and n* is the sealed window (42), not the full history. The numbers below are verified against `scripts/rfa/power.py` and are what the frozen declaration (`governance/rfa/declarations/lag.py`) uses; the pre-reg's correction note supersedes anything above that still reads otherwise.

`ncp = (δ/SD)·√n`, one-sided `tcrit = ppf(0.95, df=n−1)`:

| Corner | δ (IC) | SD | ncp (n*=42) | Power | Verdict |
|---|---|---|---|---|---|
| Optimistic | 0.045 | 0.10 | 2.916 | **0.8893** | **PROCEED** |
| Central | 0.040 | 0.14 | 1.852 | 0.5699 | below — 0.80 binds at composite |
| Pessimistic | 0.035 | 0.18 | 1.260 | 0.3426 | below |

**Formations required for power 0.80** (via `power.n_required`):
- Optimistic corner (0.045 / 0.10): **32 formations** — well inside the 42 available.
- Central corner (0.040 / 0.14): **78 formations** — unavailable (window holds 42).
- Pessimistic corner (0.035 / 0.18): **165 formations** — unavailable.

**Interpretation:** LAG clears the RFA gate at the optimistic corner (PROCEED). As with every other sleeve in the engine (Carry, Trend, Skew), the central case sits below the 0.80 standalone hurdle — **0.80 binds at the combined-engine level, not per-sleeve** (CLAUDE.md RFA section; Trend §7.1). This is the standard engine pattern, not a knife-edge. The load-bearing question — does India's delay deliver IC ≥ 0.04? — is settled only by TRAIN, which is exactly the point of the structural bet: if it pays, central rises toward the hurdle; if it does not, TRAIN kills LAG the same way it killed Trend.

Verified against `scripts/rfa/power.py`; the binding artifact is the frozen declaration `governance/rfa/declarations/lag.py` (SHA recorded in `LAG_RFA.md`).

---

## 6. Why the build is nearly free (reuses certified substrate)

LAG consumes no new ingestion and no new substrate certification:

| Input | Source | Status |
|---|---|---|
| Per-name roll-adjusted continuous returns | `data/signal_engine/trend/continuous.duckdb` (363 underlyings, 477,577 FUTSTK cells) | Built (commit `0ea419e`) |
| Sector classification (leader/laggard graph) | G2-R sector map | **Certified — 0 unclassified** |
| Beta + sector neutralization | same OLS machinery as Carry/Trend/Skew (`scripts/signal_engine/{carry,trend,skew}/neutralize.py`) | Reusable |
| Era futures fee model | existing §8 fee machinery | Reusable |
| RFA gate + power math | `governance/rfa/` + `scripts/rfa/power.py` | Reusable |

Marginal build ≈ one construction script (`build_lag.py` — leader identification + catch-up residual) + one TRAIN runner (`run_train.py`). The continuous-series work that took Trend the most effort is already done.

---

## 7. Honest caveats (disclosed before freeze, not after)

1. **Momentum-adjacent → multiplicity penalty.** Delay is *partially* subsumed by momentum in US data. LAG must declare Trend as prior-adjacent exposure: the family-wise penalty is **m ≥ 2** (Carry's read + Trend's read are both prior exposure in the momentum/diffusion neighborhood). The Bonferroni evidence floor tightens accordingly. If LAG-IC residualized against Trend's signal drops below 60% of raw, LAG is momentum in disguise and dies regardless of its standalone number.

2. **The central case is on the knife's edge.** This is not a comfortable declaration. At the available n*≈125 and central assumptions (δ=0.04, SD=0.18), projected power is ~0.80 — meaning TRAIN itself is the deciding event, not a formality. If the operator wants a margin-of-safety PROCEED, LAG does not offer one; only the optimistic corner does.

3. **The structural bet could be wrong.** India's higher frictions *could* enlarge the delay premium (the thesis), or they could mean the anomaly is already arbed by the same retail flow that creates it, or that the SSF universe (large-caps) is efficient enough that delay is small. There is no prior Indian cross-sectional delay study in the repo to lean on. The bet is reasoned, not established.

4. **Hou–Moskowitz delay in the US is a 12-month lookback, monthly formation** construct. LAG inherits that cadence. Weekly alternatives were considered and rejected — cadence cancels in the power math, and monthly is fee-safer (Trend's realized turnover at monthly was 0.69; LAG's slow-diffusion construction should be similar or lower).

5. **The sector-leader identification rule must be pinned at freeze.** Candidate definitions (largest market cap in sector, highest ADV, highest prior attention) give different leader sets. The choice is outcome-relevant and must be declared *before* any read, not selected after seeing ICs.

---

## 8. What this record is NOT

- **Not a frozen pre-registration.** No SHA-256, no bands pinned, no construction frozen. That is `LAG_PHASE0_PRE_REGISTRATION.md`, the next step if the operator authorizes.
- **Not an RFA declaration.** No `governance/rfa/declarations/lag.py` exists. The §5 numbers are hand-computed for decision support; the binding gate runs through `scripts/rfa/power.py`.
- **Not a data read.** Zero formations consumed. The TRAIN (2016-02 → 2020-12), HOLDOUT (2021-01 → 2023-12), and SEALED (2024-01 → present) windows are all untouched.
- **Not a guarantee.** LAG's central-case survival is identical to its TRAIN falsification. It may well die the same way Trend did; that is the protocol working.

---

## 9. Decision requested from operator

| Option | Meaning |
|---|---|
| **PROCEED to pre-reg** | Authorize drafting `LAG_PHASE0_PRE_REGISTRATION.md` (DRAFT) + `governance/rfa/declarations/lag.py`, then run the free RFA gate via `scripts/rfa/run_rfa.py`. Still no data read until the declaration is frozen and the gate returns PROCEED. |
| **REVISE** | Reject LAG on its merits (e.g., too momentum-adjacent, central case too thin) and brainstorm a different candidate. |
| **STOP** | Accept the engine at 1 sleeve (Carry alone); do not pursue a new construct. The documented finding supports this as a defensible outcome. |

---

## 10. Lineage and prior exposure ledger (for the eventual declaration)

| Prior read | Window | Relation to LAG | Disclosure |
|---|---|---|---|
| Carry TRAIN | 2016-03 → 2020-12 | Different economic family (basis vs diffusion); correlation to be measured on TRAIN | Disclose; m counts if correlation > 0.3 |
| Carry HOLDOUT | 2021-01 → 2023-12 | Same | Disclose |
| Carry SEALED | 2024-01 → present | Same; **Carry has spent the SEALED window for its own construct** — LAG's SEALED read is a different construct and the window is re-readable across constructs per the framework | Disclose |
| Trend TRAIN | 2017-02 → 2021-12 | **Prior-adjacent — momentum/diffusion family.** Same substrate (FUTSTK continuous) | **Disclose; m ≥ 2** |
| Skew TRAIN | 2016-07 → 2020-12 | Different family (options-implied) | Disclose |

The exact m and the Bonferroni-adjusted evidence floor are pinned at declaration freeze, not here.
