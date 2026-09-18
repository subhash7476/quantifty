# JEV-NMS-1 — Amendment-2 Freeze Record (A2 seal)

**JEV-NMS-1 IS RE-FROZEN under Amendment 2.** This is a **new seal event**. It does not
replace or modify the F₁ freeze.

| Item | Value |
|---|---|
| F₁ (protocol freeze date) | **2026-09-18**, unchanged |
| A2 seal timestamp | 2026-09-18T11:13:09Z (16:43:09 IST) |
| Branch | `research/jev-nifty-market-state` |
| F₁ sealed commit | `1d199cb5b51f8e15a82306da28f9bf2da40caa1d` |
| F₁ freeze-record commit | `8d13bac1a79dfe4e8c15bd7d45820311605c408f` |
| Platform calendar merged into branch | `a3107a32444a8cfcfbf8e2a25b78b3e3da33c436` (merges `main` @ `8696a83`) |
| Amendment 2 + configuration addendum commit | `65c31dbf0d54f8b7e0fef2f7dbb479cca99ec309` |
| This record | committed on top of `65c31db` |

## Authoritative sealed set

The amended protocol is the **F₁ protocol + Amendment 2**. The authoritative configuration is
the **F₁ configuration + the Amendment-2 addendum**.

### Unchanged F₁ artifacts: byte-identical to F₁ (verified against `8d13bac` and HEAD)

| Artifact | File | SHA-256 |
|---|---|---|
| Protocol | `docs/reports/jev/JEV_NMS_1_PROTOCOL.md` | `7e7f848d1f1664a34213dad8cb84c0e98a72833e621f719e64007a6f3af036a3` |
| F₁ configuration | `governance/jev_nms_1/config.json` | `9ed5dcaec115a93afbbc6d0edb51295efeea2966fe1fb49701d3aec59f967fee` |
| Template h = 5 | `governance/jev_nms_1/templates/h5.json` | `f934648150c5e304c0414d0e0e296a9b5614d089d5fcf80db1d420ba84a8dd07` |
| Template h = 15 | `governance/jev_nms_1/templates/h15.json` | `9105c0f99e5697ccb8b7e7b907197f85c8ab3098b7e43ab963fc1acf7d5e6a12` |
| Template h = 30 | `governance/jev_nms_1/templates/h30.json` | `4d9055e480ac69a065a316fe1fc8aff0db66a3d73acc9297ef4fe2488c91a4c7` |
| Template L2 | `governance/jev_nms_1/templates/l2_year.json` | `e94e351bbb93da701ad3d3046d5a63337c068f565b25aa0d74c90efa9f5804d0` |
| Environment | `governance/jev_nms_1/environment.json` | `7d86acb5ca263f9e16a246937381be8d7db37782273edbde7e21e3917584ca62` |
| Requirements | `governance/jev_nms_1/requirements-jev.txt` | `64b00470a3f8391255e7385682057cf86fc9ba8ec7e57d70448b867b4bb18655` |
| F₁ freeze record | `docs/reports/jev/JEV_NMS_1_F1_FREEZE_RECORD.md` | `d051b53859d4fc43394a61a6c2bfadc806beec96c4e8a766d83f0a96cd252bda` |

### New A2 artifacts

| Artifact | File | SHA-256 |
|---|---|---|
| Amendment 2 | `docs/reports/jev/JEV_NMS_1_AMENDMENT_2.md` | `2731a6254521520034e97fc542fa2253cc1a92713fed170cd46d0a58fbde40ae` |
| Amendment-2 configuration addendum | `governance/jev_nms_1/config_amendment_2.json` | `b9640bf22d2f1d53ca913654863280fa54087db00c2cd26675c1343ca9395484` |

The addendum references by SHA-256 the F₁ configuration (`9ed5dcae…`), the protocol
(`7e7f848d…`) and Amendment 2 (`2731a625…`). Every sealed path carries `-text` git
attributes, so the committed blob bytes equal the hashed bytes.

### Platform calendar dependency (recorded, not sealed; committed blob SHA-256 at `65c31db`)

| Module | SHA-256 |
|---|---|
| `core/market/nse_holidays.py` | `b6c8c57c2fd910bca3d59353a1ec2c4ef32edd3f74aefa9590ed26a341c71893` |
| `core/market/session_schedule.py` | `c1c8ca447f64f77abe546dbb03fb981b1ca83864e4ea018a1e3e986e822f7977` |
| `core/market/bar_labeling.py` | `6db7317c04d8e72736df6c371861dc76a9606e83323b91d60830bd3a9776fd1f` |
| `core/market/trading_calendar.py` | `58ba39dae0948ff55d4e8c5ee9be22711781159c287836cffaf3d63068bbe36e` |

Source commits: `b5620cd2190163474ec4103b23fb728da3ef914e`,
`02d1c87ac10fd41a8c65dd2237a9b43d651d9d6f` and `8696a830790b754ffb690028ddce3eaede7dafcd`.
Extending calendar coverage (e.g. 2027) is a platform-data change and does not amend the
protocol (Amendment 2 §A2-7).

## Pinned environment
Unchanged from F₁ (Amendment 2 §A2-10):
- Python 3.13.5;
- numpy 2.4.4, pandas 2.3.3, scikit-learn 1.8.0, scipy 1.17.0, duckdb 1.4.3;
- OpenSSL 3.0.16;
- stdlib `http.client.HTTPSConnection`, with the TypeSafe SDK not installed;
- `POST https://api.typesafe.ai/v1/systemone` (v1), model `jev-1.13.0`, 20 s per attempt,
  transport-only retries.

## Boundaries: unchanged
- H-exposed: 2026-01-01 → last session dated ≤ 2026-09-18.
- Buffer: sessions dated > 2026-09-18 and ≤ F₂ (F₂ not yet set).
- P: first eligible session dated > F₂.

## What Amendment 2 resolves
The documented reproducibility ambiguities:
- G-1 draw procedures (including the C-2 L3 pool and the L2/development overlap ruling);
- G-2 B2 per-horizon C;
- G-3 S0/L3 template (C-1);
- G-4 quantile method, for all quantiles (C-3);
- G-5, closed without amendment;
- G-6 previous-session semantics and the calendar dependency contract;
- the §10/§23 L2 population;
- the 2023-03-01 disclosure correction.

It also records the H-exposed item-8 audit: 177 sessions, one failure, 2026-02-02, whose
previous session 2026-02-01 has no Nifty 50 bars.

## State at the A2 seal
- **No Jev calls have been made under JEV-NMS-1.** No S0, L1, L2, L3, L5 or development call.
- **No eligibility has been constructed, no draw made, and no D-fit fitting performed**:
  no scales, thresholds, B0–B3 or pool. No development analysis has occurred.
- The H-exposed item-8 audit is a read-only diagnostic, not an eligibility artifact.
- All original F₁ artifacts remain immutable.

## Rules carried forward
- Implementation may implement the amended protocol but may not alter it. Any ambiguity
  found during implementation stops work and returns to the operator.
- Any change to the protocol, Amendment 2, the F₁ configuration, the A2 addendum or a
  template requires a new formal amendment and a new seal. After the first Jev call, none is
  permitted (§26, §28).
- Next: §28 step 2 sequence (eligibility → draws → D-fit scales/thresholds → B0–B3 → persist
  and hash → verify), then S0 → L1/L2/L3 → development. **Not started.**
