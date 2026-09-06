# NiftyShield — Adoption Assessment

**Date:** 2026-08-07
**Strategy identity (reserved):** `nifty_shield_v1` (Promotion Ledger E004, status DEVELOPMENT)
**Status:** Stage 0 (DEVELOPMENT) — assessment / spec of record. No strategy code exists in this repository.
**Authored by:** Claude (Opus 4.8). Author *proposes* with evidence; author grants nothing (MM12.5 §8).
**Governing documents:** `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` (the pipeline); `docs/STRATEGY_PROMOTION_LEDGER.md` (the ledger); `CLAUDE.md` Architecture Principles #1–#3; ADR-002, ADR-016, ADR-021.
**Source bundle:** `F:\nifty_research_bundle\` (assembled 2026-08-07 from the retired `D:\BOT\root` platform).

---

## 0. Verdict

NiftyShield is adopted **through the MM12.5 Strategy Promotion Pipeline as a new external
strategy at Stage 0** — *not* through the research track (RFA → pre-registration →
TRAIN/HOLDOUT/SEALED). This routing decision is the load-bearing content of this document,
because it determines which protocols apply and — more importantly — which protocols
*cannot be broken* because they never engage.

Two findings follow from the routing and are established mechanically below:

1. **No sealed research window is spent and no pre-registration is consumed by adoption.**
   The de-authorization mechanism that retired TS Basis and IVOL operates on the research
   track only; it is structurally absent here (§2, §3).
2. **The bundle cannot be copied in as-is.** The bundled `nifty_shield_strategy.py` fails
   Stage 1 CONFORMANT by static inspection — it violates the `SignalSource` import and
   handle contract and side-effects inside `on_bar`. The README's "copy to
   `core/strategies/` + wire 5 glue objects" is the *dead platform's* architecture and
   would produce an un-certifiable strategy (§4). The **design** is adopted; the **code**
   is re-expressed against this platform's contracts.

The single concrete protocol landmine available during this work is the OSC-preserved
unread Nifty index-options window; §3 makes avoiding it an explicit prohibition.

---

## 1. What is being adopted, and what it is not

The bundle carries three pieces. Only one is a *strategy*; the routing below is about that
one. The other two are consumed infrastructure and are **out of scope for this branch**
(§7), noted here only to fix their governance category:

| Piece | Governance category | Where it goes |
|---|---|---|
| **NiftyShield** (`nifty_shield_strategy.py`) | **Strategy** → MM12.5 promotion pipeline | `nifty_shield_v1` identity; this assessment |
| DayType engine (`daytype_engine.py`) | **Analytics/state dependency** (Principle #2 — offline facts, runtime read-only) | future infra branch; a *dependency* of the strategy, not part of its identity except via content-hash (§5.1) |
| sweep_filter (K-line tokenizer + logistic) | **Research act if used to gate entries** — its own pre-registration | kept *out* of `nifty_shield_v1` entirely (§5.4) |

NiftyShield is a regime-adaptive weekly Nifty options **premium seller**: at 13:00 it reads
a DayType regime + India VIX, selects a structure (short straddle / strangle / iron fly /
bull-put / bear-call), and manages to a 50%-capture / 2×-stop / 15:15 / delta-adjust exit.
It is a rule-based directional-neutral options strategy — not a cross-sectional statistical
construct.

---

## 2. Routing: MM12.5 (safety), not RFA (alpha)

This repository runs **two separate governance systems**. Conflating them is exactly how a
protocol gets "broken":

| | Research track (RFA → pre-reg → sealed) | **Promotion pipeline (MM12.5)** |
|---|---|---|
| Certifies | *Alpha* — statistical demonstrability (power ≥ 0.80) | *Safety* — contract-obedience, determinism, risk-bounding (§1.1: "certifies safety, **not** alpha") |
| Evidence substrate | A **fixed** historical window (TRAIN/HOLDOUT/SEALED) | **Forward-generated** PAPER sessions accruing on the calendar (§7.3) |
| Pass/fail on P&L? | Yes — net spread, power | **No** — PnL is the Account Owner's Stage 3→4 input, never a pipeline criterion (§1.1) |
| De-authorization seen in this repo | TS Basis (wrong test on a gated window), IVOL (sealed regime flip) | — |
| NiftyShield belongs here? | **No** | **Yes** |

MM12.5 §6.1 is explicit that a *port of a historical design* is "architecturally identical
to brand-new strategies" (MM12.1 §14.2) and walks the same five stages, no stage skipped.
NiftyShield is precisely such a port. Its external backtest is **Stage-0 strategy-owned
evidence, "filed, not graded"** (§3.2, §4.0(d); ADR-002 — the platform hosts no research).

**Consequence:** adoption consumes no pre-registration and spends no sealed budget. The
alpha of NiftyShield is validated at **Stage 2 by forward PAPER** (§7.3: ≥20 sessions AND
≥30 round-trips), which draws on *no* historical gated window. The mechanism that
de-authorized TS Basis — opening a sealed read on a gate that did not hold — has no
counterpart in the promotion pipeline, because there is no sealed read to open.

### 2.1 Why RFA is Not Applicable — documented, not silently skipped

A silent omission of the RFA gate is the kind of gap a future reviewer challenges. It is
recorded here as a reasoned **non-applicability**, with two independent reasons:

1. **RFA presupposes a fixed available sample.** The gate's question is "given the
   formations *actually available*, can this construct reach power 0.80?" — an inversion
   over a fixed n (`scripts/rfa/power.py`). Forward PAPER has no fixed n; the window
   extends until §7.3 is satisfied. The gate's core input does not exist for this construct.
2. **Filing one would be actively harmful.** NiftyShield expressed as a single-instrument
   P&L series is a `per_trade_pnl` construct. The RS-MOM structural finding (`RS_MOM_RFA.md`;
   `CLAUDE.md` RS-MOM entry) establishes that any single-/two-index `per_trade_pnl`
   declaration returns **ABANDON** on the demonstrability wall (`ncp = S·√T`, √T fixed). The
   RFA would issue a kill it was never designed to issue on a rule-based options seller whose
   authorization path is forward paper, not a sealed statistical read. Running it would
   manufacture a spurious ABANDON verdict against a strategy the framework does not govern.

RFA is therefore **not run** for `nifty_shield_v1`. This paragraph is the record of that
decision.

---

## 3. PROHIBITION — the OSC unread index-options window

**Do not backtest NiftyShield over Nifty index-options history to "re-validate the Sharpe
on real option marks."**

The OSC construct preserved the Nifty index-options window **2016-02-11 → 2022-12-31
(1,701 daily formations) explicitly UNREAD** (`CLAUDE.md` OSC section;
`OSC_RFA_ABANDON.md`). A backtest of NiftyShield over that span — which the bundle README's
§3c caveat ("the P&L must be re-validated against real option marks") walks directly toward
— would **spend that window on an ungated read presented as validation**. That is the one
concrete protocol breach available in this work, and it is exactly the shape of the breach
that de-authorized TS Basis: a validation read taken outside the gate that authorizes it.

The safe path is the one MM12.5 already mandates and requires no historical option-mark
backtest at all: **Stage 2 forward PAPER only**, on live/near-real option marks, accruing on
the calendar. The Sharpe-9.40 backtest stays where §4.0(d) puts it — filed as intent, never
re-run as platform evidence.

This prohibition is binding on every downstream artifact and implementer prompt derived from
this assessment.

---

## 4. The bundled strategy fails Stage 1 CONFORMANT as-copied — mechanical finding

Stage 1 requires a **well-formed, deterministic, side-effect-free `SignalSource`** passing
the `SignalSourceConformanceSuite` (`core/runtime/conformance.py`), Layer 1 (static) and
Layer 2 (behavioral). The bundled `nifty_shield_strategy.py` fails Layer 1 by static
inspection on three independent counts. "Evidence is mechanical or it is not evidence"
(§1.2), so each is cited to the code.

### 4.1 Sanctioned-import violation (Layer 1 check on import surface)

`conformance.py` pins `SANCTIONED_IMPORT_PREFIXES = ("core.events",
"core.runtime.signal_source")` — the *only* `core.*` imports an external strategy may carry.
The bundled file's module-level imports (`nifty_shield_strategy.py:22–28`) are:

| Import | Sanctioned? |
|---|---|
| `core.state.daytype_engine` | ✗ violation |
| `core.execution.options.selector` | ✗ violation (also §4.2) |
| `core.instruments.option` | ✗ violation |
| `core.risk.greeks.black76_engine` | ✗ violation |
| `core.logging` | ✗ violation |
| `core.analytics.capture` | ✗ violation |
| `core.events` (`SignalType`) | ✓ sanctioned |

Six of seven `core.*` imports are boundary violations. (The README §3b also names lazy
reaches into `core.database`, `core.brokers.upstox_market_data`, and
`core.instruments.instrument_db` via the injected `db_manager` — additional violations, but
the six static ones already fail the gate.)

### 4.2 Forbidden-handle violation (`check_no_forbidden_handles`)

`FORBIDDEN_HANDLE_MODULE_PREFIXES = ("core.execution", "core.brokers")`. No instance
attribute may hold an object from those layers. NiftyShield holds an `OptionsContractSelector`
(`core.execution.options.selector`) as an attribute, and — in live mode — an
`UpstoxMarketData` (`core.brokers`). Both are contraband under the behavioral check.

### 4.3 Side-effects inside `on_bar` (the §5.2 core invariant)

`SignalSource.on_bar` "MUST be side-effect-free with respect to platform state"
(`signal_source.py:44`). The bundled strategy's bar path invokes `_init_db`
(`:131`), `_persist_signal` (`:775`), `_persist_trade_entry` (`:797`),
`_persist_trade_exit` (`:826`), `_fetch_vix_close` (`:712`), and `_has_open_trade_today`
(`:340`) — DB writes and network I/O. A strategy that persists trades and fetches LTP inside
the loop is definitionally not side-effect-free.

### 4.4 What the README's compatibility table actually verified

Bundle README §3a checked NiftyShield's **call signatures** against `Black76Engine`,
`OptionsContractSelector`, and `Option` — and those are genuinely compatible. But it never
checked **contract** compatibility with `SignalSource`, because the dead platform had no such
contract. §3a is real and narrow; it does not bear on certifiability.

### 4.5 The re-expression, not a port

The **design** — regime read → structure choice → strike selection → position sizing →
exit management — is the asset (README §3c). It is re-expressed against this platform's
contracts as:

- a **dumb `SignalSource`** (`nifty_shield_v1`) that at the 13:00 bar reads DayType + VIX,
  chooses a structure and strikes, and emits `SignalEvent`s **only** — Principle #1
  ("Strategies Stay Dumb");
- **sizing, greeks, margin, and exit management owned by `core/execution/`** — Principle #3
  ("Execution Owns Reality"). `Black76Engine` and `NseMarginEngine` already exist there;
- **persistence via the platform ledger/journal**, not a strategy-owned DB.

The detailed re-expression is the Decomposition Spec
(`docs/reports/NIFTY_SHIELD_DECOMPOSITION_SPEC.md`); the build is a DeepSeek deliverable from
the Stage 1 implementer prompt. This assessment fixes only that the copy-in path is invalid
and the decomposition path is the one taken.

---

## 5. Carry-forward constraints (each de-authorizes work later if missed)

### 5.1 The DayType model is an identity hole (§2)

Certification identity is `(strategy_id, code_ref, config_hash)`. The DayType 13pm model is a
`.pkl` at a hardcoded path *outside all three*. Retraining the model while holding the triple
fixed changes emitted signals, voiding §2 ("evidence produced under one identity is void for
any other") and the §7.2 determinism contract. **Fix at Stage 0**, one of:
(a) content-hash `model.pkl` / `scaler.pkl` / `metadata.json` and record the digest in the
datasheet + ledger note; or (b) vendor the model *inside* the strategy package so `code_ref`
covers it. Option (b) is preferred — it makes identity self-contained. This is the single
most likely way a reviewer later voids a Stage 1 grant, so it is pinned before any code.

### 5.2 The max-DD declaration is a trap (§7.4.3)

Declared max DD is binding at every trading stage; the drawdown gate tripping **is** the
breach, there is no "explainable breach" carve-out, and a breach forces a **new identity**
(Stage 0 restart). A short-straddle/strangle seller carries a fat left tail, and the
backtest's DD was produced under **flat IV, no gap modeling** (§6) — precisely the number the
declaration must *not* be derived from, or it arms an automatic F2 demotion on the first real
overnight gap. The risk declaration (datasheet) must set max DD from a **stress view of the
tail** (gap + vol-spike scenario), not from the optimistic backtest DD, and state that
derivation explicitly.

### 5.3 Round-trip counting convention + timeline (§7.3)

Stage 2 needs ≥20 sessions **AND** ≥30 completed round-trips. NiftyShield is an **intraday**
seller (enters 13:00, hard-exits 15:15 same session — `exit_time`), so it does ~1
round-trip/*session*, not ~1/week — the §7.3 floor is reachable in ~35–45 sessions (~2 months),
not the ~30 weeks a multi-day holder would need. Two conventions must be pinned in the
datasheet **before** the window runs (deciding after seeing the count is the post-hoc sin
this repo punishes):

1. **Whether one multi-leg structure counts as one round-trip or several.** Undefined in
   MM12.5. Pin it. (Recommendation, to record in the datasheet: one *structure* open→close =
   one round-trip, so the count reflects decisions, not legs.)
2. **The realistic window.** Use §7.3's escape hatch: accept the **60-session window
   (~3 months)** with any round-trip shortfall **ledgered as an accepted deviation, visible
   forever** — not silently waived.

### 5.4 sweep_filter is a research act, kept out of the identity

Adopting sweep_filter *as a library* is safe. Training a Nifty classifier and gating
NiftyShield entries on its probabilities is a **research act with selection degrees of
freedom** — the exact TS Basis Daily failure ("the filter was chosen on TRAIN and promoted
on a HOLDOUT accept/reject check … m ≫ 1 and no α is justified"). For `nifty_shield_v1`,
sweep_filter is **excluded from the certified identity**. If an entry-quality filter is ever
wanted, it is a *new pre-registration*, never a bolt-on to this identity (which would change
the triple and restart Stage 0 anyway).

### 5.5 DayType runtime classification vs Principle #2

DayType's runtime `on_bar` classification is in tension with Principle #2 ("indicators
pre-computed offline; runtime is read-only"). The repo's convention-respecting shape is
offline `publish_facts.py` → DuckDB → runtime reads facts (as Carry/TS-Basis do). Whether the
regime read belongs inside the `SignalSource` (permissible — "strike/expiry chosen inside the
source", `signal_source.py:52`) or as a pre-published fact is a Decomposition-Spec question,
flagged here, resolved there. It does not block Stage 0.

---

## 6. The external backtest — filed, not graded

Recorded here for provenance; the full filing with caveat is
`docs/strategies/nifty_shield_v1/external_backtest.md`. Headline (bundle README §3c):
400 trades, 97.5% win rate, Sharpe 9.40, +Rs 26L over 4 walk-forward windows — produced with
**flat IV (VIX/100, no smile), synthetic Black-76 pricing, no gap/slippage modeling**, and
**paper-only** (no live order placement wired). These numbers are **optimistic and
unvalidated by construction**; they are Stage-0 evidence of *intent*, referenced (not
re-run) at the Stage 3→4 decision, and never presented as platform validation (§1.1, §3.2).

---

## 7. Scope of this branch, and sequenced future work

**In scope (this branch, `research/nifty-research-bundle-adoption`, docs only):**
this assessment; Ledger E004; the Stage 0 Strategy Datasheet + risk declaration; the filed
backtest; the Decomposition Spec; the Stage 1 implementer prompt. No strategy code (role
split: Claude writes docs/prompts; DeepSeek V4 implements; Claude reviews).

**Out of scope (future, separate branches):**

| Work | Prerequisite | Note |
|---|---|---|
| DeepSeek builds the decomposed `SignalSource` | Decomposition Spec + Stage 1 prompt approved | Stage 0→1 exit; run conformance suite |
| DayType adoption as offline fact-publisher | its own infra branch | resolve §5.1 (vendor or content-hash) and §5.5 (offline facts) |
| sweep_filter as library | — | never inside `nifty_shield_v1`; §5.4 |
| Stage 2 forward PAPER window | Stage 1 CONFORMANT grant | §5.2, §5.3, §3 all bind here |

---

## 8. Cross-references

- Pipeline: `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` (§1.1, §2, §3.2,
  §4.0–§4.4, §6.1, §7.3, §7.4.3, §8, §9).
- Ledger: `docs/STRATEGY_PROMOTION_LEDGER.md` (E004).
- Contract: `core/runtime/signal_source.py`; `core/runtime/conformance.py`;
  `tests/runtime/test_signal_source_conformance.py`.
- RFA non-applicability basis: `docs/reports/RS_MOM_RFA.md`; `CLAUDE.md` RFA + RS-MOM sections.
- OSC unread window: `docs/reports/OSC_RFA_ABANDON.md`; `CLAUDE.md` OSC section.
- Architecture principles: `CLAUDE.md` (#1 Strategies Stay Dumb, #2 Analytics Produce Facts,
  #3 Execution Owns Reality); ADR-002, ADR-016, ADR-021.
- Source bundle: `F:\nifty_research_bundle\README.md`.
