# MSI Grounding Brief — Platform Constraints for the MSI Architecture Author

**Purpose:** Paste this into ChatGPT as binding context before it drafts or revises any MSI (Market State Intelligence) document. ChatGPT has no repository access; this brief supplies the platform's real principles, current state, and existing governance so MSI specifications conform instead of contradicting them.

**Authoritative sources (do not override):** `docs/PLATFORM_CONSTITUTION.md`, `docs/ARCHITECTURE_DECISIONS.md`, `docs/PROJECT_STATE.md`, `docs/DRIVER_SPECIFICATION.md`. Where this brief and an MSI doc disagree, these files win.

---

## 1. What the platform is — and is not

`F:\Nifty` is a **deterministic execution, risk, ledger, and operations platform for Indian derivatives** (equity futures + NIFTY/BANKNIFTY option selling). Two statements from the Constitution govern everything MSI proposes:

- **"The platform is not responsible for generating alpha."** (Constitution §1)
- **"The platform must remain strategy-agnostic"** and **"must remain usable even when no strategies exist."** (§1, §5)

MSI's stated vision — *"the canonical knowledge layer... every strategy reasons about markets through MSI"* — must be reconciled with this, explicitly and up front. "Knowledge, not alpha" is an acceptable answer, but it must be stated and defended, not assumed.

## 2. The five binding principles (MSI must not contradict any)

1. **Ledger is Truth** — authority chain: Exchange → Broker → Execution → Ledger → Risk → Dashboard. Nothing overrides ledger truth.
2. **Execution Before Alpha** — execution correctness outranks indicators, models, predictions, research outputs.
3. **Deterministic Operation** — single execution path, deterministic event processing, auditable state transitions. **"Hidden side effects are prohibited."**
4. **Risk Before Trading** — no trade without defined size, risk, stop, margin validation, clearance.
5. **No Trading On Stale Data** — feed freshness is mandatory.

## 3. The repository trichotomy — the question every MSI doc must answer first

Constitution §10 requires every module to answer: **is this Platform, Strategy, or Research?** This is the decisive constraint for MSI, because §4 lists what the platform repository **shall NOT contain**:

- **Machine Learning** — model training, feature engineering, label generation, training pipelines
- **Strategy Research** — signal discovery, alpha research, **"market regime research"**
- **Backtesting** — backtest engines, walk-forward frameworks, research simulations
- **Research** — notebooks, experimental studies, parameter sweeps

> These belong **outside** the platform repository.

**Direct consequence for MSI:** an MSI subsystem that *trains models*, *engineers features*, or does *market-regime research* cannot live in the platform repo as written. MSI-008 ("Daily Regime Analyzer") is by name "market regime" work. MS001 must therefore declare, explicitly:
- which parts of MSI are **offline research/training** (live outside the platform repo), and
- which parts are a thin, **read-only, deterministic runtime consumer** of already-computed facts (may live in the platform).

Do not paper over this with the phrase "implementation-independent." The boundary is a repository-placement decision, not a philosophical one.

## 4. Current true state (as of 2026-07-03)

- **Greenfield strategy layer.** `core/strategies/` **does not exist**; there is **no production `SignalSource`**, no alpha, no strategy.
- **No `DayTypeEngine`, no regime classifier, no `market_state` code exists in this repo.** (CLAUDE.md documents a `DayTypeEngine` and FTMO system — that documentation is **stale**; the code is not present. Do not treat it as prior art or as an existing MSI implementation.)
- `core/analytics/` contains only `options_analytics.py`, `diagnostic_engine.py`, `resampler.py`.
- Platform Infrastructure is certified **v1.0 complete** (deterministic `LoopDriver`, execution/OMS, SPAN + `NseMarginEngine` + ELM risk, canonical instruments, SQLite-truth + DuckDB audit, telemetry, Paper/Upstox brokers). LIVE trading and broker reconciliation are gated/deferred.

MSI is therefore **net-new**: it must justify its existence against a platform that today deliberately contains no alpha and no strategy.

## 5. Governance already exists — reuse it, do not reinvent it

The platform runs a working **ADR process** in `docs/ARCHITECTURE_DECISIONS.md` (**ADR-001 … ADR-022**), plus a formal **strategy-promotion governance model** (ADR-021/022, `docs/STRATEGY_PROMOTION_LEDGER.md`, evidence-gated and revocable).

- MSI change-control must be expressed as **ADRs in the existing file**, not as a parallel "Chief Research Architect / Architecture Review Board / freeze lifecycle." Map MSI's lifecycle onto the existing ADR + PROJECT_STATE mechanism.
- Relevant existing ADRs MSI must respect: **ADR-002** (Platform/Strategy separation), **ADR-003** (deterministic event processing), **ADR-006** (LoopDriver is the sole runtime orchestrator), **ADR-016** (`SignalSource` is the strategy interface), **ADR-018** (platform-owned boundary guard). Strategies enter the platform **only** through the `SignalSource` interface — MSI outputs a strategy consumes must reach a strategy that way, not through a new privileged runtime channel.

## 6. Runtime boundary (determinism)

`docs/DRIVER_SPECIFICATION.md` + the CLAUDE.md architecture principles fix the runtime contract MSI must honor:

- **Analytics Produce Facts** — indicators/facts are **pre-computed offline; runtime is read-only.** If MSI does inference *at runtime*, it must prove it introduces no hidden state, no wall-clock nondeterminism, and no side effects (Principle 3). The default expectation is: **MSI facts are computed offline and consumed read-only at runtime.**
- **Runner is Neutral** — live and backtest data are processed identically; MSI must produce identical output on identical input regardless of mode.
- **Causality / point-in-time correctness is mandatory** — inference at time *T* may use only information available at *T*. (The platform is strict about this: causal swing detection, warmup windows, no centered/look-ahead computation.) MS001 currently has **no** first principle covering look-ahead; it needs one — this is the top scientific-validity risk for any market-state system.
- **Out-of-sample validation is mandatory** — "in-sample results are meaningless." Any MSI claim of "scientific defensibility" must commit, at the principle level, to out-of-sample / walk-forward validation, not defer 100% of it to a later document.

## 7. Style / house rules

- **No over-engineering; no speculative abstractions ahead of a concrete need; no backwards-compat shims.** MS001-series drafts are heavy on restated slogans (e.g. "architecture independent of implementation" appears 6+ times) — compress.
- Documents live under `docs/architecture/market_state_intelligence/`; reports/reviews under `docs/reports/`.
- Prefer plain paragraphs and lists over one-sentence-per-line prose.

---

## 8. Settled decisions — MS001–008 must remain consistent with these

The MSI README (`docs/architecture/market_state_intelligence/README.md`) has been revised and now settles four points. These are **binding**: every downstream MSI document (MS001 through MS008) must conform to them and must not re-open or contradict them.

1. **Strategy is the sole signal producer; Runtime MSI is a read-side dependency of the strategy.** The flow is `Published MSI Artifact → Runtime MSI → Strategy (read-only MSI consumer) → SignalSource → Platform Infrastructure → Execution`. Runtime MSI **never** generates trading signals and is **not** in the signal-production chain — the strategy remains the sole producer of `SignalEvent`s through the existing `SignalSource` interface (ADR-016). Any diagram or prose that places Runtime MSI directly ahead of `SignalSource` (omitting the Strategy) is wrong.

2. **The Published MSI Artifact is the controlled Research→Platform boundary object, and it must be provenance-pinned.** Only Published MSI Artifacts may cross from the research repo into the platform. Each artifact must be uniquely identifiable, versioned, reproducible, scientifically validated, traceable to its originating research, and governance-approved. **Runtime replay must identify the exact MSI Artifact version used to produce every market-state output** — this is what makes auditability and deterministic replay real. The formal artifact format/schema is deferred to a later MSI doc (MS004/005/008) but the versioning + provenance-pinning requirement is fixed now.

3. **Runtime MSI evaluates only deterministic, point-in-time platform facts — no online derivation.** Runtime MSI performs no online feature engineering, no online training, no parameter optimisation, no historical reinterpretation, no adaptive learning. It consumes only already-computed point-in-time platform facts (keeps it inside "Analytics Produce Facts — runtime read-only"). Determinism contract: identical **platform facts + artifact version + runtime configuration ⟶ identical output**.

4. **Runtime MSI is sequencing-gated to the first production strategy (MM13).** It is a net-new *platform* surface with zero consumers today (`core/strategies/` is empty). Per the constitution ("keep platform code small," "usable even when no strategies exist") and CLAUDE.md ("no abstractions ahead of concrete need"), Runtime MSI stays specification-only until the first production strategy demonstrates a concrete requirement for it. Do not spec implementation surface that presumes an earlier start.

**Consistency obligation.** The README currently out-specifies its own governing philosophy doc: it states no-look-ahead causality, out-of-sample/scientific validation, and the determinism contract cleanly, while **MS001 still lacks explicit first principles for point-in-time/no-look-ahead and out-of-sample validation** and remains redundant. When revising MS001, bring it up to the README's bar — earlier/governing docs must not be weaker than the overview they govern.

---

## What ChatGPT should produce given this brief

A revised MS001 that, at minimum:
1. States MSI's relationship to "the platform is not responsible for alpha / strategy-agnostic" — is MSI Platform, Strategy, or Research, per §10?
2. Splits MSI explicitly into **offline (research/ML/training — outside the platform repo)** vs. **runtime (read-only, deterministic — potentially inside)**.
3. Adds first principles for **point-in-time / no-look-ahead causality** and **mandatory out-of-sample validation**.
4. Routes governance and change-control through the **existing ADR process**, not a new board.
5. Does not reference `DayTypeEngine` or any code as existing prior art — the strategy/regime layer is greenfield.
