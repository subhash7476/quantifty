# PSB-2 Phase 1 — Lead Review

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** `8a95a28` (Phase 1 harness + dev-proof), `f961d19` (debug-artifact removal).
**Against:** `docs/reports/PSB2_PROTOCOL.md` — **FROZEN Rev 4**, §3/§5/§9/§11.
**Date:** 2026-07-16.

---

## Verdict: **BLOCK** — Phase 1 does not pass §11.2

§11.2 requires "the adapted screening harness must pass a synthetic-data dev-proof and Lead Review **before** any real candidate runs."

The dev-proof does not establish what it claims. Two of its arms are vacuous — they would report PASS against a harness that does not work at all:

1. **The S1 determinism proof hashes nothing.** Both subprocesses crash; the report compares the SHA-256 of the empty string to itself and prints "IDENTICAL". Reproduced exactly (below).
2. **The signal-recovery arm plants a signal no candidate can read.** `deliv_pct` is independent noise in both panels, so C2 cannot see the planted signal by construction. The report's own table confirms zero discrimination — C3's *null* IC (0.0350) exceeds its *signal* IC (0.0296) — and no prediction tests recovery at all.

This is not a request for polish. A dev-proof exists to demonstrate the pipeline recovers a signal it was given and reproduces byte-identically. Neither is demonstrated. The Phase 1 gate cannot be cleared on this evidence.

Separately, three correctness defects (T2.1–T2.3) must be fixed before Phase 2. They are latent on the synthetic panel — which is precisely why a dev-proof this shape did not surface them.

**Tiers:** T1 = the gate failure. T2 = correctness, must fix before any real candidate runs. T3 = hygiene.

---

## T1 — The dev-proof does not prove what it reports

### T1.1 — S1 determinism is vacuous (`run_devproof.py:168-181`)

```python
env = {**dict(PYTHONHASHSEED=hs)}
r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=env, ...)
(h0 if hs == "0" else h1).update(r.stdout.encode())
```

`env=` **replaces** the entire environment with one variable. The stripped environment drops the variables Python needs to locate its site-packages, so `import numpy` fails. `subprocess.run` without `check=True` does not raise on non-zero exit, so the crash is silent; `stderr` is captured and never inspected. `r.stdout` is `""`, and both hashes become the SHA-256 of the empty string.

Reproduced on this machine:

```
SHA256(empty)  = e3b0c44298fc1c14
child rc       = 1  ModuleNotFoundError: No module named 'numpy'
child stdout   = ''
hash(stdout)   = e3b0c44298fc1c14
```

`e3b0c44298fc1c14` is exactly the value printed in the report's §H for **both** seeds. The proof compares empty to empty. The commit message's claim "S1 determinism verified cross-process" is not supported.

**Fix:** `env={**os.environ, "PYTHONHASHSEED": hs}`; assert `r.returncode == 0` and surface `r.stderr`; assert the digest is not the empty digest. A determinism proof must fail loudly when the thing it measures did not run.

### T1.2 — The planted signal is invisible to the candidates (`run_devproof.py:59-97`, §C of the report)

`signal = {e: rng.normal(0, 1)}` is a fixed per-entity score planted into forward **prices** (`price[i, tp_idx] *= 1.03` for the top third). But `deliv_pct` is written as `rng.uniform(0.2, 0.7)` — independent noise, drawn identically in both panels.

C2 scores `deliv_pct`. Its input is therefore statistically identical between the null and signal panels: **C2's IC must be ≈ 0 in the signal arm by construction.** C3 inherits C2's percentile weight. The report's table is the confirmation, not the exception:

| Scenario | C2 IC | C3 IC | C4 IC |
|---|---|---|---|
| Signal | −0.0170 | 0.0296 | −0.0040 |
| Null | −0.0237 | 0.0350 | −0.0023 |

The signal arm is indistinguishable from the null arm, and for C3 the null is *stronger*. A pipeline returning ~0 on a planted signal is either broken or was handed an unreadable signal; this arm cannot distinguish those cases.

The section is titled "Pipeline Signal Recovery" but the prediction list contains **no recovery prediction** — only C-P1 (`null |IC| < 0.05`), F-P1 (fence), G-P1 (`net < gross`). The report is marked all-PASS because the one arm that could fail was never asserted on.

**Fix:** plant the signal in the feature each candidate actually reads — for C2/C3, make `deliv_pct` elevated for names that subsequently outperform; for C4, plant a persistent trend in the 12-1 price path. Then state a falsifiable prediction *before* the run, per the repo's research convention: e.g. **signal-arm mean IC > +0.10 and ≥ 3× the null-arm |IC|, for each candidate**. A dev-proof whose only predictions are "the null is null" and "fees are positive" cannot fail.

### T1.3 — Two required dev-proof arms were silently omitted

Prompt 1 specified arms **A–H**. The report contains §11.1, F, B, C, A, G, H. **D and E are absent** — not failed, not deferred, not mentioned; `run_devproof.py` contains no code for either. The report's own section lettering skips them.

- **D — C3's sign convention.** Prompt 1: *"Plant **both** regimes; show the recovered sign matches §5's stated hypothesis in each. An interaction-term sign error is the classic defect that survives to production looking plausible."* `test_c3_21_day_return_horizon` plants a single regime and asserts both names score positive — it does not test the p→0 reversal vs. p→1 continuation split at all. Acceptance criterion 7 is unmet.
- **E — Staggered mechanics.** Prompt 1: *"A name entering a tranche stays until **that tranche's** next rebalance regardless of rank drift; realized turnover ≈ 1/6 per month. **C4's IC is invariant to the holding mechanism** — if staggering changes the IC, that is a bug."* Nothing tests this. Acceptance criterion 8 is unmet. This is the arm that would have caught **T2.3**, and Prompt 1 named the staggered path "the highest-risk new code in this prompt."

An omitted arm is worse than a failed one: a failure is visible, an omission reports all-PASS. Combined with T1.1, T1.2, and T3.1, **at least six of Prompt 1's thirteen acceptance criteria (4, 5, 6, 7, 8, 10) are unmet while the report reads all-PASS.** Criterion 9 is treated separately in T1.6 — it was not satisfiable as written.

### T1.4 — G-P1 and C-P1 are near-unfalsifiable

`net < gross` (G-P1) holds whenever fees are non-zero — it is true of any fee model, correct or not, and does not test era-accuracy, per-leg STT, or κ. C-P1 (`null |IC| < 0.05`) is a weak bound at n≈55. Neither constrains the implementation. G's turnover column is the informative number and is unasserted: C2 shows 0.4677 against §3's design expectation of ~0.15. On i.i.d. synthetic data high turnover is expected and this is **not** itself a defect — but it means the §3 turnover premise remains entirely untested, and it is the premise the whole battery's fee-survivability rests on.

### T1.5 — The §11.1 gate is reported, not enforced (`run_devproof.py:121-134`, `241-246`)

The report's §11.1 block ends with the certifier's own words:

```
| Arm B cross-symbol handoff | HALT | 4 splice fabrications |
CERTIFICATION INCOMPLETE - HALT items above must be resolved.
```

The report then editorializes: *"Arm B: 4 known splice fabrications (same as PSB-1, resolved by fragmentation test)."* Three problems:

- **The claim contradicts the suite's contract.** `certify_substrate.py:265` — `b_halt = arm_b.splices  # ALL splices HALT (none dispositioned)`. Arm B is zero-tolerance by design and reports raw counts, unlike Arms A/D which report "(N dispositioned, 0 undocumented)". "Resolved" is prose with no register entry behind it.
- **`_certify()` is dead code.** It is defined at line 121 and **never called** — `main()` reads `certify_output.txt` off disk directly (line 242). The §11.1 evidence is an unverified, possibly stale cache; if the file were absent the section would degrade to the prose sentence alone.
- **Nothing gates.** The certifier's HALT does not enter `all_pass`. §11.1 calls this "a structural gate — no Phase 1 without a certified substrate."

I am **not** asserting the substrate is uncertified — the 4 splices are plausibly the known PSB-1 items, and the working tree currently shows an uncommitted edit to `PSB1_SUBSTRATE_CERTIFICATION.md`. **Required:** reconcile the 4 splices against the committed disposition register, and either gate on the result in code or record an explicit operator disposition. A HALT may not be cleared by a sentence in a generated report.

### T1.6 — The fence arm proves less than §F asked, and could not have proved it. **This defect originates in Prompt 1, not in the implementation.**

Prompt 1 §F required: *"Plant a 2023 row on a **synthetic** panel and show the fence **raises** — not warns, not filters silently."* §4 separately required: *"The fence test below stays on synthetic data; do not let it become a third touchpoint."*

**Neither instruction was satisfiable.** Two facts about read-only PSB-1 machinery settle it:

- **`load_panel` cannot raise on a post-fence row.** It filters at `screening_harness.py:128` (`WHERE a.trade_date<=?`) and *then* asserts at line 145 (`assert observed_max <= cutoff`). The assert is downstream of the filter, so it is **structurally unreachable** — a planted 2023 row is silently dropped, which is precisely the "filters silently" behavior §F declared unacceptable. `scripts/psb1/` is read-only, so this cannot be fixed under Prompt 1's own constraints.
- **`fence_check` is a real-store touch by design.** Its docstring: *"The ONLY permitted real-store touch in Phase 1 (§7 exception / P7): dates + counts only... asserts `fenced <= cutoff < unfenced` — evidence that sealed data is physically present and was excluded, **not merely that a WHERE clause filtered** (Lead Review S2/S3)."* PSB-1's Lead Review found this exact tautology and built `fence_check` as the answer. §4's "keep the fence synthetic" instruction contradicts the control's purpose.

**What was delivered is therefore the right call**, and I credit it: calling `fence_check()` on the real store is the sanctioned control operating as designed, and its `fenced <= cutoff < unfenced` result is meaningful evidence — it proves sealed data physically exists and was excluded, which a synthetic panel cannot prove. It reads a date and a count; no prices, symbols, or scores. On the best reading it is **not** a §1 breach: §1 prohibits "any load of price, delivery, volume, or universe data," and an aggregate `MAX(trade_date)`/`COUNT(*)` loads none of those, so §1's "sole exception" clause is not even engaged.

**Two items for disposition, neither chargeable to the implementer:**

1. §1's sole-exception clause names `trading_calendar` only. `fence_check` reads `equity_bhavcopy_adjusted` metadata. The protocol is FROZEN, so this cannot be reconciled by editing §1 — it wants an explicit **operator disposition** recording that the aggregate read is outside §1's prohibition rather than an exception to it.
2. `load_panel`'s tautological assert should be stated in the Phase 1 report as a **known limitation**, with `fence_check` named as the actual protection. A report that prints "Sealed fence OK: observed MAX ≤ cutoff" from a filtered load implies a check that did not occur.

---

## T2 — Correctness defects (must fix before Phase 2)

These are latent on a dense synthetic panel and would activate on real data.

### T2.1 — `date_ic` is fed pre-imputed forwards; the primary IC is contaminated (`harness.py:425-438`)

PSB-1's `date_ic(s_all, fwd_all)` expects `fwd_all` **to contain `None`** for missing forwards. It does the imputation itself:

```python
present = [(s, f) for s, f in zip(s_all, fwd_all) if f is not None]   # primary: excludes missing
worst = min(f_p)
f_imp = [f if f is not None else worst for f in fwd_all]              # §4.2 column
```

PSB-2 builds `fwd_imputed` with `worst_fwd` **already substituted**, then passes it as `fwd_all`. Inside `date_ic`, `present` filters nothing, so:

- **`ic_primary` is computed over the imputed vector** — the headline IC now assigns every delisted/missing name the date's worst return. This IC is the §8(i) eligibility statistic *and* the δ driving §7 power.
- **`ic_primary == ic_imputed` identically**, for every date. The §4.2 robustness column becomes a duplicate of the primary, and `sign_flag` (`harness.py:465`) is therefore always `False` — it can never fire.

The synthetic panel has a price for every entity every day, so `_ret` is never `None`, imputation never triggers, and both values coincide with the correct answer. The dev-proof could not have caught this.

**Fix:** pass forwards with `None` preserved, exactly as PSB-1 does at its lines 736-737, and let `date_ic` own the imputation.

### T2.2 — C2's fortnight window is improvised, with unpinned constants (`harness.py:146-164`)

§5 pins: `dp_i(t) = mean of deliv_pct over fortnight's whole trading days ending t (≥ 8 non-NULL)`. The implementation:

```python
# For the harness we use a sliding window approach: the last ~10 trading days.
# Simpler: take the most recent ~10 full-session days ending at t.
for j in range(cal_idx, max(cal_idx - 20, -1), -1):
    ...
    if len(recent_dps) >= 15:
        break
```

This scans back **20** trading days and stops at **15** non-NULL observations. Neither 20 nor 15 appears in §9's exhaustive pinned-parameter list; both were introduced at implementation time. The window is systematically longer than a fortnight (~10-11 trading days), so `dp_i(t)` is not the §5 quantity — and the comments contradict the code they sit above ("~10 trading days" vs. 20/15).

Root cause is structural: `score_c2_psb2(panel, t)` has no access to the grid, so it cannot know the prior grid date. The scorer needs the fortnightly grid (or the prior grid date) passed in, and must average `deliv_pct` over trading days in `(prev_grid_date, t]`, requiring ≥ 8 non-NULL. §9 immutability is not yet breached — no candidate result exists — but this must be corrected before one does.

### T2.3 — C4 silently drops held names that stop scoring (`harness.py:308-309`)

```python
fwd_map = {e: f for e, s, f in rows}          # only names scored at t, with a forward
topq_held_seq.append((t, [(e, fwd_map[e]) for e in sorted(held) if e in fwd_map]))
```

§5 is explicit: *"A name held in any tranche remains held until its tranche's next rebalance date, regardless of rank drift."* A held name that fails to score at a later `t` — left the universe, lost 12 prior grid dates, missing forward — is filtered out of that period's holdings by `if e in fwd_map`. Its return over the period is excluded from the portfolio return, and because `_simulate` derives `cur` from the holdings list, it is charged a phantom SELL on the way out and a phantom BUY if it scores again later. It remains in `tranches[k]`, so it can silently re-enter at a new price with the intervening return discarded.

This corrupts the §8(ii) net-spread for C4 in both directions: dropped returns and fabricated churn.

**Fix:** hold the name at its actual forward return until its tranche's rebalance; only a genuinely untradeable name should exit, and then through the §4.2 imputation rule rather than by vanishing.

*(Note: I initially flagged the union-of-6-cohorts breadth as a defect. It is not — an overlapping 6-month-hold portfolio holding ~6 cohorts' worth of names is inherent to the construct. The equal-weight-across-union vs. average-of-cohort-means distinction diverges only for names held in multiple tranches; record it as a minor fidelity note, not a blocker.)*

### T2.4 — The exit band is not plumbed; the pinned constant is dead (`harness.py:343, 350, 476`)

```python
exit_band = C2_EXIT_BAND      # assigned...
...
topq_seq, botq_seq, base_seq = _quintile_sequences(scored_by_date, banded=True)   # ...never passed
```

`_quintile_sequences` takes no band parameter — it reads PSB-1's module-level `C5_EXIT_BAND` (`screening_harness.py:65`). PSB-2's `C2_EXIT_BAND`/`C3_EXIT_BAND` are **never read by any code path**. Today both are 0.40, so the behavior is accidentally correct; a change to PSB-1's C5 constant would silently retune PSB-2's frozen band, and PSB-2's own constants would keep asserting 0.40 while the harness used something else.

**Fix:** give `_quintile_sequences` an explicit band parameter and pass PSB-2's constant. PSB-1 stays git-clean only if the reuse route is honest — an unparameterized borrow of a PSB-1 constant is a hidden coupling, not reuse.

---

## T3 — The fidelity suite does not test what it claims

The commit message states the suite covers "every pinned §9 parameter with exact expected values"; the file docstring says "a wrong constant makes the assertion fail on a known input." **Both claims are false for 9 of 10 tests.** This matters more than any single defect: it is the reason T2.1–T2.4 shipped as 10/10 PASS.

**Five are constant tautologies** — `test_exit_band`, `test_staggered_tranches`, `test_power_hurdle`, `test_bonferroni_m`, `test_slippage_kappa` assert only `H.X == literal`. They exercise no harness behavior and cannot fail unless someone edits the constant in the same commit. `test_exit_band` is worse than empty: it asserts a constant T2.4 shows is **dead**, and reports PASS for a band the harness never reads.

**Four are mutation-insensitive** — each passes under mutation of the parameter it names:

| Test | Claims to pin | Why it cannot fail |
|---|---|---|
| `test_c2_252_day_baseline_ending_t21` | 252-day baseline / window | Plants `dp=0.80` across **20** recent days, so *any* window length yields mean 0.80. Docstring says "z ≈ 16.7"; the assertion is `z > 1.0`. Actual 17.6071. Cannot detect T2.2. |
| `test_c2_fortnightly_mean_min_8` | `≥ 8` non-NULL | Only ~30 non-NULL exist in the baseline region vs. the required 150. Set `DELIV_MEAN_MIN = 5` and the entity is still skipped — by the **baseline** rule. Assertion passes either way. |
| `test_c3_21_day_return_horizon` | 21-day horizon | Every close is 100.0 except at `t`. Any horizon *k* gives `r = 110/100 − 1`. Insensitive to 21. |
| `test_c4_lookback` | `g−12` and `g−1` | All off-grid closes are 100.0 and `t_12` is *set* to 100.0 — a no-op update. Any *k* ≠ 1 yields `r_12 = 0.20`. Sensitive to `g−1` only; insensitive to the 12. |

`test_fortnightly_grid` is the one substantive test (first/last dates are calendar-sensitive) — but see T3.1.

**Fix:** for each pinned parameter, plant data that makes the *correct* value produce a value that a *wrong* value cannot. Vary `deliv_pct` by day so a wrong window shifts the mean; vary closes along the path so a wrong horizon shifts the return; give the baseline ≥150 valid observations so the min-8 branch is the only one that can fire. A test that passes under mutation of its own parameter is not a fidelity test. Delete the five constant assertions or replace them with behavioral ones.

### T3.1 — Grid identity is checked against a synthetic calendar

`run_devproof.py:209-212` builds the grid from `_bday_span(...)` — a holiday-free Mon-Fri calendar — not from `trading_calendar` at the `n_symbols >= 200` convention that §3 pins. The three counts (56/132/28) are arithmetically forced for *any* calendar with at least one session on each side of the 15th, so they cannot fail; the date assertions (`2020-09-15`, `2022-12-30`) are validated only against the fake calendar. §3 derives 56 from `scripts/psb2/count_grid_dates.py` reading the **real** calendar. Section B should read the real `trading_calendar` (dates only, §1's stated exception) or state that it delegates to the Phase 0 script.

---

## T4 — Hygiene

| # | Item | Location |
|---|---|---|
| 1 | `q1_q5` hardcoded `0.0`; `botq_seq` computed then discarded — PSB-1's gross Q1-Q5 column is silently zero for every PSB-2 candidate | `harness.py:476, 524` |
| 2 | `s_all` / `fwd_all` are built **misaligned** (score appended when forward is `None`, forward is not) — dead code today, but it is the botched draft of T2.1 | `harness.py:409-417` |
| 3 | `DEV_HI` imported from PSB-1, then shadowed by a local redefinition (same value) | `harness.py:44, 81` |
| 4 | Unused imports: `scipy.stats as ss`, `sealed_grid_count`, `CAP`, `POWER_TIE_BAND` | `harness.py:23, 30, 48, 53` |
| 5 | Docstring claims `_day_forward` and `BONFERRONI_M` are "imported unchanged from PSB-1" — neither is; `BONFERRONI_M` is correctly redefined to 3 (PSB-1 has 5), so the docstring, not the code, is wrong | `harness.py:8-13, 61` |
| 6 | `_ret` recomputed for every name a second time in the imputation loop — 2× the work per date | `harness.py:409, 429` |
| 7 | `.get(t_21, -1)` / `.get(t_base, -1)` defaults silently yield an empty range → `continue`. A missing calendar position should raise, not silently skip a name | `harness.py:168` |
| 8 | `tp` computed and never used; `_staggered_sequences` takes `panel` and never uses it; `g_idx + 1 >= len(...)` silently drops the last formation | `harness.py:251-278` |
| 9 | `fortnightly_grid` appends `d` twice if a month's last session falls on or before the 15th (not reachable on the NSE calendar; one guard closes it) | `harness.py:89-104` |
| 10 | `tests/psb2/run_quick.py` is a debug runner still in the tree — `f961d19` removed two such artifacts and missed this one; it is also what §A of the report shells out to | `run_devproof.py:216` |
| 11 | `_build_panel` inserts row-by-row (~105k `con.execute` calls), the bulk of the 391s runtime; `executemany` is already used elsewhere in the same file | `run_devproof.py:90-97` |

---

## Required to clear the Phase 1 gate

Re-run the dev-proof and resubmit once:

1. **T1.1** — S1 inherits `os.environ`, asserts child `returncode == 0`, and fails on an empty digest.
2. **T1.2** — the signal is planted in the feature each candidate reads, with a falsifiable recovery prediction stated **before** the run.
3. **T1.3** — the omitted arms D (C3 sign in both regimes) and E (staggered mechanics; C4 IC invariant to holding) are built and reported.
4. **T1.5** — the §11.1 Arm B HALT is reconciled against the committed disposition register and either gated in code or dispositioned by the operator; `_certify()` is called or deleted.
5. **T2.1–T2.4** — the four correctness defects fixed.
6. **T3** — the fidelity suite rebuilt so each test fails under mutation of the parameter it pins; the five constant assertions removed or made behavioral.

**T4 is non-blocking** and may be folded into the same resubmission.

The reusable lesson matches this program's history (`PSB1_SUBSTRATE_CERTIFICATION`, `psb1-contract-shaped-certification`): **a suite shaped to pass is worth less than no suite** — it converts unknown risk into false confidence. Every T2 defect was inside the declared scope of a test that reported PASS. The fix is the same one PSB-1 arrived at: assert against a planted answer the wrong implementation cannot produce.

---

## What is correct

Credit where due — the following are right and should not be touched on resubmission:

- **The reuse route.** Importing from `scripts.psb1.screening_harness` keeps `scripts/psb1/` git-clean and verifiable; `git status` confirms it.
- **Scorer naming.** `score_c2_psb2` etc. are unambiguous against PSB-1's C1–C5, whose numbering differs — a real trap, avoided.
- **`BONFERRONI_M = 3`** correctly overrides PSB-1's 5, matching §8's D11 rationale.
- **C4's 12-1 formula** (`harness.py:242-244`) is exactly §5: `(1 + r_12) / (1 + r_1) − 1`, with the `grid-index` lookback (`g−12`, `g−1`) rather than a calendar-day approximation — the subtle part, done right.
- **C3's ordering** (`harness.py:198-211`) — percentile ranks computed across all C2-scored names *before* dropping names that lack a 21-day return — matches §5's "among names scored at *t*".
- **Per-candidate `ppy`** (24 fortnightly / 12 monthly) and the separate `sealed_grid_count_psb2` cadence dispatch correctly implement §7's mixed-cadence n\*.
- **The dev fence** (F) is real and passes: fenced MAX 2022-12-30 < unfenced 2026-07-09.
