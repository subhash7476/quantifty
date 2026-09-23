# JEV-NMS-1 — L3 Report (repeatability probe and canary baseline)

**Final gate status: L3 COMPLETED. The canary baseline figure NEEDS AN OPERATOR RULING.**
- All 100 requests (50 states × 2 replicates) were valid, with 0 retries.
- §13 sets no pass/fail rule for L3, and no halt condition can be evaluated at L3 (§1).
- **Canary subset (D6, first 20 states):** argmax agreement 20/20 (1.00). The tie below does
  not affect it.
- **All 50 states:** argmax agreement **46/50 (0.92) or 47/50 (0.94)**. The value depends on
  how an exact argmax tie in one replicate-1 response is read (§4.3). The run pre-declared that
  a tie withholds the figure for a ruling.
- **Maximum absolute probability difference:** 0.14 over all 50 states, and 0.08 over the
  canary subset.

Development and P are **not** authorized by this report; each awaits separate operator
approval.

## 1. Preregistered rule
§13, sealed at F₁:

> "L3 repeatability: 50 states each sent twice (bypass). Report argmax agreement and maximum
> absolute probability difference. Replicate 0 is authoritative. L3 agreement is the canary
> baseline."
>
> "L5 drift canary: the first 20 L3 states in seed order, replayed (bypass) at the start of P
> and after every 60 prospective sessions; agreement = argmax agreement with their L3
> replicate-0 responses. Halt (INVALID) if agreement falls more than 10 percentage points
> below the L3 baseline."

A2-4 fixes the rest: the h15 template; D5 as 50 individual states, each sent twice; replicate
0 authoritative; replicate 1 a non-authoritative cache-bypass record under
`canonical_request_hash + run_id + replicate_index` (§12); canaries = the first 20 L3 states
in seed order (D6), unchanged.

**How the rule was applied:**
- **L3 is report-only.** §13 prescribes two figures and no threshold. No acceptance criterion
  was added.
- **The canary halt is L5's rule, not L3's.** It compares a later P-time replay against this
  baseline (§24 rule 9, §26 "Canary halt (L5)"). L3 *establishes* the baseline, so it has
  nothing to compare against. **No canary halt condition exists or was evaluated at L3**, and
  none was constructed.
- **§26 conditions that could apply now were checked:**

  | Condition | Status |
  |---|---|
  | Model identifier | `jev-1.13.0` on all 100 |
  | Request/response identifier mismatch | none |
  | Cache loss | none |
  | Invalid responses | 0 of 100 |

  None was met.

## 2. D5 sample and draw provenance
- **Source:** `draws_step2.json` (SHA-256 `e4c1f3c9…733de8`), verified before use. There was
  no redraw: the frozen manifest was checked against its A2-1 population, which was recomputed
  from `eligibility_step1.json` (`b5d1cd48…`).

| Check | Value |
|---|---|
| Eligible states in D-fit ∪ D-eval (685 sessions × 10 slots) | 6,850 |
| Excluded: S0 (D3) states | 10 |
| Excluded: L2 (D4t) states | 90 |
| Excluded: development states (D1 sessions × 10 slots) | 1,000 |
| Overlaps inside the exclusion set | S0 ∩ L2 = 1; L2 ∩ development = 30; S0 ∩ development = 0 |
| Excluded total (10 + 90 + 1,000 − 1 − 30) | **1,069** (matches the manifest) |
| L3 population | **5,781**. Population SHA-256 `d9cada9dc75c42be…` matches the manifest. |
| D5 output | 50 distinct states, all in the population, none in S0, L2 or development |
| D6 canaries | Equal to the first 20 of D5 in seed order |

**Every state before sending:**
- passed the L1 fence for stage L3 (active set D-fit ∪ D-eval, eligible sessions only);
- passed the request audit: the nine features were rebuilt from the SHA-256-checked store and
  equalled the sealed `features_step2.json` values;
- was checked against the sealed h15 template (`9105c0f9…`).

The 50 payloads are the same ones L1 audited.

**D5 in seed order** (entries 1–20 are the D6 canaries):

| # | State | # | State | # | State | # | State | # | State |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2025-08-18 13:30 | 11 | 2023-06-22 10:00 | 21 | 2023-04-10 11:00 | 31 | 2024-02-15 10:00 | 41 | 2023-07-11 12:30 |
| 2 | 2023-07-21 10:00 | 12 | 2025-05-20 13:00 | 22 | 2025-03-06 13:00 | 32 | 2023-03-13 11:30 | 42 | 2023-06-28 13:30 |
| 3 | 2023-04-05 14:30 | 13 | 2024-08-16 10:30 | 23 | 2023-11-06 13:00 | 33 | 2023-09-15 14:00 | 43 | 2024-06-26 11:00 |
| 4 | 2024-02-12 12:30 | 14 | 2023-04-17 14:00 | 24 | 2025-09-10 11:00 | 34 | 2025-12-16 14:00 | 44 | 2023-07-05 10:00 |
| 5 | 2024-01-04 10:30 | 15 | 2023-04-13 10:30 | 25 | 2025-12-22 12:00 | 35 | 2024-08-16 13:30 | 45 | 2024-05-30 14:30 |
| 6 | 2023-12-07 14:00 | 16 | 2023-06-30 12:30 | 26 | 2025-01-28 11:30 | 36 | 2024-05-07 13:00 | 46 | 2024-05-10 13:00 |
| 7 | 2023-08-24 11:30 | 17 | 2023-12-04 10:30 | 27 | 2024-08-13 10:30 | 37 | 2024-02-14 14:00 | 47 | 2025-06-17 12:00 |
| 8 | 2023-07-11 13:30 | 18 | 2023-12-19 14:00 | 28 | 2023-12-05 12:30 | 38 | 2023-09-12 11:30 | 48 | 2024-01-30 12:00 |
| 9 | 2025-11-10 11:00 | 19 | 2024-11-28 12:30 | 29 | 2024-09-17 14:00 | 39 | 2023-11-29 11:30 | 49 | 2023-05-02 12:30 |
| 10 | 2025-01-28 13:00 | 20 | 2025-06-12 10:00 | 30 | 2025-05-14 13:00 | 40 | 2024-05-02 13:00 | 50 | 2024-09-30 13:00 |

The same ordered list is in `draws_step2.json` (`d5_l3.output`) and `l3_step5.json`.

## 3. Requests and responses (50 × 2)

| Item | Value |
|---|---|
| Run ID | `L3-20260918T130620Z` |
| Send order | All 50 replicate-0 requests in seed order, then all 50 replicate-1 requests in seed order. The protocol does not fix the order; it was chosen before the run, so that replicate 0 is the first send of each state. |
| Scheduled / sent | 100 / 100 |
| Valid / invalid | **100 / 0** (schema-invalid 0, transport failures 0) |
| Attempts per request | 1 (**0 retries**) |
| HTTP status | 200 for all 100 |
| Model echoed | `jev-1.13.0` for all 100 |
| Probability vectors | Keys exactly the four §8 classes; all values in [0, 1]; maximum \|sum − 1\| = 1.1e-16 |
| `choice` vs arg-max | Agree on all 100 valid responses. On the one tie, `choice` is one of the tied classes. |
| Request IDs | 100 captured, all distinct (`x-typesafe-request-id`) |
| Usage | 788–798 input tokens, 55–56 output tokens per request |
| Sent / received | 2026-09-18T13:06:20.280Z → 13:06:57.828Z (UTC) |
| Latency | min 303.4 ms, median 357.7 ms, max 993.2 ms (the first request includes TLS setup) |
| Upstream (`x-envoy-upstream-service-time`) | min 43 ms, median 95.5 ms, max 592 ms |
| Keep-alive | One connection, reused for requests 2–100 |
| Timing validity | Not applicable (§11: historical call). Recorded in full per record. |

## 4. Replicate agreement

### 4.1 Figures

| Set | Pairs | Argmax agreements | Agreement | Max \|Δp\| |
|---|---|---|---|---|
| All 50 (D5) | 50 | 46 (47 under the tie reading in §4.3) | **0.92 (0.94)** | **0.14** |
| Canary subset (D6, first 20) | 20 | 20 | **1.00** | 0.08 |

**Across all 50 pairs:**
- The median of the per-state maximum absolute difference is 0.04.
- **No pair had identical probability vectors.** Every state's replicates differed in at least
  one class.
- Replicate-0 maximum class probability: min 0.34, median 0.53, max 0.88.

### 4.2 Disagreeing pairs
| Seed # | State | Replicate 0 arg-max | Replicate 1 arg-max | Max \|Δp\| |
|---|---|---|---|---|
| 22 | 2025-03-06 13:00 | range_bound | trending_up | 0.07 |
| 37 | 2024-02-14 14:00 | trending_down | range_bound | 0.05 |
| 40 | 2024-05-02 13:00 | trending_down | range_bound | 0.05 |
| 49 | 2023-05-02 12:30 | range_bound | **tie**: trending_down = range_bound = 0.42 | 0.07 |

None of the 20 canaries is among them.

### 4.3 The tie — ruling needed
**State 2023-05-02 12:30, replicate 1:**

| Class | Probability |
|---|---|
| trending_up | 0.06 |
| trending_down | **0.42** |
| range_bound | **0.42** |
| disorderly | 0.10 |

- Its `choice` is `trending_down`.
- Replicate 0 for the same state: range_bound 0.49, trending_down 0.35, trending_up 0.06,
  disorderly 0.10; `choice` range_bound.

**Consequences of each reading:**
- **(a) Replicate 1's answer is `choice`, or the first maximum in fixed class order:**
  `trending_down`. The pair disagrees, giving **46/50 = 0.92**. This is the value the code
  computed.
- **(b) A tie is counted as agreeing when replicate 0's arg-max is among the tied classes:**
  **47/50 = 0.94**.
- **(c) Tied pairs are excluded:** 46/49 = 0.939.

The protocol does not define arg-max under ties. As in L2, the run was set to flag any tie
rather than resolve it, so `needs_ruling` is true. The maximum absolute difference (0.14) and
the canary-subset figures (20/20, 0.08) do not depend on this ruling.

### 4.4 Second open question for P (not resolved here)
§13 names the "L3 agreement" as the baseline. Read plainly, that is the 50-state figure. L5,
however, replays only the 20 canaries. The two L3 figures differ: 1.00 on the canaries, and
0.92 or 0.94 on all 50. So the L5 halt threshold (baseline − 10 pp) is 0.90 on one reading
and 0.82 or 0.84 on the other. **Both figures are recorded.** The choice matters only at P,
and is left to the operator before F₂.

`l3_step5.json` holds the D6 baseline record: for each of the 20 canary states, the
replicate-0 arg-max, the full probability vector and the record ID.

## 5. Invalid, retry, timing and cache details
- **Invalid:** 0 of 100. L4 (≤ 2%) is not breached under either denominator: 0/100 for L3
  alone, and 0/200 cumulative (S0 10 + L2 90 + L3 100).
- **Retries:** none. Transport outcomes: 100 HTTP 200.
- **Cache (append-only):** `cache.jsonl` grew from 100 to **200** records under 200 distinct
  identifiers. Its diff against the committed L2 state is 100 insertions and 0 deletions.

| | Replicate 0 (50 records) | Replicate 1 (50 records) |
|---|---|---|
| `key` | The canonical request SHA-256 | `canonical_request_hash + run_id + replicate_index`, written literally as `<sha256>+L3-20260918T130620Z+1` |
| `authoritative` | true | false |
| `cache` | `miss_sent` (the key was new) | `bypass` |

  Every record also stores:
  - `request_sha256`, `replicate`, `run_id`;
  - the exact request bytes;
  - `state_as_of`;
  - per-attempt `request_sent_at`, `response_received_at`, latency, request ID, upstream time
    and safe headers;
  - the raw response and the validity parse.

  Replicate 0 and replicate 1 of each state have identical request bytes.
- **Guard:** before the ledger entry, all 100 record IDs were checked against the existing
  cache (the 100 S0 and L2 keys). None collided, and no cached key was re-sent.
- **First state:** 2025-08-18 13:30. Its canonical SHA-256 is
  `1cbfe8e222b227dfc09b0f101f0011fdf772ccbfbd0a3801d2d3dd526a9a06c1`.

## 6. Hashes
All data paths are relative to `data/jev_market_state/`.

| Artifact | SHA-256 |
|---|---|
| `l3_step5.json` (L3 run record: summary, pool check, figures, all 100 records) | `cb67b5551371ce5d85c4085cff004c0a70b557d411654f309605f0a90fc72c35` |
| `cache.jsonl` before L3 (100 records) | `4c2a4889a25b790a531efa4b20428e1169a3f9745d2bc1213631a1a4ae06bf47` |
| `cache.jsonl` after L3 (200 records) | `23b0bcdf1c7ffddd6350baab0770d3537948927b56045facaaaf0c23ee82e143` |
| `ledger.jsonl` before L3 (through `l2_report`) | `e425e6793735cdffc17c3b3f92d3092ac893a18d20965a97549c5d0da3fece83` |
| `ledger.jsonl` through `l3_completed` | `37587071b4228ed145c1f995485add6df726c19f19ec01a9d0203b6c7b014ba6` |

**Ledger events:**
- `l3_started` was written **before** the first send. It carries the run ID, template, model,
  transport ID, send order, and all 100 planned (state, replicate, record ID) triples.
- `l3_completed` was written after. It carries the artifact SHA-256, the valid count,
  `needs_ruling` = true, and three figures: 50-state agreement 0.92, canary agreement 1.00,
  and maximum \|Δp\| 0.14.

**Self-hash convention:** as for S0, L1 and L2, this report's SHA-256 is recorded in a
following `l3_report` ledger event. The final ledger hash is reported with the commit.

## 7. Seal, model and environment verification
- **Seals:**
  - The A2 seal chain was verified by `load_seal()`.
  - Configuration: `9ed5dcae…`, unchanged.
  - Addendum: `b9640bf2…`, unchanged.
  - h15 template: `9105c0f9…`, unchanged.
  - `git diff 22060e5..HEAD` over `governance/` and the protocol, Amendment 2 and freeze
    records is empty.
- **Artifacts:** the step-1, step-2, L1 and L2 artifacts were verified by SHA-256 before the
  run. The run proceeded only because L1 had passed and L2 was PASS.
- **Model:** `jev-1.13.0` in all 100 requests and all 100 responses.
- **Transport:** the frozen historical policy (stdlib `http.client.HTTPSConnection`, 20 s per
  attempt, transport-only retries, none used).
- **Environment:** Python 3.13.5, numpy 2.4.4, pandas 2.3.3, scikit-learn 1.8.0, scipy 1.17.0,
  duckdb 1.4.3, OpenSSL 3.0.16, with `OMP_NUM_THREADS=1`. All match the F₁ pins.
- **API key:** read only at send time. A byte scan found it in no worktree file after the run.

## 8. Tests and git
- **Tests:** `tests/jev_nms_1/test_l3.py` (8 tests) covers:
  - replicate-0 and replicate-1 record keying;
  - agreement and maximum \|Δp\| over all 50 and over the canary subset;
  - canary order;
  - exclusion of invalid responses, and the ruling flag;
  - the tie flag;
  - the absence of any pass/fail result;
  - verification of the frozen D5 pool;
  - refusal of a D5 output that overlaps L2.

  Full suite (`tests/jev_nms_1`, `tests/market`, `test_market_session_cas.py`,
  `test_cas_rules.py`, `-W error`): **227 passed, 1 skipped, 0 failed**. The skip is the CSMP
  calendar conformance test, whose store is absent from this worktree.
- **Branch:** `research/jev-nifty-market-state`.
- **L3 code** (`l3.py`, `test_l3.py`) was committed at `32b8244` (parent `e5e0ccc`) **before**
  any call.
- **L3 artifact, cache, ledger and this report** are committed together in the next commit.

## 9. Stages not performed
**No development, prospective (P), L5 or other Jev call was performed.** No fitting, no pool
and no ΔLL.

Jev calls under JEV-NMS-1 to date:

| Stage | Calls |
|---|---|
| S0 | 10 |
| L2 | 90 |
| L3 | 100 |
| **Total** | **200** |
