# PSB-1 Implementation Prompts

Prompts issued by the Lead Reviewer (Claude) to the implementation party (DeepSeek V4).
One prompt per phase gate; a prompt is binding only after it appears in this file.
Governing documents: `PSB1_PROTOCOL.md` (**FROZEN Rev 2**, ratified 2026-07-13) and
`PSB1_PHASE0_RESEARCH_RECORD.md` (operator decisions D1–D4).

Standing constraints (every prompt, non-negotiable):

- The protocol is frozen. Implement it **exactly as written**; if a section is
  ambiguous or unimplementable, STOP and report — do not resolve ambiguity in code.
- Zero changes to feature-frozen components (`CLAUDE.md` table) and zero changes to
  any `scripts/csmp/` file. PSB-1 code lives in `scripts/psb1/` (+ `tests/psb1/`).
- Store opened `read_only=True`. Every real-data load asserts **and prints** the dev
  fence: `MAX(trade_date) <= 2022-12-31` (protocol §1/§10). Sole exception: the §7
  sealed-grid count (dates only, from `trading_calendar`).
- Deterministic, re-runnable to byte-identical output. Failures reported as failures.
- Reports are script-generated, stamped with code commit and the store's row count +
  `MAX(trade_date)` at run time.

---

## Prompt 1 — Phase 1: screening harness + synthetic dev-proof (ISSUED 2026-07-13)

### Mission

Build the PSB-1 screening harness and prove it on **synthetic data only**. This prompt
authorizes **no candidate score on real data** — not as a smoke test, not "just to
check wiring." Real-data schema probes (row counts, date ranges, column presence) are
permitted; anything that produces an IC, spread, or score distribution from real data
is Phase 2 and requires the Phase-1 Lead Review PASS first (protocol §11.1–11.2).

### Deliverables

1. `scripts/psb1/screening_harness.py` — the library:
   - **Loading** (protocol §2): derive from `run_a2_validation.load_window()` at
     commit `0ae1dc4` (keep the ever-member entity restriction and the
     `rn=1` turnover-primary listing dedup), re-fenced to 2022-12-31, extended to
     carry `deliv_pct` **through the same `rn=1` pick as the price** (named
     acceptance criterion AC-3).
   - **Grids** (§3): weekly (last full-session day per ISO week) and monthly (last
     full-session day per month) from `trading_calendar` with `n_symbols >= 200`.
   - **Scoring** (§5): C1–C5 exactly as written, including every completeness rule
     (≥40/52 beta weeks, ≥3/5 delivery days, ≥40/60 baseline days, σ > 0 guards,
     ≥200/252 vol days), the §4 direction convention, and percentile ranks with
     average ties.
   - **Metrics** (§4/§6): per-date Spearman IC; series mean/SD/n, one-sided t and p;
     net top-quintile spread with gate-(d) fees + κ=5bp/side on turnover-derived
     notional, baseline leg charged on its own churn, C5 banded; the §4.2
     worst-realized-forward-return imputation as a parallel robustness column; AC₁ of
     the IC series with the Newey–West (lag 4) robustness t when |AC₁| > 0.1;
     exclusion counts per date.
   - **Power** (§7): exact sealed-grid `n*` from `trading_calendar` dates; noncentral-t
     projected power at δ = dev mean IC (and reported-only at δ/2, and NW-SE variant
     when triggered).
2. `scripts/psb1/run_synthetic_devproof.py` — builds a synthetic panel (its own
   DuckDB file under `data/psb1_synthetic/`, never the real store), runs the harness
   end-to-end, and writes the script-generated report
   `docs/reports/PSB1_PHASE1_HARNESS_REPORT.md`.
3. `tests/psb1/test_scoring.py` — unit tests for each §5 scoring function on
   hand-built fixtures (known inputs → hand-computed scores), the completeness rules,
   and the §4.2 imputation.

### Synthetic dev-proof — falsifiable predictions (state, then run)

The synthetic panel: ≥200 names × ≥150 weekly grid dates, with prices, `deliv_pct`,
a synthetic `trading_calendar`, synthetic universe membership, and planted delistings.
The report must show, in this order:

- **P1 (planted signal):** forward returns constructed as `a·score + noise` with known
  `a` and noise scale chosen so the analytic expected rank IC is ≈ 0.05. Measured mean
  IC within ±0.02 of the analytic expectation.
- **P2 (null):** `a = 0` → the 95% CI of mean IC covers 0.
- **P3 (sign wiring):** plant reversal (forward return negatively proportional to past
  5-day return) → **C1** mean IC is positive; plant delivery-direction (forward return
  positively proportional to abnormal delivery) → **C3** mean IC is positive. This
  proves the §4 direction convention end-to-end, not just in unit tests.
- **P4 (F2 machinery):** plant delistings concentrated among past losers → the §4.2
  imputed column shows **lower** C1 mean IC than the primary column (direction of the
  known bias), and the report prints both.
- **P5 (fees):** the fee model is called with era-correct synthetic dates; total fees
  > 0 on both the top-quintile and baseline legs; net spread < gross spread.
- **P6 (determinism):** the entire dev-proof run twice produces **byte-identical**
  reports (hash printed for both runs).
- **P7 (fence):** the loader pointed at the real store in a fence-check mode asserts
  and prints `MAX(trade_date) <= 2022-12-31` without computing any score (this is the
  only permitted real-store touch, and it loads dates only).

### Acceptance criteria (Lead Review checks each)

- **AC-1:** all seven predictions P1–P7 pass, shown in the script-generated report.
- **AC-2:** no candidate score computed on real data anywhere (code inspection +
  report).
- **AC-3:** `deliv_pct` flows through the same `rn=1` listing pick as `adj_close`
  (review Prompt-1 caveat) — demonstrated by a unit test with a two-listing synthetic
  symbol where the turnover-primary row differs from the other listing.
- **AC-4:** §5 formulas match the frozen protocol symbol-for-symbol (diff review); all
  pinned parameters read from one constants block that quotes §9.
- **AC-5:** unit tests pass; determinism (P6) holds; the report carries commit hash +
  store stamps.
- **AC-6:** zero diffs outside `scripts/psb1/`, `tests/psb1/`,
  `data/psb1_synthetic/` (gitignored if binary), and the report file.

### On completion

Commit with message prefix `feat(psb1): Prompt 1 —` and report back for Lead Review.
Phase 2 (the battery run, C1→C5 in §11.2 order) begins only after a written PASS.
