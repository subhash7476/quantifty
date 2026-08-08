# NiftyShield E007 — Phase A Review (Claude, empirical)

**Reviewing:** commit `9c56e44` on `main` (E007 Phase A — execution wiring + runner + evidence tooling).
**Reviewer:** Claude (empirical review per prompt §6). **Implementer:** DeepSeek V4. **Grantor of E007:** operator (Phase B evidence required first — Phase A is a harness milestone, **not** a ledger transition).
**Verdict:** **ACCEPT as a Phase-A harness.** The pipeline is correctly wired, the frozen identity is untouched, the smoke reproduces end-to-end, and the E7-4 real-marks seam is genuine. Three findings carried to Phase B (none is a Phase-A blocker); one is cosmetic.

---

## 1. Load-bearing invariants — verified

| Check | Method | Result |
|---|---|---|
| **Frozen strategy package untouched** | `git show --stat 9c56e44 -- strategies/nifty_shield_v1/` | **Empty** — zero edits. Identity preserved. |
| **`config_hash` unchanged** | `config.py` not in the commit's file list | Unchanged by construction (`c5b722ff…536c`). |
| **REPLAY smoke reproduces** | re-ran `scripts/nifty_shield_paper_smoke.py` | **SMOKE PASS** — fact published → structure emitted → handler entered → filled at marks → margin journaled → 15:15 time-exit close → RT=1; guard events 0; reverse divergence none; telemetry clean (`violations=[]`). |
| **New tests green** | `pytest` on the two new suites | **19/19 passed.** (Full-suite 1618-passed is DeepSeek's claim; the load-bearing subset is independently confirmed. Pre-existing `test_g1_closure_guard` red on `main` is unrelated / not strategy-attributable, acceptance #8.) |
| **E7-4 real option marks, no synthetic fallback** | read `nifty_shield_marks.py` + handler pricing | **Confirmed.** Fills price at `marks[signal.symbol]` (real chain LTP), never the underlying close; a missing mark → journaled `ENTRY_SKIPPED` reason "missing option marks (E7-4, no synthetic fallback)". |
| **No P&L as pass/fail** | read `metrics_report.py` | Confirmed — PnL facts recorded "NOT pass/fail (§1.1)". |
| **Gates map to datasheet §9** | read `nifty_shield_gates.py` | Mapped with documented interpretation (see Finding 4). |

---

## 2. Findings (all Phase-B items; none blocks Phase A)

### F1 — [LOW / cosmetic] Base-handler `intended_entry` exit-diagnostic warning fires on every exit
The REPLAY smoke logs, twice: `execution_handler - WARNING - Exit diagnostics failed: no such column: intended_entry`. Traced to **base** `core/execution/handler.py:483` (not touched by Phase A) — a directional-SL diagnostic (`SELECT … intended_entry, sl_distance, risk_r …`) that doesn't fit NiftyShield's schema. **It does not corrupt evidence**: `metrics_report.py` computes from its own journal events (`ENTRY_MARGIN`/`ENTRY_SKIPPED`/`STRUCTURE_CLOSE`) and the trades ledger, not this diagnostics path. **Disposition:** suppress/guard it for the options handler (or confirm inert) so it does not mask a real exit-path error during Phase B's ~40-session logs.

### F2 — [MEDIUM / Phase-B evidence quality] R-based metrics are silently vacuous for NiftyShield
`metrics_report.py` computes `r = pnl / risk_r`, and `risk_r` is journaled as `leg_metadata.get("risk_r", 0.0)`. NiftyShield **declares no price-distance R** (datasheet §7: "Not a price-distance SL"; exit is 2× credit / 50% capture / 15:15). So `risk_r` is 0.0 → `avg_win_r`/`avg_loss_r` collapse to 0.0, and the §7.4.2 "avg win/loss in R" line is meaningless. **Disposition:** before Phase B's risk-metrics report is offered as evidence, either define a risk base for this strategy (credit-received or NseMarginEngine margin-at-risk) and normalize R against it, or drop the R columns and report Rs- / margin-normalized figures. This is a definition to pin **before** seeing the window (same discipline as datasheet §10).

### F3 — [MEDIUM / Phase-B robustness] `ChainSnapshotMarksSource` conflates infra failure with "no data"
Both the `duckdb.connect` failure and the query failure are caught by broad `except Exception` and return `{}` — identical to "market closed / symbol absent". A misconfigured `db_path` or corrupt cache in the live window would therefore make **every** entry journal a "missing option marks" skip with no signal that the cause is a config/infra error, not absent data. This is the repo's own documented pitfall ("a bare except turns 'we failed' into 'the source doesn't have it'"). **Disposition:** distinguish cache-unavailable (loud — raise/alert) from symbol-absent (normal journaled gate outcome) before the live window opens. The hand-back already flags "the chain cache path must exist/populate"; this makes that failure visible instead of silent.

### F4 — [LOW / note] The §9 "1 structure/session" limit is enforced by the source flag + audit, not a hard handler counter
`nifty_shield_gates.py` sets the handler per-fill `max_trades_per_day = 4` (iron-fly leg count) so a leg set is never split; the true 1-structure/session limit rests on the source's `_entered_today` shadow flag and the **post-hoc audit tool**. Honestly documented in the gates docstring and defensible (the handler counts fills, not structures). **Disposition:** the audit's 1-structure/session verification is load-bearing and must actually run **every** Phase-B session, not just at report-assembly.

### F5 — [note] Smoke instrument-resolver fallback
The REPLAY smoke's date (2026-06-05) precedes the instrument snapshots → `lot_size/tick_size` fallback warnings. Fine for a harness smoke; Phase-B live sessions must resolve real instrument attributes (peak-margin-util and sizing depend on the true `lot_size`).

---

## 3. What Phase A correctly does NOT claim
- **Not a validation.** Phase B (≥20 sessions AND ≥30 RT, datasheet §10) is unstarted; E007 is not grantable yet.
- **SPAN+ELM live demo deferred (disclosed).** The smoke had no SPAN snapshot → flat-rate `MarginTracker`, correctly journaled `engine=MarginTracker`. The §7.7 SPAN+ELM-against-real-marks demonstration is a Phase-B session requirement; sessions without a current SPAN snapshot must be flagged (as the hand-back states).
- **Kill-switch drill (E7-5), replay-evidence diff (G), regression attestation** — Phase-B items, correctly listed as not done.

## 4. Recommendation
**Proceed to Phase B.** Address F2 and F3 before the first live evidence session (both change what the evidence *means* or whether a silent failure is visible); F1/F4/F5 are hygiene that can ride alongside. None requires touching the frozen strategy package. Claude re-reviews the completed report after Phase B; the operator grants E007.
