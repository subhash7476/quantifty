# Strategy Datasheet — `nifty_shield_v1`

**Template version:** 1.0 (MM12.5)
**Created at:** Stage 0 — **FROZEN at the Stage 1 CONFORMANT grant (Ledger E005, 2026-08-08)** (any later change = new identity, §2)
**Date:** 2026-08-07 · **Frozen:** 2026-08-08
**Ledger:** E004 (identity reservation), E005 (CONFORMANT grant) · **Spec of record:** `docs/reports/NIFTY_SHIELD_ADOPTION_ASSESSMENT.md`
**Source design:** `F:\nifty_research_bundle\nifty_shield\` (retired `D:\BOT\root` platform)

> The certified artifact is the **re-expressed dumb `SignalSource`** built per
> `NIFTY_SHIELD_DECOMPOSITION_SPEC.md` — the bundled code does not pass Stage 1 as-copied
> (assessment §4). The §3 dict is **frozen** as the certified config: `config_hash`
> `c5b722ff…536c` reproduces exactly from `strategies/nifty_shield_v1/config.py`. Fields
> marked *[pins @ Stage 3]* remain deferred to the Stage 3 capital plan; all Stage-1 pins are
> now final.

---

## 1. Identity

| Field | Value |
|---|---|
| `strategy_id` | `nifty_shield_v1` |
| `code_ref` | **`ebfb7ec`** — commit of the decomposed strategy package (`strategies/nifty_shield_v1/`); merged to `main` via `5594470` |
| `config_hash` | **`c5b722ff204d4e434f5cbffb1674136738a79693a3ced17bf07e46676d5336c6`** — SHA-256 of the certified `build_signal_source(config)` dict (the datasheet §3 dict, excluding the `facts_db_path` runtime seam); **reproduces from `config.py`** |
| `STRATEGY_CONTRACT_VERSION` | `1.0` |
| Package/repository | `strategies/nifty_shield_v1/` (external package; `build_signal_source` factory) |
| Factory export | `build_signal_source(config)` |

**1a. DayType model identity (§5.1 of the assessment — blocks freeze).** The strategy consumes
a DayType 13pm regime model (`model.pkl` + `scaler.pkl` + `metadata.json`) at a path *outside*
the identity triple. A silent retrain would change signals while the triple held fixed —
voiding §2 and §7.2. **Resolution (Decomposition Spec D2 — recommended; **ratified by operator
2026-08-07**): the regime is read as a **versioned, content-hashed fact** produced by an
offline/live DayType facts publisher — the model is **not** in the strategy identity; determinism
becomes a facts-*provenance* obligation (the fact's `regime_fact_version` + hash are recorded for
Stage-1 replay). This supersedes the earlier "vendor the model" idea because the source receives
only the underlying bar, not the Bank-Nifty feed the model needs. Datasheet cannot freeze until
D2 is ratified and the regime-fact provenance is fixed. `sweep_filter` is **excluded** from this
identity (§5.4).

## 2. Config schema

| Parameter | Type | Default | Description |
|---|---|---|---|
| `underlying` | `str` | `NSE_INDEX\|Nifty 50` | Traded underlying |
| `entry_checkpoint` | `str` | `13pm` | DayType checkpoint that triggers entry |
| `exit_time` | `{h,m}` | 15:15 | Hard same-session exit |
| `profit_target_pct` | `float` | 0.50 | Capture fraction of credit received |
| `stop_loss_multiplier` | `float` | 2.0 | Stop at credit × this multiple |
| `delta_adjustment_threshold` | `float` | 0.55 | **Unused in v1 (D1):** dynamic hedging is dropped; delta is a flatten-gate, not a hedge trigger |
| `max_portfolio_delta` | `float` | 500 | Portfolio delta cap |
| `max_lots` | `int` | 2 | Base lot count before regime/VIX scaling |
| `lot_size` | `int` | 75 | Nifty contract lot |
| `regime_sizing` | `dict` | Choppy 1.0 / Bull 0.5 / Bear 0.5 | Regime lot multiplier |
| `vix_skip_above` | `float` | 20.0 | Skip session entirely above this VIX |
| `vix_reduce_above` | `float` | 16.0 | Shave one lot above this VIX (non-strangle) |
| `iron_fly_vix_above` | `float` | 14.0 | Choppy VIX 14–16 → iron fly |
| `wing_offset_pts` | `int` | 100 | Iron-fly wing offset |
| `directional_wing_pts` | `int` | 150 | Bull-put / bear-call wing offset |
| `strangle_otm_pts` | `int` | 50 | Strangle OTM offset |
| `expiry_days_min` | `int` | 2 | Min DTE for the chosen weekly expiry |
| `strike_step` | `int` | 50 | Strike grid step |
| `risk_free_rate` | `float` | 0.065 | Black-76 rate |
| `iv_default` | `float` | 0.14 | Fallback IV — **decomposition must price on real marks, not this flat default** (§8) |
| `cost_per_lot_rs` | `int` | 90 | Strategy cost hint; **the platform fee model is authoritative** |

## 3. Certified config values

Proposed certified dict (freezes at Stage 1; `config_hash` computed over the frozen form):

```json
{
  "underlying": "NSE_INDEX|Nifty 50",
  "entry_checkpoint": "13pm",
  "exit_time": {"hour": 15, "minute": 15},
  "profit_target_pct": 0.50,
  "stop_loss_multiplier": 2.0,
  "delta_adjustment_threshold": 0.55,
  "max_portfolio_delta": 500,
  "max_lots": 2,
  "lot_size": 75,
  "regime_sizing": {"Choppy": 1.0, "BullTrend": 0.5, "BearTrend": 0.5},
  "vix_skip_above": 20.0,
  "vix_reduce_above": 16.0,
  "iron_fly_vix_above": 14.0,
  "wing_offset_pts": 100,
  "directional_wing_pts": 150,
  "strangle_otm_pts": 50,
  "expiry_days_min": 2,
  "strike_step": 50,
  "risk_free_rate": 0.065,
  "iv_default": 0.14,
  "undefined_risk_stress_pts": 200
}
```

**Frozen disposition (Stage 1, locked by the pinned `config_hash`).** The three questions the
draft left open are settled by the hash the grantor pinned — changing any of them mints a new
identity (§2):

- `iv_default` (0.14) — **retained, declared-but-inert.** The source never prices; execution
  prices on real marks. Kept in the certified dict for continuity but not read by
  `build_signal_source`.
- `cost_per_lot_rs` — **dropped** from the certified dict (it is not in `DEFAULT_CONFIG`). The
  platform fee model is authoritative (`core/execution/options/fees.py`).
- `undefined_risk_stress_pts` (200) — **retained** in the certified dict; it feeds the per-leg
  `sl_distance`/`risk_r` declaration and the §7a max-DD number.

The "minimal-surface" option floated in the draft (drop the inert keys at grant) is **foreclosed**:
dropping keys changes the hash, and the grantor pinned `c5b722ff…536c`. The exit-manager reads
only `profit_target_pct` / `stop_loss_multiplier` / `exit_time` / `max_portfolio_delta`.

## 4. Universe

| Field | Value |
|---|---|
| Symbols | `NSE_INDEX\|Nifty 50` weekly options (CE/PE), nearest weekly expiry ≥ `expiry_days_min` DTE |
| Derivative types | Options (index) |
| Underlyings (F&O) | NIFTY |
| Regime inputs (read-only, not traded) | `NSE_INDEX\|Nifty 50` 1m, `NSE_INDEX\|Nifty Bank` 1m (DayType Block-H), `NSE_INDEX\|India VIX` |

## 5. Session behavior

| Field | Value |
|---|---|
| `on_bar` signals per bar (max) | Up to **4** at the 13:00 entry bar (iron-fly = 4 legs); ≤ 2 otherwise (exit/hedge). **Resolved (D3): one `SignalEvent` per leg**, all legs sharing a deterministic `group_id`. |
| Entry frequency band | **1 structure/session** at 13:00 (0 on VIX-skip days); no stacking (`_has_open_trade_today`) |
| Exit frequency band | 1 structure closed/session (50% capture, 2× stop, or 15:15) |
| Max simultaneous positions | **1 structure** (up to 4 legs) |
| Session bounds | Entry 13:00 IST; hard flat by 15:15 IST — **intraday, no overnight hold**; all trading days |

**5a. Structure selection** (regime × VIX): BullTrend → bull-put (defined); BearTrend →
bear-call (defined); Choppy VIX>16 → strangle (**undefined risk**); Choppy 14<VIX≤16 → iron-fly
(defined); Choppy VIX≤14 → straddle (**undefined risk**); VIX>20 → **skip**. Sizing
`lots = max(1, round(2×regime_mult))` then −1 lot if VIX>16 (non-strangle) → 1–2 lots ×75.

## 6. Latency budget

| Field | Value |
|---|---|
| `on_bar` p99 latency budget | **≤ 50 ms — measured 0.0022 ms** (2,250-bar corpus, single-threaded; fact loaded at `on_start`, `on_bar` is a dict lookup + arithmetic) |

## 7. Risk declaration

| Field | Value |
|---|---|
| Max drawdown (Rs) | **Rs 30,000 worst single day / Rs 150,000 stressed 5-day streak** (computed via §7a stress method — **pinned at E005**) |
| Max drawdown (% of allocated capital) | *[pins @ Stage 3 capital plan]* |
| Per-trade risk (`risk_r` semantics) | **Not fixed-R.** Lot-based (1–2 lots ×75). Loss bounded by structure: defined = `(wing_width − net_credit) × 75 × lots`; undefined = 2× credit stop **+ intraday-spike slippage** (§7a). Declared per leg: `sl_distance` = wing width (defined) / 200-pt stress distance (undefined), `risk_r` = distance × 75 × declared lots |
| `sl_distance` semantics | **Not a price-distance SL.** Exit is a **2× credit-received** stop on the structure, plus a **15:15 hard time-exit** and a **50% capture** target |
| Max margin utilization | **Ceiling pinned at 25% of allocated capital**; margin computed **only** by `NseMarginEngine` (SPAN+ELM; ADR-011/013). Undefined-risk legs must show SPAN+ELM exercised in the PAPER report (§7.7) |
| Allocated capital (Stage 3+) | *[pins @ Stage 3 capital plan]* |

**§7a computed numbers (proposed, script-derived, no backtest input).** Per structure at
declared lots (datasheet §5a sizing: `lots = max(1, round(2 × regime_mult))`, −1 if VIX>16
non-strangle): bull_put/bear_call (1 lot, wing 150) → **Rs 11,250**; iron_fly (2 lots, wing 100)
→ **Rs 15,000**; short_straddle/strangle (2 lots, 200-pt stress) → **Rs 30,000**. The declared
max DD is the larger single worst-structure day (**Rs 30,000**) and a 5-consecutive-day stressed
streak (**Rs 150,000**) — the undefined-risk stress distance is the config
`undefined_risk_stress_pts = 200`, a *proposed freeze value*. Backtest DD is explicitly not an
input.

**7a. Max-DD derivation method (the §5.2 trap, handled).** The declared max DD is **not** read
off the external backtest (flat IV + synthetic pricing + no gaps — §8). It is a **stress view**,
fixed here; the number computes at freeze: (1) **defined-risk** worst case is analytic,
`(wing_width − net_credit) × 75 × lots`; (2) **undefined-risk** worst case is a stressed
intraday 13:00→15:15 Nifty excursion (a stated high percentile, e.g. 99.5th) priced on the short
legs with a stop-slippage allowance — **no overnight gap enters because the book is flat by
15:15**; (3) **portfolio** max DD is the larger of a stressed losing streak (1 structure/session)
and a single worst-structure day, in Rs and %. The backtest DD is explicitly not an input.

## 8. External backtest reference

| Field | Value |
|---|---|
| Backtest period | *[from `external_backtest.md`]* — 4 walk-forward windows |
| Backtest report path | `docs/strategies/nifty_shield_v1/external_backtest.md` (artifact #4, filed not graded) |
| Key metrics (filed, not graded) | 400 trades, 97.5% WR, Sharpe 9.40, +Rs 26L — **flat IV / synthetic pricing / no gaps; optimistic & unvalidated** (§1.1, §3.2). **Never** re-run over the OSC unread window (assessment §3) |

## 9. Risk gate configuration (for validation windows)

| Gate | Setting | Source |
|---|---|---|
| Drawdown limit | **Rs 30,000 single day / Rs 150,000 5-day streak** (§7) | Handler drawdown gate |
| Daily trade limit | **1 structure/session** | Handler daily-limit gate (from §5 entry band) |
| Max positions | **1 structure** | Handler stacking gate (`_has_open_trade_today`) |
| Margin budget | **25% of allocated capital** (§7) | Handler margin gate (`NseMarginEngine`) |
| Greek limits | Portfolio \|Δ\| > **500** → **flatten the structure** (D1: close-only gate, **no dynamic hedge** in v1 — a new hedge would invert ADR-006) | Handler Greek gate (`max_portfolio_delta`) |

---

## 10. Round-trip counting convention (MM12.5 §7.3) — pinned before any window

Stage 2 needs **≥20 sessions AND ≥30 round-trips**. Pinned now (deciding after seeing the count
is prohibited): **(1)** one round-trip = one *structure* opened and fully closed (an iron fly =
**one** RT, not four); **(2)** a within-position delta hedge is management, not a new RT;
**(3)** cadence ≈ 1 RT/session (intraday design), less VIX-skip/regime days → the §7.3 floor is
reached in **~35–45 sessions (~2 months)**, not the ~30 weeks a multi-day holder needs. If 30 RT
are not reached by 60 sessions, the §7.3 escape applies — accept the 60-session window with the
shortfall **ledgered as an accepted deviation, visible forever**.

## 11. Stage 1 freeze checklist

- [x] `code_ref` + `config_hash` pinned to the decomposed package/config. **`ebfb7ec` / `c5b722ff…536c` — hash reproduces from `config.py`.**
- [x] DayType model identity resolved — vendored in `code_ref` (preferred) or content-hashed (§1a). **Resolved: content-hashed fact (D2 ratified); `config_hash` covers the strategy dict, the fact's `model_hash`/`regime_fact_version` are recorded per row.**
- [x] Max-DD **number** computed via §7a and inserted (backtest DD excluded). **Rs 30,000 single day / Rs 150,000 5-day streak.**
- [x] Max margin utilization ceiling set; `NseMarginEngine` SPAN+ELM confirmed exercised. **Ceiling pinned 25%; sizing service wired to the margin engine (D4, unit-tested). Scope note: the §7.7 SPAN+ELM confirmation on undefined-risk legs against *real marks* is a Stage-2 PAPER obligation — this tick covers ceiling-set + engine-wired, not the live-marks demonstration.**
- [x] `on_bar` p99 latency measured at conformance. **Measured 0.0022 ms.**
- [x] `iv_default` + `cost_per_lot_rs` decomposition disposition recorded. **`iv_default` retained-inert; `cost_per_lot_rs` dropped; `undefined_risk_stress_pts` retained — locked by the pinned hash (§3 frozen note).**
- [x] Conformance report attached; datasheet frozen at the CONFORMANT grant. **`docs/reports/NIFTY_SHIELD_STAGE1_CONFORMANCE_REPORT.md`; frozen 2026-08-08 at Ledger E005.**
