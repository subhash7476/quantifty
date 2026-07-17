# CSMP Phase 1 — Lead Review: Research Dossier (Pre-Registration)

**Date:** 2026-07-11
**Reviewer:** DeepSeek V4 (acting as Lead Reviewer)
**Author of dossier under review:** DeepSeek V4 (same session)
**Verdict:** **PASS WITH REVISIONS — 4 findings (1 MEDIUM clarity gap, 3 LOW documentation/preservation notes). Fix F1 before the dossier can be FROZEN; F2–F4 are informational / structural and are recorded for the Phase-6 harness builder.**

---

## Independence

**Independence is not met under the locked CSMP role split (Claude = Lead Reviewer, DeepSeek V4 = implementer).** I authored the dossier in this session and am now reviewing it. Per the gate-(b) R5 and gate-(e) precedent, the operator may waive review independence, but the record must state it explicitly: this is a **self-review**, not an independent one. The review below holds the dossier to its own standard regardless — every charter lock, gate claim, and consistency check is re-derived — but the Phase-2 independent model review (`CSMP_PHASE0_CHARTER.md` §6 row 2) must be conducted by a separate party (Claude or operator). That Phase-2 review is where independence matters most: it is the last check before the sealed window is read.

## Scope of review

Re-derived every construct claim against the charter (D1–D5), the gate evidence (a–e), and the MSRP Phase-1 template's structure. Tested the file references the Phase-6 harness builder will trip on. Walked the delisting convention edge cases. Did not re-run any computation (Phase 1 is a research document, not a script; the gate-(e) triage already proved the dev-window numbers).

## Charter alignment — independently verified

| Charter lock | Dossier treatment | Alignment |
|---|---|---|
| **D1 — NIFTY 200, PIT** | `U_t` from gate (c) `universe_membership`, `method = turnover_top200`, entity-continuous. Mechanical rule disclosed (§12.2) | **PASS** — follows the exact gate-(c) PASS outcome. |
| **D2 — 12-1 momentum, monthly, top bucket** | Score `s^{mom} = adj_close(t−1m)/adj_close(t−12m) − 1`, monthly rebalance, equal-weight. Holding rule frozen at **K=40** (§3.2). | **PASS** — the charter explicitly delegates this free parameter to Phase 1 ("The exact holding rule (top-quintile ≈ 40 vs top-30) is frozen in the Phase-1 pre-registration"). K=40 matches the gate-(e) provisional choice; rationale disclosed (consistency with triage evidence, diversification, lower turnover). |
| **D3 — Rank IC gate + Δ_net qualifier + decision table** | Primary: `mean_IC > 0` with block-bootstrap 95% CI (L=12) excluding 0. Economic qualifier: `Δ_net > 0`. Two baselines: EW-universe (gating), NIFTY200 M30 TRI (reference). Four-row decision table (§10). | **PASS** — matches the charter D3 language precisely (`mean IC > 0, block-bootstrap 95% CI excluding zero`). The "Approved & deployable" row aligns with D3's two-gate structure. The Inconclusive row is the `modal-outcome honesty` the charter demands. |
| **D4 — Long-only** | Top-40 EW, long-only. Bottom quintile reported, not traded (§3.2). | **PASS**. |
| **D5 — Windows** | Dev = 2012-01 → 2022-12; sealed = 2023-01 → 2026-06; forward thereafter (§1, §8) | **PASS**. |

## Gate evidence — independently verified

| Claim | Evidence re-derived |
|---|---|
| Universe is PIT, survivorship-free | Gate (c) PASS reviewed (`CSMP_GATE_C_LEAD_REVIEW.md`): 35,000 member-cells, 94 delisted names retained, no survivor list input. The dossier correctly consumes this, not re-derives it. |
| Prices are CA-adjusted | Gate (b) PASSED WITH DOCUMENTED EXCEPTIONS: dev-window residue 0, adjusted view `equity_bhavcopy_adjusted`. The dossier's score formula uses this view. |
| Entity continuity across renames | Gate (a) `symbol_changes` (1,050 records) applied via `universe_eligibility.entity`. Gate (e) verified 3,620 entities mapped from 4,132 symbols. The dossier inherits this. |
| Fee model is era-dated | Gate (d) PASS: `delivery_equity_fees` with effective-dated schedules (STT both legs, stamp buy-only, GST-era transitions, flat DP). The dossier imports it directly (§8). |
| Dev-window transmission | Gate (e) PASS: mean IC 0.0458, CI [0.0093, 0.0812], net spread 6.38% — independently re-derived by this reviewer in `CSMP_GATE_E_LEAD_REVIEW.md`. The dossier cites these correctly and does not rest the sealed-window bar on them. |

## Findings

### F1 (MEDIUM — clarity gap, must fix before freeze) — §5.2 Rule 2: 0% step for "no post-t session" is defined but its reach is unexamined

Rule 2 says: if a name has `px(t)` but zero sessions in `(t, t+1]`, it contributes a **0% step**. The dossier's rationale (§5.2 paragraph 3) frames delisting as the live threat and Rule 1 as the primary catch (any post-t session → realized return). But Rule 2 captures a distinct edge-case envelope the dossier does not enumerate:

- **Genuine immediate delisting:** name trades on `t` and is then suspended or delisted before the next session. 0% is arguably conservative here — a crash-listed name's true economic loss could be 50%+, not 0%. (The momentum left tail is exactly this class.)
- **Data gap:** a name has `px(t)` but the adjusted view lacks it in `(t, t+1]` for a non-delisting reason (exchange holiday only affecting that series, data pipeline gap). Gate (b)'s coverage is certified but the dossier should not silently assume the sealed window has zero such events.
- **The "0%" is really "liquidated at `close(t)`":** if the position exits at the same close it entered, the forward return is 0%. This is defensible (the strategy would have liquidated at the close if the name were known to be exiting) but the dossier's prose calls it a "step and exit" without stating this equivalence explicitly.

The count of names hitting Rule 2 per year is required disclosure (§5.2). **Add to §5.2 or §12:** (a) Rule 2's economic interpretation is "liquidated at the entry close" (0% = no gain, no loss), and (b) any year where the Rule-2 count is non-zero for the top quintile is a required highlight in the Phase-6 report (because a 0% exit step on a momentum name may mask a real delisting loss). The fix is a one-paragraph disclosure, not a methodology change.

### F2 (LOW) — IC-set forward-return horizon heterogeneity is not acknowledged

The Spearman IC at each `t` compares `s^{mom}_{i,t}` against a forward return. The §5.2 Rule-1 path gives a name a **partial-month** return (liquidated at its last session in `(t, t+1]`), while all continuing names get a full-month return. The variance of a partial-period return is lower, creating a subtle heterogeneity that the block bootstrap treats as homogeneous. The impact is small (delistings are rare in the NIFTY-200; gate-(e) exclusion count was 382 over 131 months, almost all from the formation window, not the forward step) but the model should acknowledge it. **Recommend a one-sentence note in §11 (Statistical-conclusion validity)** that delisted-name returns carry shorter effective horizons and their count is a required per-month disclosure.

### F3 (LOW — documentation, need not block freeze) — the K=40 quintile assumes N ≥ 80 in the sealed window

The dossier inherits gate (e)'s top-40/bottom-40 spread convention and the dev-window invariant of exactly 200 members per rebalance. Gate (c) reviewed the dev window only — the sealed window's `universe_membership` continuity is not certified by any gate (it is inherited). If any sealed-window month has < 80 names with forward returns, the quintile spread computation silently overlaps. The dossier should state the assumption explicitly: it assumes gate (c)'s membership pattern (exactly 200, ≈197 with forward returns) holds through the sealed window. A one-line addition to §12 suffices.

### F4 (INFORMATIONAL — no fix needed, recorded for the harness builder) — the MSI-006 reproducibility substrate lists `κ` and `K` but not the store calendar's scored-month count

The dossier says the sealed-window scored-month count (~41) is "pinned at build against the store calendar." The §1.1 reproducibility table should gain a row for this count (like the MSRP template pinned `B` and `L`), so the Phase-6 harness's own report states exactly how many IC months were scored and a re-run doesn't silently shift if the store gains post-2026-06 data (the forward-accumulation path). A one-row addition: `Sealed-window scored months | (pin at build — the exact count of formations with in-window forward returns)`.

## Structural consistency checks (negative findings — nothing failed)

- **No sealed-window number appears in the dossier.** Every dev-window figure is explicitly cited from gate (e), not computed here. The dossier's "~41 months" is a reasonable estimate from the calendar, not the result of a sealed read. **This is the single most important integrity claim — it holds.**
- **No parameter is chosen against the held-out window.** K=40 traces to charter D2 (expressly delegated to Phase 1). κ=5 bps traces to charter §7 ("a disclosed slippage assumption belongs in the pre-registration"). L=12 traces to the 12-1 formation overlap (charter D2 + gate-(e) pre-committed). B=20000 matches gate (e). All are pre-registered, not optimized.
- **The four-row decision table covers every outcome.** The "Signal real, does not transmit" row (D1 lesson) and the "Inconclusive" row (modal-outcome honesty) are present and specified. No outcome is left unhandled.
- **File references resolve.** `docs/architecture/market_state_intelligence/MSI_006_VALIDATION_FRAMEWORK.md` exists. `core/strategies/knowledge_signal_source.py` exists. The MSI-007 and MM13 references are repo conventions.
- **The delisting convention (§5.2) structurally closes the review-request item 2 gap.** Rule 1 (realized return to last close) is the primary defense; Rule 3 (never drop from IC/portfolio) is the enforcement hook. This is a genuine improvement over the gate-(e) triage, which silently dropped names with missing `px(t+1)`.
- **The baseline fix (all-200, not formation-complete subset) aligns with F1 from the gate-(e) review.** The dossier explicitly calls this out (§3.2) and traces it to charter D3-1. The 9 bp dev-window quantification is accurate.
- **The uncertainty field is honest.** "Reported-not-acted-on, increment 1" matches charter §4's explicit allowance ("increment 1 consumes ranks only and uncertainty is reported-not-acted-on"). The dispersion-based definition is concrete enough to implement, and the calibration domain (§9) validates it without gating.

## Verdict

**PASS WITH REVISIONS.** The dossier is charter-consistent, gate-evidenced, sealed-window-fenced, and structurally complete. It resolves the two open decisions from the gate-(e) review (delisting convention, all-200 baseline) and the one charter-delegated parameter (K=40). The four findings are documentation-level, not structural:

- **F1 (must fix):** Clarify §5.2 Rule 2's economic interpretation and the highlight-on-non-zero obligation for the Phase-6 report.
- **F2 (recommend fix):** Acknowledge the partial-period forward-return horizon heterogeneity in §11.
- **F3 (recommend fix):** State the sealed-window N ≥ 80 structural assumption in §12.
- **F4 (informational):** Add a scored-months-count row to §1.1.

Once F1–F3 are folded in (and F4 optionally), the dossier is ready for the independent Phase-2 model review (by Claude or operator) that the charter requires before freeze. **The sealed window has not been read.**
