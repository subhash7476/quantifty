# JEV-NMS-1 — Development Call Audit (read-only)

**Conclusion: VERIFIED on repository evidence.**
- The cache holds 1,600 development records.
- Each one is a distinct canonical request that the ledger pre-registered.
- Each carries a captured HTTP 200 response from `api.typesafe.ai`, with a distinct
  server-issued request ID.

**The dashboard discrepancy is not explained by anything in the repository.** It can only be
resolved on TypeSafe's side (§5).

**How the audit was done:**
- Performed 2026-09-18 at about 14:07 UTC.
- No network, API or TypeSafe call was made.
- No experiment artifact was modified. The cache, ledger, analysis artifact and reports are
  byte-identical to commit `90477d6`.
- Tooling added: `scripts/jev_nms_1/audit_dev_calls.py` (read-only) and
  `tests/jev_nms_1/test_audit_dev_calls.py`.

## 1. Counts and identity (items 1–3, 5, 6, 12)

| Check | Result |
|---|---|
| `cache.jsonl` records by stage | S0 10, L2 90, L3 100, **development 1,600** (total 1,800) |
| Development records by template | h15 1,000; h5 300; h30 300 |
| Distinct development request keys | **1,600** |
| Keys equal to the 1,600 keys of the `development_started` ledger event (written before the first send) | **Equal, in the same order** |
| Development keys shared with S0/L2/L3 | 0 |
| TypeSafe request IDs (`x-typesafe-request-id`) | **1,600 captured, 1,600 distinct**, 0 shared with S0/L2/L3 |
| Retries | **0**. Every record has exactly one attempt. |
| Run | All records carry run ID `DEV-20260918T134137Z`, `cache = miss_sent` and `authoritative = true` |

## 2. Per-record checks (items 4, 7)
Every one of the 1,600 records passes every check below; the failure list is empty.
- **Request bytes:** the SHA-256 of the stored request bytes equals both `key` and
  `request_sha256`.
- **Model in the request:** the request body's model is `jev-1.13.0`.
- **HTTP status:** outcome `http` with status 200.
- **Raw response:**
  - it is present and parses;
  - its `model` is `jev-1.13.0`;
  - its probabilities equal the stored parse.
- **Content-Length:** the header equals the raw body's byte length (1,600 of 1,600).
- **Headers:**
  - `server: istio-envoy`, a `date` header and `x-envoy-upstream-service-time` are present;
  - the request ID matches `req_` followed by 32 hex digits and equals the header value.
- **Validity:** `validity.valid = true`, and the model is `jev-1.13.0`.

## 3. Evidence that the responses are genuine captured API responses
- **The code path sends a real request on every cache miss** (item 11).
  - `dev.run()` builds the default `Transport()` when none is passed, and `main()` passes
    none.
  - `Transport` opens `http.client.HTTPSConnection("api.typesafe.ai", 443)` and POSTs
    `/v1/systemone`.
  - The only place a response record is written is after `send_historical`, which returns
    the server's status, headers and body.
  - There is no stub, mock or fabrication path in `scripts/jev_nms_1/`.
  - `dev.py`, `transport.py` and `dev_analysis.py` are unchanged since `4673e09`, which was
    committed before the run. `transport.py` is last modified at `6ca9fcd` (pre-L2), so S0,
    L2, L3 and development all used the same transport.
- **The run log records** `sent_this_invocation 1600`, `cache_hits_this_invocation 0`,
  `complete true`, `exit=0`.
- **Server-issued fields agree with local timing:**
  - Every server `Date` header falls within the local send/receive window, to the header's
    1-second resolution.
  - Each request ID's first 48 bits decode as a Unix-millisecond timestamp, which is the
    UUIDv7 layout, although TypeSafe does not document the format. The decoded time lies
    within 0.16 s of the local window for all 1,600.
  - Those decoded times are strictly monotonic in send order.
  - The same holds for S0 (12:33 UTC), L2 (12:50) and L3 (13:06), with skew ≤ 0.134 s.
- **Upstream timing and bodies:**
  - Upstream service times range from 43 to 542 ms, and per-request latency from 316 to
    1,319 ms. Sends span 13:41:37.893Z to 13:51:48.071Z, with gaps between consecutive sends
    of 0.316–1.32 s.
  - There are 1,599 distinct raw bodies. The one duplicated body is identical, including its
    token usage.
- **Usage returned by the API:** 1,269,200 input and 89,032 output tokens across the 1,600
  development calls. Across the 200 earlier S0/L2/L3 calls: 155,142 input and 10,707 output.
  So development is about 89% of the experiment's token usage.

## 4. Hashes and derived artifacts (items 8–10)

| Item | Recomputed | Recorded in | Match |
|---|---|---|---|
| `cache.jsonl` after development | `fd27d793be510a1998d80b4d9a556e67fd0256d134a1e7d84cec3fd6f6a839c9` | Development report §9; `development_calls_completed.cache_sha256`; `development_step6.json.cache_sha256` | yes, all three |
| Ledger through `a3_ruling` (before development) | `3c7d73f7ceb9aaec2dbe49a19629f33d77a77149f860c40efad0162975b411a0` | Development report §9 | yes |
| Ledger through `development_calls_completed` | `e3b00d211e002cc17dcee59f61786ae5482a05a83c5fb59dc601a9aae50c6a6d` | not listed in the report; computed here | n/a |
| Ledger through `development_completed` | `cad2f30fbc11142284d0f0760ac829702637d74c2e9ebcdb2a4efc4783d17a16` | Development report §9 | yes |
| Final ledger (through `development_report`) | `049045a2978811975c2d5040a3a070bf0fb5c36f68f332a1184c3532afb90b7a` | development chat return | yes |
| `development_step6.json` | `3fc16a452da9630dfeac95dd9616df21e56a32a5cd6b0963db01b17b3bdd669d` | Development report §9 | yes |

**`development_calls_completed`** records `records = 1600` and `valid = 1600`, with run ID
`DEV-20260918T134137Z`.

**Analysis references exactly these records:**
- `dev_analysis` reads each observation by the `development_started` key. It asserts the
  record's stage, state, template and authoritative flag.
- The artifact records the audited cache hash, and valid-observation counts of 1,000, 300 and
  300.
- Recomputed directly from the 1,600 cache records, Jev's log-loss equals the artifact's value
  at every horizon:

  | Horizon | Log-loss |
  |---|---|
  | h15 | 1.5348762376 |
  | h5 | 1.4946899265 |
  | h30 | 1.6973106415 |

## 5. The dashboard discrepancy
Nothing in the repository contradicts the 1,600 calls, and nothing local can prove how
TypeSafe accounts for them. Relevant facts:
- **Timing:** development ran 13:41:37–13:51:48 UTC. This audit ran about 16 minutes after
  the last call. Dashboard ingestion or aggregation lag cannot be ruled out, and would be the
  simplest explanation.
- **Earlier calls look the same:** S0, L2 and L3 were sent by the same transport code in the
  same session, and they show the same server-issued fields.
- **Key identity:** the API key is never logged, persisted or hashed (standing rule). Its
  identity cannot be compared across stages. If the dashboard is scoped to a different key,
  project or organization than the `TYPESAFE_API_KEY` in this session's environment, the
  calls would not appear there. This cannot be checked locally.
- **Units:** the dashboard may count tokens or billed units rather than requests. Development
  added about 1.27M input tokens, about 8.2× the earlier 155k.

**Resolving it:** the 1,600 request IDs, for example `req_01a0b4c05638733eaeb70792c9dbf03b`
(the first, 13:41:38 UTC), are stored in the cache. TypeSafe can match them against their
server logs. Contacting TypeSafe is outside this audit and was not done.

## 6. Tests
- `tests/jev_nms_1/test_audit_dev_calls.py`: 4 passed. They check counts and distinctness,
  hash agreement with the ledger and the report, server-field and local-timing agreement, and
  the request-ID time decoding.
- The full relevant suite was also run; see the commit message.

## 7. Conclusion
**VERIFIED (repository evidence).** All 12 audit items hold. The development records are real
captured HTTP responses from the frozen transport. They are not synthetic, not test-generated,
not copied from S0, L2 or L3, and not analysis artifacts. The Development NULL rests on
exactly these 1,600 records.

The TypeSafe dashboard discrepancy is **unexplained locally**. The operator may reconcile it
with TypeSafe using the stored request IDs before freezing.
