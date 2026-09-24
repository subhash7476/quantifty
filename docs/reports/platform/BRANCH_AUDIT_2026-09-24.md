# Local branch audit — 2026-09-24

**Scope:** the 24 local branches with no worktree and no GitHub copy (excluding `main`, `research/ptms-price-time-market-structure`,
`research/funnels-filter`). Checked against `origin/main` at `b02b519`, three ways:
- **commits by hash:** `git rev-list origin/main..<branch>`;
- **patches:** `git cherry` (patch-equivalent commits);
- **files:** every file the branch changed since its merge-base — is the same blob anywhere in main's tree?

## 1. Fully on main — safe to delete (18)

0 commits missing from main by hash:

`docs/cas-register-frozen-spot` · `feat/n200-regime-hmm` · `feat/niftyshield-model-retrain` · `feat/ops-orchestrator` ·
`feat/options-wall-trade-detail-panel` · `fix/daytype-reproducibility` · `fix/nifty-shield-option-fees` ·
`fix/options-wall-cas-squareoff` · `fix/options-wall-expiry-settlement-exit` · `fix/options-wall-regime-flip-exit` ·
`fix/options-wall-stale-selfheal-test` · `fix/options-wall-tp-sl-thresholds` · `fix/ts-basis-daily-signal-defects` · `list` ·
`perf/pipeline-incrementalization` · `platform/nse-holidays-2023-2025` · `research/multi-factor-combination-assessment` ·
`research/reliance-regime-daily`

## 2. Content not on main (6)

None of these branches' commits has a patch-equivalent on main, except 1 of the bundle's 40.

| Branch | Last commit | Missing commits | Files: only on branch / differ on main / identical |
|---|---|--:|---|
| `fix/nifty-shield-poller-expiry-mismatch` | 2026-08-17 | 1 | 3 / 2 / 0 |
| `research/daytype-horizon-ceiling` | 2026-09-09 | 1 | 2 / 0 / 0 |
| `research/options-seller-edge` | 2026-09-11 | 2 | 9 / 2 / 0 |
| `research/n50-ls` | 2026-08-03 | 5 | 18 / 1 / 0 |
| `research/strategy-challenge` | 2026-08-07 | 38 | 69 / 8 / 0 |
| `research/nifty-research-bundle-adoption` | 2026-08-07 | 40 | 71 / 13 / 6 |

`n50-ls` ⊂ `strategy-challenge` ⊂ `nifty-research-bundle-adoption`, so the last one contains all 40 commits.

### 2.1 A production fix that never reached main — act on this

`9342718 fix(eod): gate the EOD chain on equity in addition to futures` (2026-08-07, on the bundle branch). Main's
`core/scheduler/eod_decision.py` still gates on futures only. That is the open CLAUDE.md pitfall "Gating a multi-feed
pipeline on one feed makes every other feed optional". The fix touches `eod_decision.py` plus two test files (+41/−14).
It should be brought to main on its own and re-tested against the current `eod_decision.py`, not merged with the whole
research bundle.

### 2.2 What else is only on these branches

- **`research/options-seller-edge`:** `docs/reports/strategies/OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md` and the 8
  `scripts/research/options_seller_edge/*.py` that produced it. The memory note `options-seller-edge-study` cites this
  report as the study's record. `scripts/research/` is gitignored, so these were force-added.
- **`research/daytype-horizon-ceiling`:** `DAYTYPE_HORIZON_CEILING.md` and `scripts/daytype/horizon_ceiling_diagnostic.py`.
- **`fix/nifty-shield-poller-expiry-mismatch`:** 3 triage/prompt/review docs. Its `chain_poller.py` and test changes
  differ from main's, which has evolved since, so they are likely superseded. That is unverified.
- **The research bundle** (n50-ls → strategy-challenge → bundle):
  - N50-LS and OSC research docs, RFA declarations (`n50_ls.py`, `se1.py`, `se3.py`), and the `scripts/osc`, `se1` and
    `se3` suites;
  - Carry/TS Basis paper-startup docs;
  - modified `span_pipeline.py`, `eod_chain.py`, `carry_paper_runner.py`, `carry_forward_runner.py`,
    `refresh_all_strategies.py` and the carry/ts_basis `publish_facts.py`. Main's versions differ, and whether each
    branch change is superseded or still missing is **unverified**.
  - Of note: the RFA declarations are governance artifacts, and CLAUDE.md's RFA table does not list N50-LS, SE1, SE3 or OSC.

## 3. Recommendation

1. Delete the 18 branches in §1.
2. Bring `9342718` (the EOD equity gate) to main as its own PR, re-tested against the current code.
3. Rescue docs and scripts that exist only on a branch, as was done for PR #12: the seller-edge study and its scripts,
   the daytype horizon-ceiling diagnostic, the expiry-mismatch docs.
4. The research bundle needs a per-file review before deletion, because it mixes research and production code. Keep it
   until that review is done.
