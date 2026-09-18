# JEV-NMS-1 — S0 Report (preregistered structural probe)

**Final gate status: S0 COMPLETE.** All 10 scheduled requests returned a valid response under
the frozen rules. L1 is **not** authorized by this report; it awaits separate operator approval.

## 1. Purpose
S0 is the preregistered unscored smoke test of protocol §23, with the §11A item 9 restriction
that outputs are checked for parsing only. It exercises the frozen payload construction,
transport, caching, validation and ledger path end to end, on 10 real states.

**S0 is not predictive evidence.** Its responses are not used for B2/B3 fitting, pool fitting,
ΔLL evaluation or any development statistic, and they are not examined for accuracy.

## 2. Experiment ID and provenance
| Item | Value |
|---|---|
| Experiment | JEV-NMS-1 |
| F₁ | 2026-09-18 (unchanged) |
| A2 freeze record commit | `22060e5f2cb41618ed3542527f1650c99baa4f3b` |
| Amendment 2 / addendum commit | `65c31dbf0d54f8b7e0fef2f7dbb479cca99ec309` |
| §28 steps 1–2 accepted at | `0ebcea4cfedf9f2328fa22f020356e6e041b819d` |
| S0 code commit (committed before any call) | `d3c01a27fd654fd56736c59f35009ee57987d74d` |
| S0 artifacts + this report | the commit that adds this file (child of `d3c01a2`) |
| Protocol SHA-256 | `7e7f848d1f1664a34213dad8cb84c0e98a72833e621f719e64007a6f3af036a3` |
| F₁ configuration SHA-256 | `9ed5dcaec115a93afbbc6d0edb51295efeea2966fe1fb49701d3aec59f967fee` |
| Amendment 2 SHA-256 | `2731a6254521520034e97fc542fa2253cc1a92713fed170cd46d0a58fbde40ae` |
| A2 configuration addendum SHA-256 | `b9640bf22d2f1d53ca913654863280fa54087db00c2cd26675c1343ca9395484` |
| h15 template SHA-256 | `9105c0f99e5697ccb8b7e7b907197f85c8ab3098b7e43ab963fc1acf7d5e6a12` |
| Model identifier | `jev-1.13.0` (sent in every body, echoed in every response) |
| Transport | stdlib `http.client.HTTPSConnection`, keep-alive, `POST https://api.typesafe.ai/v1/systemone`, 20 s per attempt, historical retry policy |
| Transport configuration identifier | `41834de153ba4dd8…` (SHA-256 of the sealed `config.json` transport block) |
| Environment | Python 3.13.5, numpy 2.4.4, pandas 2.3.3, scikit-learn 1.8.0, scipy 1.17.0, duckdb 1.4.3, OpenSSL 3.0.16. All match the F₁ pins. |
| Run ID | `S0-20260918T123303Z` |

## 3. S0 sample
The sample is the preregistered draw D3 (`draws_step2.json`, SHA-256 `e4c1f3c9…33de8`): 5
eligible D-fit sessions, each at 10:00 and 14:30, for **10 scheduled requests**, all on the
sealed **h15** template (A2-4).

| Session | Timestamps |
|---|---|
| 2023-03-22 | 10:00, 14:30 |
| 2023-05-31 | 10:00, 14:30 |
| 2023-09-28 | 10:00, 14:30 |
| 2024-07-11 | 10:00, 14:30 |
| 2024-09-25 | 10:00, 14:30 |

**Payloads.** They come from `features_step2.json` (SHA-256 `29997617…049eb3`), built under
ruling Q1 and serialized per §12a.

**Pre-send request audit.** Each state's nine features were rebuilt from its own session file
(bars stamped ≤ t−1, SHA-256-checked against step 1) plus the recorded C_prev. All ten matched
the sealed features field by field. The seal, template and artifact hashes were also verified
before any send.

## 4. Request details
Every request succeeded on its first attempt (attempts = 1, retries = 0), with HTTP status 200.
The cache status of every request was *miss → sent*, and each response was stored as
authoritative. Timestamps are UTC on 2026-09-18.

| # | State | Request SHA-256 (cache key) | Request ID | Sent at | Received at | Latency ms | Upstream ms | Keep-alive reused |
|---|---|---|---|---|---|---|---|---|
| 1 | 2023-03-22 10:00 | `5be1980163ee8965f751b141e7467b5efe524c99fa0986e2551c77b31b7003ec` | `req_01a0b4818e327eebaad7061b0b9d9a64` | 12:33:03.513 | 12:33:04.484 | 970.7 | 79 | no (first) |
| 2 | 2023-03-22 14:30 | `a224d21c75929855810d8212f936c6f100f0b4ebafc3054167f91d540e733f14` | `req_01a0b4818f8775558bc56bceeaf9a8f0` | 12:33:04.485 | 12:33:04.834 | 349.0 | 81 | yes |
| 3 | 2023-05-31 10:00 | `d41653db8e5a1d31ce137ce6d4f312d6073847bc20e6e0feaca2a4a245405275` | `req_01a0b48190ee7098ba8f265e636a9141` | 12:33:04.834 | 12:33:05.245 | 411.3 | 149 | yes |
| 4 | 2023-05-31 14:30 | `7b6079f23eb29c18b54d6c87b14ed94d22d9712c21596c349b3512c06b756fd1` | `req_01a0b4819281799ba0578f1d8ae283b4` | 12:33:05.246 | 12:33:05.599 | 352.9 | 90 | yes |
| 5 | 2023-09-28 10:00 | `15982d054ba360c6f63c2bf54127c245f0b9bdb29c93037da562f53b4e874965` | `req_01a0b48193e371a3b2c43abdd6fd759a` | 12:33:05.599 | 12:33:05.953 | 354.0 | 91 | yes |
| 6 | 2023-09-28 14:30 | `cc006fab29f1a60e354860698a4123296821b5add4df44b0d161a6f8c42ef82e` | `req_01a0b48195457bc691ce8508521f2b0c` | 12:33:05.954 | 12:33:06.280 | 325.3 | 61 | yes |
| 7 | 2024-07-11 10:00 | `b1455e1a23fae950c539ef600daa0bd402fb88d8a0f2d91876757c1b8ceab6cf` | `req_01a0b481968b7aba8d5e0a8ac4f142ca` | 12:33:06.280 | 12:33:06.678 | 397.5 | 135 | yes |
| 8 | 2024-07-11 14:30 | `7bdbbca1c0a0c8790bb41aea3667ad950c71b42da1f71fd01aa515f1f534e84e` | `req_01a0b481981a775597038e7ad16df0c1` | 12:33:06.678 | 12:33:07.067 | 388.9 | 118 | yes |
| 9 | 2024-09-25 10:00 | `d817e52e1cab2cd15e0b451c250596ae57b5a22dae96faa75d7442c181f2432d` | `req_01a0b481999f709599067d6f50102e18` | 12:33:07.067 | 12:33:07.465 | 398.0 | 136 | yes |
| 10 | 2024-09-25 14:30 | `f6652a8f3c50e94e947722ae4fee2dcaa0d49eee9c170d29b18e598940419a62` | `req_01a0b4819b2d79358fb6b0159ac8e510` | 12:33:07.466 | 12:33:07.825 | 358.6 | 97 | yes |

**Latency.** Request 1 includes the TLS connection setup. Requests 2–10 took 325–411 ms
(upstream 61–149 ms).

**`state_as_of`.** The last included bar is 09:59 for 10:00 states and 14:29 for 14:30 states.
The payload build time is recorded per request in the cache.

## 5. Response details
Probabilities are listed in the frozen class order (trending_up, trending_down, range_bound,
disorderly) and were mapped **by class name**; the API returns them keyed by name.

| # | State | Choice | P(up) | P(down) | P(range) | P(disorderly) | Max prob (§21 confidence) | API `confidence` field | Usage (input / output tokens) | Schema |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2023-03-22 10:00 | trending_down | 0.01 | 0.66 | 0.20 | 0.13 | 0.66 | 0.54 | 794 / 56 | valid |
| 2 | 2023-03-22 14:30 | trending_down | 0.01 | 0.63 | 0.31 | 0.05 | 0.63 | 0.49 | 795 / 56 | valid |
| 3 | 2023-05-31 10:00 | trending_down | 0.00 | 0.69 | 0.22 | 0.09 | 0.69 | 0.58 | 795 / 56 | valid |
| 4 | 2023-05-31 14:30 | range_bound | 0.19 | 0.13 | 0.52 | 0.16 | 0.52 | 0.36 | 793 / 55 | valid |
| 5 | 2023-09-28 10:00 | trending_down | 0.01 | 0.65 | 0.17 | 0.17 | 0.65 | 0.54 | 796 / 56 | valid |
| 6 | 2023-09-28 14:30 | trending_down | 0.01 | 0.70 | 0.23 | 0.06 | 0.70 | 0.59 | 797 / 56 | valid |
| 7 | 2024-07-11 10:00 | range_bound | 0.01 | 0.10 | 0.57 | 0.32 | 0.57 | 0.44 | 793 / 55 | valid |
| 8 | 2024-07-11 14:30 | range_bound | 0.06 | 0.04 | 0.75 | 0.15 | 0.75 | 0.67 | 792 / 55 | valid |
| 9 | 2024-09-25 10:00 | range_bound | 0.17 | 0.07 | 0.65 | 0.11 | 0.65 | 0.53 | 790 / 55 | valid |
| 10 | 2024-09-25 14:30 | range_bound | 0.04 | 0.19 | 0.62 | 0.15 | 0.62 | 0.49 | 791 / 55 | valid |

**Response structure.**
- Top-level keys: `answers`, `model`, `usage`.
- `answers.market_state` keys: `choice`, `confidence`, `probabilities`, `type`.
- Every probability vector sums to exactly 1.0, and the choice equals the arg-max in all 10.

**[D] Confidence field.** The API's `confidence` field is **not** the maximum probability. The
protocol does not use it: §21 defines confidence as "max of J's four class probabilities" and
requests no separate abstention judgment. It is recorded here and in the cache for provenance
only.

**[D] Zero probabilities.** Probabilities are returned to 2 decimals, and one is 0.0
(request 3, trending_up). §15 clips J at ≥ 1e-4 and renormalizes when J is used. S0 uses no J.

## 6. Validity
| Classification | Count |
|---|---|
| Scheduled | 10 |
| Sent | 10 |
| Valid | **10** |
| Invalid (total) | 0 |
| Schema-invalid (HTTP 200 failing validation) | 0 |
| Transport failures (no HTTP 200 after the retry policy) | 0 |
| Retries | 0 |
| Timing-invalid | 0 (not applicable to S0 — see below) |

**Timing.** The §11 t+15 s / t+60 s timing-validity rule applies to prospective (P)
observations only. §11 classes S0 as a historical, after-the-fact call. Timing was nonetheless
recorded in full for every call.

**Validity rule applied (frozen items only).** A response is valid when all of the following
hold:
1. the HTTP status is 200 and the body parses;
2. `model` equals `jev-1.13.0`;
3. `answers.market_state` exists;
4. the probabilities have exactly the four frozen class names, each a finite number in [0, 1];
5. the choice is one of the four classes.

The frozen text sets no tolerance on the probability sum. The run was set to stop for a ruling
if any sum differed from 1 by more than 1e-6. The maximum observed deviation was 0.0.

## 7. Integrity checks
| Check | Result |
|---|---|
| Model identifier | `jev-1.13.0` in all 10 requests and all 10 responses |
| Class mapping | By class name into the frozen order. The response class set equals the four frozen classes in all 10. |
| Probability validity | All in [0, 1] and finite. All sums exactly 1.0. |
| Payload hashes | The cache key is the SHA-256 of the exact transmitted bytes, recorded per request. The 10 keys are distinct. The request audit matched all 10 payloads. |
| Cache and key behaviour | Append-only `cache.jsonl`, 10 lines, 10 distinct keys. No key existed before the run, so none was re-sent. No bypass records (bypass is permitted only for L3 and L5). |
| Retry behaviour | 0 retries. The policy is enforced in code and tested: only on connection error, timeout, 429 or 5xx; at most 3 retries at 2/4/8 s; never after a 200 or any other 4xx; identical bytes on every attempt. |
| Timing rules | 20 s per-attempt deadline. Maximum observed latency 970.7 ms. P-only timing validity not applicable. |
| API key | Read from `TYPESAFE_API_KEY` at send time and used only in the Authorization header. A byte scan of every worktree file after the run found it in **no** file. `set-cookie`, `cookie` and `authorization` headers are excluded from stored response headers. |
| Append-only ledger | `s0_started`, listing the 10 planned request hashes, was written **before** the first send. `s0_completed` was written after, with the artifact hash. Earlier ledger lines are unchanged. |
| Seal integrity | Protocol, F₁ configuration, Amendment 2, addendum and templates are unchanged since the A2 seal. Step-1 and step-2 artifacts are unchanged. |

## 8. Interpretation boundary
- S0 responses are **diagnostic only**.
- **No predictive-performance conclusion** is drawn from them. They were not compared with
  labels and not scored.
- No response is used to modify the protocol, Amendment 2, the templates, the features, or any
  deterministic model (B0–B3 remain as frozen at `0ebcea4`).
- S0 does **not** constitute development evidence.

## 9. Artifacts
All paths are relative to `data/jev_market_state/`.

| Artifact | Role | SHA-256 |
|---|---|---|
| `s0_step3.json` | S0 run record: 10 request records and summary | `53113e5c0dc8805785963b01386e2b1c0628561a329ddba54480e35ae28cd308` |
| `cache.jsonl` | Append-only Jev cache: request bytes, raw response, validity, timing | `1a4e5bf5cf851b23b34846df1d6a6f32a87ac208426ab91787b6f14fa11f223f` |
| `ledger.jsonl` | Ledger at report finalization (through `s0_completed`) | `bb832cbc8e5e5adb05bcaee1b5340d9ba581e279c6db1a28fd77d8ae0e2ad97c` |

**Self-hash convention.** A file cannot contain its own SHA-256, so this report does not. Its
SHA-256 is written to the ledger as an `s0_report` event appended after this file was
finalized. That event changes the ledger's hash from the value in the table above; the final
ledger hash is reported with the commit.

## 10. Tests
- `tests/jev_nms_1` covers eligibility, draws, D-fit, features, models and transport. The
  transport tests cover canonical bytes, validation, the retry policy and API-key
  non-persistence, using a fake connection with no network.
- Together with `tests/market`, `tests/database/utils/test_market_session_cas.py` and
  `tests/execution/test_cas_rules.py`: **213 passed, 1 skipped, 0 failed, no warnings.**
- The skip is the empirical CSMP calendar conformance test; that store is absent from this
  worktree.

## 11. Git and reproducibility
- Branch: `research/jev-nifty-market-state`.
- The S0 code was committed at `d3c01a2` (parent `0ebcea4`) **before** the run.
- The run artifacts, the ledger and this report are committed together in the next commit.
- No unrelated file changed. The only non-S0 files touched since `0ebcea4` are the S0 code and
  tests in `d3c01a2`.

## 12. Final gate status
- **S0 COMPLETE** under the frozen rules: 10/10 valid, 0 invalid, 0 retries, and the model
  identifier was verified on every call.
- **L1 is NOT authorized.** It awaits separate operator approval.
- **No L1, L2, L3, development or prospective call was made.** No pool fit and no ΔLL scoring.
  The 10 S0 requests are the only Jev calls under JEV-NMS-1.
