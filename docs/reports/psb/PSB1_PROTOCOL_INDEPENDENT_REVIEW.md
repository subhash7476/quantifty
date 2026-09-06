# PSB-1 Screening Protocol — Independent Review

**Date:** 2026-07-13
**Reviewer:** DeepSeek V4, acting as the independent second-party reviewer (the author of the protocol, Claude, cannot be its only reviewer — the CSMP Phase 2 pattern)
**Artifact reviewed:** `docs/reports/PSB1_PROTOCOL.md` DRAFT Rev 1 (2026-07-13)
**Governing record:** `docs/reports/PSB1_PHASE0_RESEARCH_RECORD.md` (operator decisions D1–D4, LOCKED 2026-07-13)
**Verdict:** **APPROVE WITH MINOR REVISIONS**

The protocol is disciplined, internally consistent, and correctly institutionalizes the CSMP power lesson — §7 runs the power projection that killed CSMP *before* promotion, per candidate. Two findings can bias the ranking/verdict and should be fixed before freeze (F1, F2); three are disclosure/robustness additions that do not require redesign (F3–F5). No finding requires reworking the battery's architecture.

I did not read the sealed window and this review touches no data ≥ 2023-01-01. The verification below reads dev-era schema/coverage only.

---

## Verification performed

Against the live substrate pinned in §2:

| Check | Result |
|---|---|
| `equity_bhavcopy_adjusted` columns | `trade_date, symbol, series, open, high, low, close, prev_close, volume, turnover, deliv_qty, deliv_pct` — `deliv_pct` present as pinned |
| `deliv_pct` non-NULL span | 2020-01-01 → 2026-07-09, 2,954,585 rows — matches §2/§4 (SECFULL era) |
| Store max `trade_date` | 2026-07-09 — the dev fence is **load-critical**, not cosmetic; §10 assert-and-print is correctly mandatory |
| Loader lineage `load_window()` | Exists at `scripts/csmp/run_a2_validation.py:52`; dedups by `turnover DESC, symbol` (`rn=1`); asserts + prints observed `MAX(trade_date)` |

**Prompt-1 caveat (loader):** the inherited `load_window()` selects only `adj_close` — it does **not** carry `deliv_pct`. The Phase-1 harness must extend the SELECT to carry `deliv_pct` through the *same* `rn=1` pick, so the delivery value is the turnover-primary listing's and matches its price. Pin this in Prompt 1.

---

## Substantive findings (address before freeze)

### F1 — The selection statistic is confounded by unequal n (§8)

The winner is chosen by the one-sided **t-statistic of mean IC**, but the candidates carry unequal dev sample sizes: C1/C2/C5 at ~572 weekly / 132 monthly formations vs C3/C4 at ~143 weekly formations. For identical effect size and dispersion the t-statistic scales with √n, so the ranking has a structural thumb on the scale **against the delivery candidates (C3/C4)** — the very constructs the research record (§4) names as the repository's comparative advantage.

Eligibility already forces power ≥ 0.80 on the common sealed n\* (§7), so effect size is separately gated; the residual problem is confined to *ranking among the eligible*. §8's own "unequal dev windows" clause admits the risk is live.

**Recommendation:** rank eligible candidates on a size-invariant footing — either **projected sealed power** (the program's actual objective) or **mean IC on the common 2020-04→2022 sub-window** as the *primary* ranking, with the full-window t-statistic retained as the robustness column. This inverts the current primary/robustness roles for the ranking step only; eligibility and deflation are unchanged.

### F2 — Delisting exclusion directionally inflates the reversal candidates (§4.2)

Dropping scored names that have no price at *t'* (delisting/suspension) removes exactly the delisted losers that a reversal book — C1, and C4's revert leg — would be long, censoring the −100% tail and biasing C1/C4 IC and net spread **upward**. These are also the most fee- and tail-sensitive candidates in the slate, so the bias lands where it does the most damage to an honest read.

§4.2 records the exclusion as a limitation but states neither its *direction* nor its *asymmetry across candidates*.

**Recommendation:** pin a delisting-return convention (e.g., force the delisted name's forward return to the date's worst-quintile value) reported as a mandatory robustness column, so the tail is bounded rather than silently dropped. The bias is then quantified in every reversal candidate's report.

---

## Should-fix (disclosure / robustness — non-gating)

### F3 — Weekly IC t-statistic independence (§6/§7)

Weekly cross-sectional IC series cluster in regimes; positive lag-1 autocorrelation inflates the mean-IC t-statistic and therefore the §7 power projection — the exact quantity this program exists to state honestly. CSMP's monthly cadence was less exposed to this. **Recommendation:** report the IC-series lag-1 autocorrelation per candidate and, where material, a block-bootstrap or Newey-West standard error as a robustness column, so power is not quietly overstated.

### F4 — C4 momentum-adjacency (§5)

For high-delivery names (`p_i(t) → 1`) the C4 score reduces to `s_i = + r_i(t−5, t)` — mechanically a one-week **continuation** leg. §5 pre-empts the objection and it is acceptable for a no-sealed-read screen, but because the CSMP fence is a *credibility* fence, the operator should explicitly acknowledge C4's continuation leg at ratification, so the successor program's D2 prior-exposure disclosure covers it.

### F5 — Net spread is an upper bound (§3/§6)

Same-close formation with no execution lag (kept for CSMP comparability, §3) makes the net top-quintile spread an **upper bound** on realizable economics. Acknowledged and correctly deferred to the successor pre-registration; state it as an upper bound wherever the number is reported.

---

## Minor

- **§11 data-integrity stop rule (> |20%| single-day move):** will trigger on legitimate mid-cap earnings/news moves, risking frequent false halts. Clarify it targets adjustment residue (e.g., cross-check the unadjusted move) or raise the threshold.
- **§6 net-spread baseline:** state whether the EW-universe baseline leg is also charged fees on membership churn, so the active net spread is apples-to-apples against the top-quintile leg.

---

## Recommendation

Address **F1** and **F2** (both verdict-affecting), fold **F3–F5** in as disclosure/robustness columns, add the Prompt-1 loader note, then ratify and stamp **FROZEN**. The battery's architecture — pre-registered five-candidate slate, structural power hurdle, Bonferroni-deflated single-winner selection, and the no-sealed-read boundary — is sound and faithful to operator decisions D1–D4.
