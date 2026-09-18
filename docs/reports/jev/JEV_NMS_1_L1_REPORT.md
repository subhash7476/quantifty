# JEV-NMS-1 — L1 Report (structural probe)

**Final gate status: L1 PASSED.** Every structural test passed with zero failures.
**L1 made no Jev calls.** L2 is **not** authorized by this
report; it awaits separate operator approval.

## 1. Purpose
L1 is the structural probe of protocol §13 ("L1 structural [R]"). It runs the §7 required tests
and two guards:
- input/label disjointness;
- isolation (a directory containing only D and D−1 reproduces the state exactly);
- request audit (every payload checked field by field against I_t and against the sealed
  template hash);
- a **fence guard** refusing any date outside the active set, and every buffer date;
- a **guard against dates beyond those present in the store**.

§26 lists L1 failure as an INVALID condition, so L1 is a gate before any further Jev call.

**Request count: 0, by definition.** §13 defines L1 as structural tests, and the §23 call budget
contains no L1 row (S0 10, L2 90, L3 100, development 1,600). L1 therefore sends no request.
Request IDs, latency, upstream timing, retries and response validity do not apply. The
append-only Jev cache is unchanged: SHA-256 `1a4e5bf5…f223f`, the same 10 S0 records.

## 2. Preregistered sample
| Check | Population |
|---|---|
| Disjointness and isolation | Every §4-eligible state of D-fit and D-eval: 685 sessions × 10 slots = **6,850 states**. Label locality covers every D-fit state at h = 5, 15 and 30: **13,260 label checks**. |
| Request audit | **Every preregistered Jev payload: 1,750**, all distinct. S0 10 (h15, already sent), L2 90 (`l2_year`), L3 50 (h15), development 1,000 (h15) plus 600 secondary (h5 and h30 for the first 30 development sessions). |
| Fence | The same 1,750 planned (stage, state) pairs as positives, plus 10 preregistered negative probes. |

All draws come from `draws_step2.json`, all features from `features_step2.json` and all
eligibility from `eligibility_step1.json`. Each file's SHA-256 was verified before use.

## 3. Checks and results

| # | L1 test | What was verified | Result |
|---|---|---|---|
| 1a | Input/label disjointness, features | Every state's nine features recomputed with every bar stamped ≥ t replaced by NaN equal the unpoisoned values. No input reads a label bar. | **6,850 / 6,850 pass** |
| 1b | Input/label disjointness, labels | Forward R, ER_f and RV_f recomputed with every close stamped ≤ t−2 replaced by NaN equal the stored D-fit label statistics exactly. The label reads only P(t) = C₍t−1₎ and bars t … t+h−1. Input bar set [0, t−1] ∩ label window [t, t+h−1] = ∅. | **13,260 / 13,260 pass** |
| 2 | Isolation | For each session, a fresh directory containing **only** the D file and the `previous_session(D)` file, both SHA-256-checked against step 1. Features were rebuilt with C_prev read from D−1's own 15:29 bar in that directory, not from any artifact. | **6,850 / 6,850 states reproduced exactly** |
| 3 | Request audit | Each of the 1,750 payloads rebuilt from the isolated I_t, then parsed back with literals preserved. Checked: top-level key order `model, state, questions`; model literal `jev-1.13.0`; the nine §6 state keys in order; every value's fixed-decimal literal equals the I_t value; I_t equals the sealed feature artifact; a single question keyed by the template's question ID; the question object equals the sealed template's (type, instructions, criteria, criteria order); all four template files match their sealed SHA-256. The 10 S0 bytes already sent were **byte-identical** to the rebuilt bytes. | **1,750 / 1,750 pass, 0 audit hits** |
| 4 | Fence guard, positives | Every planned (stage, state) passed its stage's fence. Active sets per §10/§23: S0 → D-fit; L2 and L3 → D-fit ∪ D-eval; development → D-eval; eligible sessions only. | **1,750 / 1,750 admitted** |
| 5 | Fence and store guard, negatives | Each preregistered probe must be refused (next table). | **10 / 10 refused** |

**Negative probes:**

| Stage | State | Refusal |
|---|---|---|
| S0 | 2023-02-28 10:00 | Outside S0's active set (before D-fit) |
| S0 | 2023-03-01 10:00 | Not eligible (no Nifty bars) |
| S0 | 2025-06-02 10:00 | Eligible, but D-eval is not S0's active set |
| development | 2024-06-03 10:00 | D-fit is not development's active set |
| L2 | 2024-03-04 10:00 | Not eligible (item 8) |
| L3 | 2026-01-05 10:00 | H-exposed: no Jev calls |
| development | 2026-09-18 10:00 | H-exposed: no Jev calls. Its file is also absent. |
| L2 | 2026-09-21 10:00 | Buffer date (> F₁) |
| P | 2025-06-02 10:00 | P has no active set before F₂ |
| L3 | 2027-01-04 10:00 | Buffer date (> F₁). It is also beyond the store. |

**[D] Store-guard branch.** In the live probe set, the two beyond-store dates were refused by an
earlier rule (buffer or H-exposed), so the beyond-store branch itself did not fire there. It is
verified separately by the unit test
`test_store_guard_refuses_an_eligible_in_set_date_whose_file_is_absent`. That test uses an
eligible, in-set, pre-F₁ date whose store file is absent, and the refusal is "beyond the store".

## 4. Request and response counts
| Item | Count |
|---|---|
| Jev requests sent by L1 | **0** |
| Responses | 0 |
| Retries | 0 |
| Cache records added | 0 (cache SHA-256 unchanged: `1a4e5bf5…f223f`) |

## 5. Validity
There were no responses to classify. All five structural tests passed with zero failures, so no
§26 L1-failure condition was met and no request-audit hit on post-t information occurred.

## 6. Timing
L1 ran from 2026-09-18T12:42:05Z to 12:43:45Z (UTC). No Jev-call timing applies.

## 7. Cache and request-hash provenance
- The request audit rebuilt all 1,750 preregistered payloads. Their canonical bytes are fully
  determined by the sealed templates and the audited I_t, so the future cache keys (the SHA-256
  of those bytes) are fixed.
- The only cached records remain the 10 S0 records. Their stored request bytes were verified
  byte-identical to the rebuilt payloads.

## 8. Model and version
L1 made no model calls. The model literal `jev-1.13.0` is verified in all 1,750 rebuilt
payloads. The environment matches the F₁ pins: Python 3.13.5, numpy 2.4.4, scikit-learn 1.8.0,
duckdb 1.4.3.

## 9. Pre-L1 verification
- **Seals:** the A2 seal chain verified. The addendum and its three references (F₁
  configuration, protocol, Amendment 2) match; all four templates, `environment.json` and
  `requirements-jev.txt` match; both freeze records match.
- **Artifacts:** all step-1, step-2 and S0 artifacts, the pickles, the S0 report, the cache and
  the ledger match their committed copies.
- **Code and tree:** the worktree was clean. There has been no protocol, configuration or
  template change since the A2 seal (`22060e5`), and the S0 code is unchanged since `d3c01a2`.

## 10. Artifacts
All paths are relative to `data/jev_market_state/`.

| Artifact | SHA-256 |
|---|---|
| `l1_step3.json` (full L1 record: every check, count and probe) | `502070d8148a73f1c94a63a334e2ce73da3ccd59a200e5d25e4a0838407ca11f` |
| `cache.jsonl` (unchanged by L1) | `1a4e5bf5cf851b23b34846df1d6a6f32a87ac208426ab91787b6f14fa11f223f` |

## 11. Ledger
`l1_started` (jev_calls 0) was written before any check. `l1_completed` (passed true, jev_calls
0, artifact hash) was written after. Earlier lines are unchanged. The ledger SHA-256 at report
finalization, through `l1_completed`, is
`9e01acba59d84c59bbea960b0989ee4bc97cf4b8bc51cc349feefb3e7f4d10c6`.

**Self-hash convention (as for S0).** This report's SHA-256 is recorded in a subsequent
`l1_report` ledger event, which changes the ledger hash. The final ledger hash is reported with
the commit.

## 12. Tests
- `tests/jev_nms_1` includes the new fence, store-guard and planned-request tests. Together with
  `tests/market`, `tests/database/utils/test_market_session_cas.py` and
  `tests/execution/test_cas_rules.py`: **216 passed, 1 skipped, 0 failed, no warnings.**
- The skip is the empirical CSMP calendar conformance test; that store is absent from this
  worktree.

## 13. Git
- Branch: `research/jev-nifty-market-state`.
- The L1 code (`fence.py`, `l1.py`, tests) was committed at `88948a8` (parent `5383fc4`)
  **before** the run.
- The L1 artifacts, the ledger, this report and the added store-guard unit test are committed
  together in the next commit.
- No protocol, configuration, template, model or earlier artifact changed.

## 14. Interpretation boundary
L1 provides **no predictive-performance evidence**. It checks structure only: point-in-time
construction, isolation, payload integrity and call fencing. Nothing was scored, fitted or
modified.

## 15. Stages not performed
**No L2, L3, development or prospective call was performed.** No pool fit and no ΔLL. The only
Jev calls under JEV-NMS-1 remain the 10 S0 requests.
