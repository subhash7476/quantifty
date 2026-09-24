# Basis-Momentum vs. Ship-Carry — Decision Review

**Generated:** 2026-07-26
**Question posed:** after the IVOL SEALED FAIL, choose between (1) ship Carry to implementation,
or (2) explore basis-momentum (Boons–Moskowitz–Pedersen) as "the one genuinely
different-in-kind idea left."
**Verdict:** the option set as posed is wrong. Neither option is the best available move.

---

## 1. The load-bearing factual error

The proposal describes `data/signal_engine/ts_basis/ts_signals.duckdb` as an orphan artifact —
*"someone explored it but never ran it through the gates."*

**That is false.** TS Basis is one of the most completely gated constructs in the repository:

| Artifact | State |
|---|---|
| `TS_BASIS_PHASE0_PRE_REGISTRATION.md` | **FROZEN** 2026-07-23, SHA `07265b50…` |
| `scripts/signal_engine/ts_basis/` | 7 scripts (build, net-spread, drawdown, capacity, holdout, sealed) |
| `governance/rfa/declarations/ts_basis.py` | Written |
| TRAIN read | net **+18.4%**, IC +0.070 (t=4.55) |
| HOLDOUT read | net **+14.8%**, IC +0.0412 (t=1.96) |
| **SEALED read** | **TAKEN 2026-07-24** — IC **+0.0767**, t=5.89, p=3.1e-07, net **+22.57%** |
| Drawdown / capacity | Complete |

The SEALED window was **spent on TS Basis** and returned a PASS that beats Carry's own
sealed read (+22.57% vs +20.52%).

**Why the proposal got this wrong:** it is quoting `SLEEVE_INVENTORY_REPORT.md` §7, which
flags the `.duckdb` file as having "zero script references and zero doc references." That
report was generated against the main worktree; the TS Basis work was done on branch
`carry/cadence-decay` in a separate worktree (`F:\Nifty-carry-cadence`) and merged after.
The inventory was stale the day it was written. Decisions are being made off a stale map.

---

## 2. TS Basis is blocked by a governance defect, not a signal defect

`TS_BASIS_SEALED_REPORT.md` carries a retroactive de-authorization (2026-07-25, commit `b9524cf`):
the HOLDOUT gate that authorized the sealed read was computed with **Pearson** correlation
instead of the pre-registered **Spearman** rank-IC. Recomputed correctly:

- HOLDOUT IC +0.0412, t=1.96, **p = 0.0313 > α = 0.025** → gate does **not** clear.
- Per pre-reg §6 the signal is **not falsified** (sign correct, net +14.8%) — the gate is
  **INCONCLUSIVE**.
- The sealed read's own internals are sound (Spearman used correctly inside `run_sealed.py`;
  construction and sign SHA-locked before the read). What is compromised is **selection** —
  TS Basis reached the sealed window through a gate that did not hold.

**This cannot be repaired by argument.** A p-value-based re-authorization ("p=3.1e-07
survives any multiplicity correction") is invalid: Bonferroni corrects for *many hypotheses
tested*, whereas the failure here is that *the gate deciding whether testing was permitted
was mis-implemented*. The selection process cannot be characterized, so it cannot be
principledly corrected. This repo has already ruled on exactly this shape — PSB-2's
out-of-digest "predictions verified" section was logged as a finding even though the claims
were independently verified true. Provenance matters independently of whether the number is right.

**Correct framing: the sealed read is spent and the number is known. That makes TS Basis
unverifiable by this repo's standard — not false.** The only remedy for
unverifiable-but-promising is new evidence from forward calendar time.

---

## 3. Why basis-momentum specifically is the weakest option

The proposal's own caveats (prior-adjacent, ρ~0.3–0.5, same demonstrability arithmetic) are
real but understate the problem. The decisive objection is structural:

**The out-of-sample budget is exhausted.** The 2023–2026 window has now been read three times:

| Construct | Sealed read | Outcome |
|---|---|---|
| Carry | taken | PASS (+20.52%) |
| TS Basis | taken | PASS (+22.57%) — de-authorized on selection |
| IVOL | taken | FAIL (IC +0.018 sign-flipped, −13.78%) |

Two of those three are **basis-derived**. A basis-momentum pre-registration would carry
m ≥ 3–4 at declaration and would have **no unread window to confirm on** — futures history
cannot predate 2016, so n\* stays at ~42 and the calendar lever is exhausted (the same wall
that killed FLOW at the RFA gate). A fourth read of 2023–2026 is not a sealed read; it is an
in-sample read the repo would be labelling sealed.

To be fair to the proposal: basis-*momentum* (change in basis / calendar spread) **is**
genuinely untried and is analytically distinct from TS Basis (basis *level* vs own history).
The idea is not redundant. There is simply nowhere left to validate it.

---

## 4. Two computations that decide this — both run, neither touching sealed data

Computed on TRAIN+HOLDOUT only (2016-03-31 → 2022-12-31, 71 formations), quintile
equal-weight long/short, from the existing signal stores.

### 4.1 Is TS Basis just Carry?

| Measure | Value |
|---|---|
| Signal cross-sectional rank correlation (mean per formation) | **+0.669** |
| Long/short **return** correlation | **+0.463** |

The *signals* share most of their information (+0.67), but the realized L/S *return* streams
are only moderately correlated (+0.46). Not a duplicate, not decorrelated.

### 4.2 Is the TS Basis edge smuggled market beta?

It is not. TS Basis applies **no** beta or sector neutralization (1 construction step vs
Carry's 5), which made uncompensated market exposure the leading suspect. Regressed on Nifty 50:

| Series | Beta to Nifty | Corr to market | Raw ann | Alpha ann |
|---|--:|--:|--:|--:|
| TS Basis | **+0.022** | +0.040 | +18.29% | +17.98% |
| Carry | +0.023 | +0.053 | +13.47% | +13.15% |

TS Basis is as market-neutral as the explicitly-neutralized Carry. Its outperformance is
**not** beta. (Sector exposure was not tested and remains open.)

### 4.3 The finding that actually matters

| Book | Ann return | Monthly SD | **Sharpe** |
|---|--:|--:|--:|
| Carry | +13.74% | 2.307% | 1.72 |
| TS Basis | +18.04% | 2.908% | **1.79** |
| **50/50 rank-blend** | **+20.08%** | 2.779% | **2.09** |

Two conclusions, and the second is the important one:

1. **TS Basis is not a better Carry.** Risk-adjusted it is a near-tie (1.79 vs 1.72); most of
   its higher return is simply higher volatility, which levering Carry would also buy. It is
   not a replacement for the production Carry infrastructure.
2. **TS Basis is a genuinely useful second sleeve.** At ρ=0.46 the blend delivers Sharpe
   **2.09**, ~21% above Carry standalone — a real diversification gain, and precisely the
   breadth thesis `SIGNAL_ENGINE_DESIGN.md` was built around, available from a sleeve that
   is **already built** rather than one that needs inventing.

**Caveat, stated plainly:** these numbers include TRAIN, which was burned for Carry sign
discovery. They are decision-support estimates, not a gated read, and carry an in-sample
flavour. They are sufficient to rank the options; they are not evidence of forward performance.

---

## 5. Recommendation

**Neither option as posed. Ship Carry to PAPER *and* stand TS Basis up beside it in PAPER;
start no new construct.**

1. **Ship Carry to PAPER now.** It is the only fully-validated, parity-gated, production-wired
   sleeve (44 tests, REPLAY parity +0.0 bp). PAPER is unblocked today — the four pre-freeze
   items in CLAUDE.md are LIVE gates, not PAPER gates.
2. **Run TS Basis in PAPER alongside it.** Its pipeline exists; the marginal research cost is
   near zero. Forward paper results are the *only* evidence that can resolve its de-authorization,
   and every month of paper trading is a month of genuinely unseen data. Track the realized
   Carry↔TS Basis correlation live against the +0.46 estimate.
3. **Do not open basis-momentum.** Not because the idea is bad — it is the best remaining idea —
   but because there is no unread window to validate it in. Revisit only once forward paper
   data has accumulated enough calendar time to serve as a genuine out-of-sample window.
4. **Housekeeping:** `CLAUDE.md` documents four sleeves and never mentions TS Basis, IVOL, or
   LAG. `SLEEVE_INVENTORY_REPORT.md` is stale. Both should be corrected before the next
   decision is taken off them.

---

## 6. PAPER is not LIVE — the remaining gate

Recorded because the recommendation in §5 was read as "go live." It is not. The authoritative
sequence is `CARRY_IMPLEMENTATION_BRIDGE.md` §6:

| Step | State |
|---|---|
| 1. Parity gate | **PASSED** (+0.0 bp) |
| 2. Capacity analysis | **DONE** — ADV cap is not the binding constraint |
| 3. Drawdown / regime profile | **DONE** — conservative sizing basis: net +6.96%/yr, worst month −4.59%, max DD −6.44% |
| 4. **PAPER mode — run forward for a defined period** | **NOT RUN.** Integration is closed and smoke-tested against three *historical* dates; no forward paper period has been run. |
| 5. LIVE, small size, IC-decay monitoring | Blocked on 1–4 |

Two blockers the bridge doc itself names as **"still open, documented but unsolved, and
blocking before step 5"**:

1. **Nothing refreshes `carry_facts` with new formation dates.** A forward-running PAPER
   instance will **silently stop firing** once it passes the last date `publish_facts.py` was
   run against — no error, no orders. This is the repo's own documented failure class (a
   silent no-op that looks like normal operation), and in LIVE it means a real book quietly
   stops rebalancing while still holding positions. This must be fixed *before* step 4 is
   meaningful, not before step 5.
2. **The LIVE gross-exposure policy is an explicit `NotImplementedError`.** PAPER uses a fixed
   Rs 1 Cr policy; sizing a live book off real PnL/drawdown is called out as "a separate,
   not-yet-designed decision." There is currently no code path that sizes live capital.

Additionally: broker margin reconciliation remains a deferred LIVE-only capability with **no
code** (ADR-011/012/013), and per `CLAUDE.md` no funded LIVE account exists.

**TS Basis is not a LIVE candidate at all.** Its sealed read is de-authorized (§2); only Carry
holds a valid sealed result. If both run in PAPER, only Carry is on the live track.

**Stale-doc count now three:** `CLAUDE.md` records P2 substrate certification as "Unrun" — it
is in fact **CERTIFIED**, all four arms PASS (`CARRY_SUBSTRATE_CERTIFICATION.md`, commit `18641ba`).
Together with the missing TS Basis/IVOL/LAG sleeves and the stale `SLEEVE_INVENTORY_REPORT.md`,
the project's summary docs are materially behind its actual state.

---

## 7. Reproduction

Both computations in §4 are reproducible from committed stores and touch no sealed data:
`data/signal_engine/ts_basis/ts_signals.duckdb`, `data/signal_engine/carry/signals.duckdb`,
`data/signal_engine/carry/nifty50.duckdb`, window 2016-03-31 → 2022-12-31.
