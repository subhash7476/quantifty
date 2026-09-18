# JEV-NMS-1 — L2 Report (year-memorization probe)

**Final gate status: L2 PASS.** 28 of 90 correct. The one-sided exact binomial test against
chance 1/3 gives p = 0.7088, which is not below the preregistered failure threshold of 0.01.
L3 is **not** authorized by this report; it awaits separate operator approval.

## 1. Purpose and preregistered rule
§13, sealed at F₁ (`config.json` `probes.l2_fail_p` = 0.01, `probes.l2_chance` = 1/3), reads:

> "L2 memorization: 90 states (30 per year 2023/2024/2025, §23 draw) with Template 4. Fail if
> a one-sided binomial test against chance 1/3 gives p < 0.01. On failure, development results
> are CONTAMINATED, no development conclusion is drawn, and P requires explicit operator
> approval before F₂."

**Test as applied:**
- **Success:** Jev's answer equals the state's true calendar year.
- **Statistic:** `scipy.stats.binomtest(k, n, 1/3, alternative="greater")`, exact, scipy 1.17.0
  (pinned).
- **Two readings of "answer", both evaluated:** the `choice` field and the arg-max probability.
  The run was set to withhold the gate result for a ruling if the readings disagreed on any
  state, if any arg-max tied, or if any response was invalid. **None of these occurred:** all
  90 responses were valid, the readings agreed on all 90, and there were no ties.

## 2. Sample and draw provenance
The sample is the preregistered A2-1 draws in `draws_step2.json` (SHA-256 `e4c1f3c9…33de8`),
using the A2-2 population rule (eligible sessions within D-fit ∪ D-eval, grouped by calendar
year; 2023 starts at 2023-03-01).

| Draw | Population | Population SHA-256 | Output |
|---|---|---|---|
| D4-2023 | 201 eligible sessions | `8183db3a25f572b6…` | 30 sessions |
| D4-2024 | 241 eligible sessions | `9c1941cc1a22740e…` | 30 sessions |
| D4-2025 | 243 eligible sessions | `c0e7ba1b498e52d0…` | 30 sessions |
| D4t timestamps | the 90 L2 sessions in date order | `82436a9c3a639da0…` | one drawn slot per session |

- **Result:** 90 states (30 per year), 90 distinct payloads. The full state list is in
  `l2_step4.json` and `draws_step2.json`.
- **Overlap with development (permitted, disclosed in A2 review):** 30 of the L2 sessions are
  development sessions. These are exactly the 2025 L2 draw, which equals D2, because the
  identical population and seed-42 stream produce the same sample.

**Before sending:**
- every state passed the L1 fence for stage L2;
- every payload passed the request audit (features rebuilt from the SHA-256-checked store equal
  the sealed features);
- the `l2_year` template matched its sealed SHA-256 (`e94e351b…5804d0`);
- the L1 artifact confirmed a pass.

## 3. Requests and responses
| Item | Value |
|---|---|
| Run ID | `L2-20260918T125022Z` |
| Scheduled / sent | 90 / 90 |
| Valid / invalid | **90 / 0** (schema-invalid 0, transport failures 0) |
| Attempts per request | 1 (**0 retries**) |
| HTTP status | 200 for all 90 |
| Model echoed | `jev-1.13.0` for all 90 |
| Probability vectors | Keys exactly {2023, 2024, 2025}; all in [0, 1]; every sum exactly 1.0 |
| Request IDs | 90 captured, all distinct (`x-typesafe-request-id`) |
| Usage | 749–761 input tokens, 51 output tokens per request |
| Sent / received | 2026-09-18T12:50:22.123Z → 12:50:57.351Z (UTC) |
| Latency | min 320.4 ms, median 373.0 ms, max 986.5 ms (the first request includes TLS setup) |
| Upstream (`x-envoy-upstream-service-time`) | min 53 ms, median 101 ms, max 589 ms |
| Keep-alive | One connection, reused for requests 2–90 |
| Timing validity | Not applicable (§11: historical call; t+15 s / t+60 s applies to P only). Recorded in full. |

## 4. Result
| Statistic | Value |
|---|---|
| n (valid) | 90 |
| Successes (`choice` = true year) | **28** |
| Successes (arg-max = true year) | 28 |
| One-sided exact binomial p (H1: p > 1/3) | **0.7088448046066163** |
| Failure threshold | p < 0.01 |
| **Gate result** | **PASS** |

Descriptive counts, reported without interpretation beyond §13 (rows are the true year,
columns Jev's `choice`):

| True year | → 2023 | → 2024 | → 2025 | Correct |
|---|---|---|---|---|
| 2023 (n = 30) | 2 | 28 | 0 | 2 |
| 2024 (n = 30) | 4 | 26 | 0 | 26 |
| 2025 (n = 30) | 4 | 26 | 0 | 0 |

Maximum class probability per response: min 0.49, median 0.56, max 0.64.

Under §13, a PASS means the memorization failure condition was not met. Development results are
therefore not marked CONTAMINATED by L2.

## 5. Cache, request hashes and artifacts
- **Cache:** append-only `cache.jsonl` now holds 100 records under 100 distinct keys (S0 10,
  L2 90). No key was re-sent and no bypass was used.
- **Request hashes:** each L2 record stores its exact request bytes, the SHA-256 (the cache
  key), attempts, raw response and validity. The first key is
  `4ecd7ce5f3f461e56b1441167cbcd4d1f6611466a141a5c4784ad91e86d5b8ab`, for 2023-03-14 10:30. All
  90 keys are in `l2_step4.json` and in the `l2_started` ledger event, which was written
  before the first send.

All paths are relative to `data/jev_market_state/`.

| Artifact | SHA-256 |
|---|---|
| `l2_step4.json` (L2 run record and decision) | `c27b65eba39c76052e5e94271ee33bea60e917d643140eedaa880dfc0143be92` |
| `cache.jsonl` (after L2) | `4c2a4889a25b790a531efa4b20428e1169a3f9745d2bc1213631a1a4ae06bf47` |

## 6. Ledger
- `l2_started` (run ID, template, model, transport ID, and all 90 planned state and key pairs)
  was written **before** the first send.
- `l2_completed` was written after, with the artifact SHA-256, result PASS, 28 successes and
  the p-value.
- Earlier events are unchanged.
- Ledger SHA-256 through `l2_completed`: `dca85ed7ea00c9c786bd4ff5d17aa6306886c2c78ba5fae21d7840d3c42fcc6e`.
- **Self-hash convention:** as for S0 and L1, this report's SHA-256 is recorded in a following
  `l2_report` ledger event. The final ledger hash is reported with the commit.

## 7. Model, environment and seal verification
- **Model:** `jev-1.13.0` in all 90 requests and all 90 responses.
- **Transport:** the frozen historical policy (stdlib `http.client.HTTPSConnection`, 20 s per
  attempt, transport-only retries, none used).
- **Environment:** Python 3.13.5, numpy 2.4.4, scipy 1.17.0, scikit-learn 1.8.0, duckdb 1.4.3,
  OpenSSL 3.0.16. All match the F₁ pins.
- **Seals and artifacts:** the A2 seal chain (addendum and its F₁ configuration, protocol and
  Amendment 2 references) and the `l2_year` template were verified. The step-1, step-2 and L1
  artifacts were verified by SHA-256 before the run. Protocol, configuration and templates are
  unchanged since the A2 seal (`22060e5`).
- **API key:** read only at send time. A byte scan found it in no worktree file after the run.

## 8. Tests
- `tests/jev_nms_1` now includes the L2 decision-rule tests: the exact binomial p-value and
  threshold, the stop-for-ruling cases (invalid response, tie, disagreement between choice and
  arg-max), and validation of the year classes. Together with `tests/market`,
  `test_market_session_cas.py` and `test_cas_rules.py`: **219 passed, 1 skipped, 0 failed,
  no warnings.**
- The skip is the empirical CSMP calendar conformance test; that store is absent from this
  worktree.

## 9. Git
- Branch: `research/jev-nifty-market-state`.
- The L2 code (`l2.py`, the `validate_response` class-set parameter, tests) was committed at
  `6ca9fcd` (parent `0762cfc`) **before** the run.
- The L2 artifacts, the ledger and this report are committed together in the next commit.

## 10. Stages not performed
**No L3, development, prospective or other Jev call was performed.** No fitting, no pool and no
ΔLL. Jev calls under JEV-NMS-1 to date: S0 10 plus L2 90, for a total of 100.
