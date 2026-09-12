# Research Exposure & Budget Register

**Status:** v2 · **Opened:** 2026-09-12 · **Last appended:** 2026-09-12 (P0.2–P0.4 complete) · **Authority:** operator ruling
PTMS-ALIGNMENT-2026-09-12 §1.
**Purpose:** a durable, versioned, citable record of which *data surface* has been read,
over which *window*, at which *exposure level*, by which *hypothesis family* — so that no
future project has to re-litigate whether a window was previously read.

**This register authorizes nothing.** It records reads. It does not grant or withhold
permission to read; that is the operator's call, informed by what is recorded here.

---

## 1. The key — three dimensions, never collapsed

Per the operator ruling, exposure is tracked as **data surface × exposure level ×
hypothesis family**, with the window recorded on every row. Feature-level exposure is
**recorded but not equated** to signal-level exposure.

### Exposure levels (ordered, least to most spending)

| Level | Definition | Spends budget? |
|---|---|---|
| **meta** | Schema, row counts, distinct-symbol counts, min/max dates, file presence. Computes no signal and no label | **No** |
| **display** | Operator-driven chart/table rendering; no computation retained | **No** |
| **ingest** | Write path (download, parse, insert, mark, backfill) | **No** |
| **feature** | Structural transforms of OHLC computed and retained (returns, TWAP, vol, ranges), **not** linked to a forward outcome | **Recorded, does not by itself spend** |
| **estimation** | Parameters fitted against an outcome variable, then frozen — but the outcome is not a directional trading claim (e.g. forward realized volatility) | **Yes, partially — operator adjudicates per successor** |
| **signal** | A signal is linked to a forward outcome, or a trading rule is evaluated, on that window | **Yes** |

### Window-scoping rule

A read spends **only the dates it touched**. A signal-level read of 2023→2026 does not
spend 2012→2022 on the same surface. Every row names its window explicitly.

### Lineage-local vs global

A construct's own "SEALED / untouched" designation is valid **within its own experiment
lineage only**. It does not make the underlying observations globally unread for successor
research (operator ruling §1). Successors read **this register**, not a predecessor's
closure record.

---

## 2. Enumeration method — and its proven weakness

**Method.** (a) Component-wise grep over `scripts/`, `core/`, `flask_app/`, `app_facade/`,
`governance/` for the store's directory components *and* the module-level constants that
wrap them; (b) transitive grep for importers of those constants; (c) an artifact-side
closure check — every output artifact under `data/` and `docs/reports/` implies a reader,
so an artifact whose producer is absent from this register proves the enumeration
incomplete.

**Why (a) is stated so specifically — a demonstrated failure.** On 2026-09-12 the naive
path-literal search returned **9** readers of the 1m store:

```
grep -rl "candles/1m" --include=*.py scripts core flask_app app_facade governance   ->  9 files
```

The component-wise search returned **63**:

```
grep -rln '"candles"|candles/1|candles\\1|CANDLE_DIR|CANDLES_1|_candles_1' ...        -> 63 files
```

The naive search missed `scripts/build_intraday_features.py` — **the single largest
exposure on the index 1m surface** — because the path is assembled from parts
(`ROOT / "data" / "market_data" / "nse" / "candles" / "1m"`). It also missed the second
wrapper constant `CANDLES_1M_DIR` in `core/analytics/realized_vol.py`. A register whose
enumeration can silently miss its own biggest entry is not durable; path-literal grep is
therefore **not an acceptable enumeration method** for this register.

**Stated limits (this register certifies committed readers plus artifact-implied reads —
not exhaustive human activity).**
- **Deleted code cannot be enumerated.** The Nifty/Bank pair research scripts were removed
  at commit `a30f1fe`; its windows are reconstructed from the frozen report + JSON, not code.
- **Untracked operator probes and ad-hoc notebook reads** cannot be enumerated.
- Git history was searched for surviving scripts, not exhaustively for deleted ones.

---

## 3. Register — index 1m surface

**Surface:** `data/market_data/nse/candles/1m/{date}.duckdb`, rows where
`symbol IN ('NSE_INDEX|Nifty 50','NSE_INDEX|Nifty Bank')`. Span 2012-01-02 → present.

| # | Window | Level | Hypothesis family | Consumer | Evidence |
|---|---|---|---|---|---|
| I-1 | 2012-01-04 → 2025-12-31 | **feature** | Regime classification (day-type) | `scripts/build_intraday_features.py` + `core/analytics/day_features.py` | Output CSVs `intraday_features_{10am,11am,13pm}.csv`, 3,402–3,413 rows, built 2026-08-11 |
| I-2 | 2023-01-02 → 2026-07-03 | **feature** | Regime facts → NiftyShield gating | `scripts/daytype/publish_facts.py` | `day_type_facts.duckdb`, 840–845 sessions |
| I-3 | 2023-01 → ~2026-05 (844 sessions) | **signal** | Nifty/Bank ratio mean-reversion | pair research (deleted, `a30f1fe`) | `NIFTY_BANKNIFTY_PAIR_RESEARCH.{md,json}`; 27 parameter combos, all net-negative |
| I-4 | TRAIN 2012-01-01 → 2018-12-31 | **signal** (gated) | A — opening-drive continuation | `scripts/a_index_intraday/run_train.py` | `A_TRAIN_REPORT.md`; TRAIN PASS, +1.27 bp net, n=1,699 |
| I-5 | HOLDOUT 2019-01-01 → 2022-12-31 | **signal** (gated) | A — opening-drive continuation | A holdout runner | `A_HOLDOUT_REPORT.md` / `A_HOLDOUT_CLOSURE.md`; **FAIL**, −0.22 bp, n=988 |
| I-6 | **2023-01-02 → 2025-12-31** | **estimation** | MSRP forward realized volatility | `scripts/msrp/build_forward_vol_artifact.py` | Module docstring declares the frozen dev window; **OLS coefficients frozen on it**; symbols `NSE_INDEX|Nifty 50` + `NSE_INDEX|India VIX`; also reads the 1d store over the same span |
| I-7 | TRAIN 2012-01-01 → 2018-12-31 | **signal** (gated) | Intraday analog path (KNN path-shape → direction) | `scripts/analog_path/` | `INTRADAY_ANALOG_PATH_TRAIN_REPORT.md`, config seal `cd3d5149…` |
| I-8 | HOLDOUT 2019-01-01 → 2022-12-31 | **signal** (gated) | Intraday analog path | `scripts/analog_path/` | `INTRADAY_ANALOG_PATH_HOLDOUT_REPORT.md` (terminal, run once) |
| I-9 | 6 sessions 2023-01-02..06, 2023-01-09 | **ingest** (fixtures) | — | `scripts/nifty_shield/build_conformance_corpus.py` | Frozen test fixtures |
| I-10 | any date, operator-driven | **display** | — | `flask_app/blueprints/data/routes.py` | Chart views only |

### Finding I-α — the A "SEALED untouched" claim, adjudicated

`A_HOLDOUT_CLOSURE.md` designates index 1m 2023-01-01 → present as SEALED and untouched.
Rows **I-2, I-3, I-6** show that window read at feature, **signal**, and **estimation**
level respectively. Per operator ruling §1, A's designation stands **within A's lineage
only**; globally the window is **SPENT at signal level**.

### Finding I-β — OPEN / QUARANTINED (operator decision PTMS-2026-09-12 §2)

`INTRADAY_ANALOG_PATH_PROTOCOL.md` §5 (dated 2026-09-09, TRAIN and HOLDOUT already run,
SEALED pending) discloses three prior reads of its SEALED window — A, the pair-ratio
analysis, and the DayType pipeline. It does **not** disclose **I-6**: MSRP's frozen-OLS
estimation read of `NSE_INDEX|Nifty 50` 1m *and* 1d closes over **2023-01-02 →
2025-12-31**, which lies wholly inside analog path's SEALED window (2023-01-01 → present).

The protocol's claim is level-qualified — "never been read **at construct level**" — and
I-6 is estimation-level against a *volatility* target, not a directional construct. So the
claim is not obviously false. But the disclosure is incomplete as written, and the
operator's ruling makes level a recorded dimension rather than an automatic exemption.
**Operator status: OPEN / QUARANTINED.** MSRP's estimation-level read is *not* ruled harmless, and the analog-path directional experiment is *not* ruled invalid merely because MSRP targeted forward volatility. The analog-path **SEALED decision is BLOCKED** until the exact dependency and possible contamination are formally examined. **No new market-data window may be spent investigating this.** Strengthened 2026-09-12 by row **I-11** — MSRP touched the window a second time (bootstrap block length from dev-window RV autocorrelation, same 2023-01-02 → 2025-12-31 span).

---

## 4. Register — equity breadth 1m surface

**Surface:** same store, rows where `symbol LIKE 'NSE_EQ|%'`. **Span 2023-01-02 →
present** (188 → 196 names; see PTMS C1 — this start date corrects both the operator
charter and `docs/DATA_STORE_MAP.md` §9, which say 2024-10-17).

| # | Window | Level | Hypothesis family | Consumer | Evidence |
|---|---|---|---|---|---|
| E-1 | 2023-01-02 → 2024-11-30 (474 sessions) | **signal** (gated) | ISD F1 — opening-drive continuation, cross-sectional | `scripts/isd/` battery | `ISD_BATTERY_TRAIN_REPORT.md`; TRAIN sign negative → family closed |
| E-2 | 2023-01-02 → 2024-11-30 (474 sessions) | **signal** (gated) | ISD F4 — overnight-gap, cross-sectional | `scripts/isd/` battery | Same; IC −0.0289, NW t −6.09, p 0.0000, **net −3196 bp** |
| E-3 | 2023-01-01 → present | **signal** | MRLC — multi-timeframe resample + scanner | `scripts/mrlc_test/{build_candles,scanner,size_split,report}.py` | `MRLC_TEST_2026-08-30.md`, `MRLC_ARCHIVE_TEST_2026-08-31.md`, `MRLC_CONSTRUCT_ASSESSMENT.md`; `data/mrlc_test/` |
| E-4 | 2023-01-02 → 2026-08-24 (898 sessions) | **meta** | — | `scripts/isd/build_pit_universe.py` | `data/isd/pit_universe.duckdb:pit_membership`, 173,900 rows — membership flags, no OHLC computation |
| E-5 | post-CAS sessions ≥ 2026-08-03 | **ingest** | — | `scripts/cas/{mark_synthetic_bars,backfill_fo_1m,fo_1m_coverage}.py` | Synthetic marking + gap backfill |
| E-6 | current signal dates | **feature** | TS Basis Daily spot pricing | `scripts/signal_engine/ts_basis_daily/build_ts_basis_daily.py` | Post-CAS continuous-session close (F10 fix, 2026-09-11) |

**ISD reservation:** `ISD_PROGRAM_REASSESSMENT.md` reserves 2026-01-01 → present as ISD's
SEALED. Per §1 that is lineage-local; rows **E-3** and **E-6** touch dates inside it.

---

## 5. Register — other surfaces (lineage rows; reader enumeration is a P0 gap)

| # | Surface | Window | Level | Hypothesis family | Evidence |
|---|---|---|---|---|---|
| D-1 | 1d index store | 2023-01-02 → 2025-12-31 | **estimation** | MSRP forward vol | `scripts/msrp/build_forward_vol_artifact.py` |
| D-2 | 1d index store | 2016 → 2022 / 2020 → 2022 | **signal** (gated) | CB-N50 constituent breadth — TRAIN / HOLDOUT | `CB_N50_{TRAIN,HOLDOUT}_REPORT.md`; TRAIN IC +0.059, HOLDOUT IC +0.029 |
| Q-1 | Equity EOD panel | dev ≤ 2022-12-30 | **signal** (gated) | PSB-1 C1–C5 | `PSB1_C{1..5}_REPORT.md` |
| Q-2 | Equity EOD panel | dev ≤ 2022-12-30 | **signal** (gated) | PSB-2 C2–C4 | `PSB2_C{2,3,4}_REPORT.md`, `PSB2_SELECTION_REPORT.md` |
| Q-3 | Equity EOD panel | TRAIN 2011–2018 | **signal** | C2 Phase 0.4 / 0.5 SD re-estimation + mini-battery | `C2_PHASE0_5_MINIBATTERY.md` |
| Q-4 | Equity EOD panel | 2012–2023 | **feature** | N200 regime HMM | `data/features/n200_regime/`, `N200_REGIME_EVALUATION.md` |
| F-1 | Futures EOD | TRAIN / HOLDOUT / **SEALED** | **signal** (gated) | Carry — all three fences **spent**, SEALED PASS | `CARRY_SEALED_SNAPSHOT.json`, net +20.52% |
| F-2 | Futures EOD | TRAIN / HOLDOUT / **SEALED** | **signal** (gated) | TS Basis monthly — SEALED spent, **de-authorized** on a gate defect | `TS_BASIS_REAUTHORIZATION_ASSESSMENT.md` |
| F-3 | Futures EOD | TRAIN / HOLDOUT / **SEALED** | **signal** (gated) | IVOL — SEALED spent, **FAIL** (sign flip) | `IVOL_SEALED_REPORT.md` |
| F-4 | Futures EOD | TRAIN | **signal** (gated) | Trend, Skew, LAG — all TRAIN FAIL | `{TREND,SKEW,LAG}_TRAIN_REPORT.md` |
| F-5 | Futures EOD | TRAIN 1,202 + HOLDOUT 495 formations | **signal**, multiply selected | TS Basis Daily — both fences burned **as selection surfaces**; sealed 876 formations **preserved unspent** | `TS_BASIS_REAUTHORIZATION_ASSESSMENT.md` §B |
| F-6 | Futures EOD (cash-synthesized) | TRAIN 2012–2018, HOLDOUT 2019–2022 | **signal** | SFB-1 / F1 feasibility screen | `F1_FEASIBILITY_SCREEN_VERDICT_REVIEW.md` |
| O-1 | Stock options EOD | 2023 → 2026 | **signal** | Options seller-edge (late-cycle straddle selling) | `data/scratch/options_seller_edge/`, seller-edge study |
| O-2 | Index options EOD | — | **signal** (gated) | Skew sleeve, MSRP fee triage | `SKEW_TRAIN_REPORT.md`, `scripts/msrp/triage_fee_impact.py` |
| **V-0** | `data/market_data/INDIA VIX_minute.csv` (vendor, gitignored, uncertified) | 2015-01-09 → 2025-03-05, 2,515 of 2,518 calendar sessions | **NONE — unread** | — | no committed reader; no script references the file | Assessed meta-level 2026-09-12; 99.99% value-exact vs canonical over the 8,249-bar overlap. **A genuinely unexposed surface.** Certification-blocked, not budget-blocked — `VIX_1M_VENDOR_CSV_ASSESSMENT_2026-09-12.md` |
| V-1 | `1m_vendor/reliance.duckdb` | 2015-02-02 → 2025-08-06 (2,605 sessions) | **signal** | Reliance regime (single name, vendor store) | `scripts/reliance_regime/`, `data/reliance_regime/` |

---

## 6. Unread / partially-unread surfaces (as of 2026-09-12)

Recorded for planning only. **Nothing here is authorized for reading.**

| Surface | Unread portion | Caveat |
|---|---|---|
| Index 1m, Nifty 50 | **2012 → 2022 is spent** (I-1 feature, I-4/I-5 and I-7/I-8 signal). **2023 → present is spent at signal level** (I-3) | No genuinely unread index-1m window remains at signal level |
| Equity breadth 1m | 2024-12-01 → present is unread by ISD, but touched by E-3 (MRLC, signal) and E-6 | ~3.7 years total, one macro regime; C1 makes a split arithmetically possible |
| `NSE_INDEX|Nifty Bank` 1m | Read at feature level (I-1, Block H intermarket) and signal level on the **ratio** (I-3); no standalone Bank-only directional construct recorded | The ratio read constrains pair constructs, not necessarily Bank-alone ones |
| TS Basis Daily sealed | 876 formations, 2023-01-01 → 2026-07-24 | Deliberately preserved; `run_sealed.py` refuses to run |
| Equity EOD 2023 → present | Largely unread at signal level by the cash-equity batteries (fenced at 2022-12-30) | PSB sealed window never opened; C2 retired pre-read |
| Sector / thematic 1d indices | No signal-level read recorded | Membership is **not PIT-tabled** — a substrate blocker, not a budget one |
| **India VIX 1m (vendor CSV)** | **Entire span 2015-01-09 → 2025-03-05 — zero exposure** | Uncertified and of unstated provenance; blocked on P2 certification, **not** on research budget |

---

## 7. Gap list as opened at v1 (superseded — see §5e for current status)

| Gap | What is missing | Why it matters |
|---|---|---|
| **G-A** | Reader-level enumeration for the **equity EOD** surface (~40 path-literal hits, component-wise count not yet run) | §5 rows Q-* are lineage-level only; a utility reader could constitute an undisclosed feature-level read |
| **G-B** | Same for **futures EOD** (~40 hits) and both **options EOD** stores | As above |
| **G-C** | Same for the **1d index** store | D-1/D-2 are lineage rows only |
| **G-D** | Window determination for intraday readers classified by name but not inspected: `scripts/analog_path/eligibility.py`, `scripts/nifty_shield*/`, `scripts/daytype/build_eod_features.py`, `scripts/msrp/derive_block_length.py`, `scripts/research/options_seller_edge/cas_pcp_forward.py` | Each could carry an unrecorded window |
| **G-E** | Artifact-side closure check run systematically over `data/` and `docs/reports/` | The completeness proof; currently spot-checked only |
| **G-F** | Adjudication of **Finding I-β** (MSRP estimation-level read inside analog path's SEALED window) | Blocks the analog-path SEALED read |


---

## 5b. Register — EOD surfaces, component-wise enumeration (G-A / G-B / G-C, closed 2026-09-12)

**Method.** Component-wise search over `scripts/`, `core/`, `flask_app/`, `app_facade/`,
`governance/`, plus transitive importers of the modules that wrap store paths
(`scripts/isd/__init__.py`, `scripts/psb1/screening_harness.py`, `scripts/psb2/harness.py`,
`scripts/signal_engine/carry/*`, `core/analytics/realized_vol.py`). For the EOD stores the
path is a single filename token, so the literal and component-wise searches coincide — the
divergence that defeats the naive method is specific to the per-date candle stores (§2).

**Reader counts:** equity EOD **84** · futures EOD **86** · index options **13** ·
stock options **10**.

Readers cluster by programme directory; every cluster maps to a recorded lineage. No
orphan reader was found.

| Surface | Cluster | Readers | Level | Family / disposition |
|---|---|---:|---|---|
| Equity EOD | `scripts/signal_engine/` | 19 | signal (gated) | Carry, TS Basis, TS Basis Daily, IVOL, Skew, LAG, Trend — rows F-1…F-5 |
| Equity EOD | `scripts/psb1/` | 16 | signal (gated) + ingest/repair | PSB-1 C1–C5 — row Q-1 |
| Equity EOD | `scripts/csmp/` | 14 | ingest + substrate repair | CSMP substrate build (write path, not exposure) |
| Equity EOD | `scripts/psb2/` | 5 | signal (gated) | PSB-2 C2–C4 — row Q-2 |
| Equity EOD | `scripts/research/` | 5 | signal | pair research, options seller-edge — rows I-3, O-1 |
| Equity EOD | top-level `scripts/*.py` | 5 | mixed | C2 Phase 0.5 (Q-3), download/ingest pipeline, G2 sector ingest, index-history ingest |
| Equity EOD | `scripts/mrlc_test/` | 4 | signal | MRLC — row E-3 |
| Equity EOD | `scripts/sfb/` | 3 | signal | SFB-1 / F1 — row F-6 |
| Equity EOD | `scripts/isd/` | 3 | signal (gated) | ISD — rows E-1/E-2 |
| Equity EOD | `scripts/n200_regime/` | 2 | feature | N200 regime HMM — row Q-4 |
| Equity EOD | `core/msi/` | 2 | **signal (frozen artifact)** | **New — row Q-5 below** |
| Equity EOD | `governance/`, `core/scheduler/`, `app_facade/`, `scripts/{cas,reliance_regime}/` | 5 | declaration / ops / display | Not exposure |
| Futures EOD | `scripts/signal_engine/` | 34 | signal (gated) | Rows F-1…F-5 |
| Futures EOD | top-level `scripts/*.py` | 17 | signal + ops | Carry + TS Basis (daily/monthly) replay, forward runners, concentrated backtests, refresh pipeline |
| Futures EOD | `scripts/sfb/` | 10 | ingest + signal | Futures substrate build; F1 screen (F-6) |
| Futures EOD | `scripts/research/` | 7 | signal | pair research, options seller-edge |
| Futures EOD | `governance/` | 5 | declaration | Frozen RFA declarations — not exposure |
| Futures EOD | `scripts/{cas,isd,csmp,a_index_intraday}/`, `core/*` | 9 | ingest / meta / ops | A cost substrate (`measure_cost_substrate.py`) is **meta** — fee/slippage measurement, no signal |
| Index options EOD | `scripts/{signal_engine,research,msrp,sfb,isd}/` + `core/*` + `app_facade/` | 13 | signal + ingest + live | Skew (O-2), MSRP fee triage, seller-edge, live option selection |
| Stock options EOD | same shape | 10 | signal + ingest + live | Skew, seller-edge, PIT universe build, live selection |

| # | Surface | Window | Level | Hypothesis family | Consumer | Evidence |
|---|---|---|---|---|---|---|
| **Q-5** | Equity EOD (adjusted) | **dev: through 2022-12-30** (dossier §1.1 — every parameter fixed from the charter + dev window; gate (e) and the §2.1 re-run assert and print that nothing past 2022-12-30 was read) | **signal** (frozen artifact) | CSMP 12-1 cross-sectional momentum | `core/msi/artifacts/xs_momentum_v1/model.py` | Frozen `PublishedArtifact` v1; spec `CSMP_PHASE1_RESEARCH_DOSSIER.md` Rev 7 (FROZEN); parameter-free construct. Already disclosed as PSB-2 prior exposure (decision D2) |
| **Q-6** | Equity EOD (adjusted) | **sealed: 2023-01 → 2026-06, 42 formation-months (2022-12-30 → 2026-05-29 grid)** | **UNREAD** | CSMP 12-1 cross-sectional momentum | — | Dossier Rev 7: single-shot Phase-6 read, subject to the §8 VOID precondition; **"the window has not been read."** Recorded so a successor cannot assume it free |

---

## 5c. Register — G-D window determination (closed 2026-09-12)

| # | Consumer | Window | Level | Note |
|---|---|---|---|---|
| I-11 | `scripts/msrp/derive_block_length.py` | **2023-01-02 → 2025-12-31** | **estimation** (second-order) | Pins the moving-block-bootstrap length L from dev-window RV autocorrelation on Nifty-50 1m. Docstring: "never opens a 2026 file." A *second independent* MSRP artifact fitted on the analog-path SEALED span — see Finding I-β for why characterization, not the count, is the issue |
| I-12 | `scripts/analog_path/eligibility.py` | from 2012-01-01 | **meta** | Rule-driven eligible-day build + integrity scan + append-only defect register; no OHLC into features |
| I-13 | `scripts/daytype/build_eod_features.py` | as invoked (defaults not pinned in source) | **feature** | Session features via `core/analytics/day_features.py` — same family as I-1 |
| I-14 | `scripts/nifty_shield/derive_anchoring_params.py` | historical | **feature** | Scale-invariant re-derivation of config constants; docstring: "Nothing here reads a trade, a fill, or an outcome" |
| I-15 | `scripts/nifty_shield/audit_regime_and_structures.py` | 2026-09 PAPER sessions | **feature / operational** | Forward paper window, not a research fence |
| O-3 | `scripts/research/options_seller_edge/cas_pcp_forward.py` | 2026-09-* | **signal** | Put-call-parity implied spot vs frozen `underlying_ltp`; reads `wall_chain_snapshots`, **not** the canonical 1m store |

**Shared-reader note.** `scripts/analog_path/data_layer.py` imports `scripts.isd` — the
analog-path lineage reads the 1m store through ISD's certified reader (`scripts/isd/read_1m.py`).
A substrate defect there is common to both lineages.

---

## 5d. G-E — artifact-side closure check (closed 2026-09-12)

Every research-artifact directory under `data/` and every subdirectory of `docs/reports/`
was mapped to a recorded reader. **Result: closed, with one addition.**

- Mapped with no gap: `a_index_intraday` (I-4/I-5) · `analog_path` (I-7/I-8/I-12) ·
  `audit` (Q-2/Q-3) · `cas` (E-5) · `features/day_type` (I-1/I-2) ·
  `features/n200_regime` (Q-4) · `isd` (E-1/E-2/E-4) · `mrlc_test` (E-3) ·
  `mto_probe` (CSMP ingest) · `nifty_shield*` (I-15, PAPER) · `ops` · `options` (live) ·
  `psb{1,2}_synthetic` (fixtures) · `reliance_regime` (V-1) · `se3` (O-1) ·
  `signal_engine` (F-1…F-5).
- **Addition found:** `docs/reports/substrate_csmp/` + `core/msi/artifacts/xs_momentum_v1/`
  → **row Q-5**. `core/msi/artifacts/forward_vol_v2/` → the MSRP family (I-6, I-11, D-1).
- The check earned its keep: Q-5 was reachable from the artifact side and was **not**
  surfaced by the v1 lineage sweep.

---

## 5e. Gap status after P0.2–P0.4

| Gap | Status |
|---|---|
| G-A equity EOD enumeration | **CLOSED** (§5b) |
| G-B futures + both options stores | **CLOSED** (§5b) |
| G-C 1d index store | **CLOSED** — readers are the MSRP dev-window build (D-1), CB-N50 (D-2), `ingest_index_history.py` (ingest), `g1_r2_final_verification.py` (meta), pair research (I-3), `app_facade/data_facade.py` (display) |
| G-D intraday reader windows | **CLOSED** (§5c) |
| G-E artifact-side closure | **CLOSED** (§5d) |
| **G-F adjudication of I-β** | **OPEN / QUARANTINED** — operator decision PTMS-2026-09-12 §2. The analog-path SEALED decision is **BLOCKED**. Strengthened by I-11: MSRP touched that window **twice** (frozen OLS coefficients *and* the bootstrap block length), both estimation-level on a volatility target. Not adjudicated here; no new window may be spent investigating it |

---

## 8. Maintenance rule

- Append a row **before** a read, not after. A read not recorded here did not happen for
  register purposes — and a project that fails to record one cannot later claim the window
  was fresh.
- Every new RFA declaration must carry a prior-exposure section citing the rows it inherits,
  and `n_available` must be justified against this register.
- Rows are append-only. Corrections are new rows that cite and supersede the old, never edits.
- A construct's own closure record is **not** a register update.
