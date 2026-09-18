# JEV-NMS-1 — F₁ Freeze Record

**JEV-NMS-1 IS FROZEN.**

| Item | Value |
|---|---|
| F₁ (protocol freeze date) | **2026-09-18** |
| F₁ timestamp | 2026-09-18T08:11:05Z (13:41:05 IST) |
| Sealed commit | `1d199cb5b51f8e15a82306da28f9bf2da40caa1d` |
| Branch | `research/jev-nifty-market-state` (worktree from `main` @ `9b4e9a6`) |
| Configuration SHA-256 | `9ed5dcaec115a93afbbc6d0edb51295efeea2966fe1fb49701d3aec59f967fee` |
| Protocol document SHA-256 | `7e7f848d1f1664a34213dad8cb84c0e98a72833e621f719e64007a6f3af036a3` |

## Template SHA-256

| Template | File | SHA-256 |
|---|---|---|
| h = 5 | `governance/jev_nms_1/templates/h5.json` | `f934648150c5e304c0414d0e0e296a9b5614d089d5fcf80db1d420ba84a8dd07` |
| h = 15 (primary) | `governance/jev_nms_1/templates/h15.json` | `9105c0f99e5697ccb8b7e7b907197f85c8ab3098b7e43ab963fc1acf7d5e6a12` |
| h = 30 | `governance/jev_nms_1/templates/h30.json` | `4d9055e480ac69a065a316fe1fc8aff0db66a3d73acc9297ef4fe2488c91a4c7` |
| L2 year probe | `governance/jev_nms_1/templates/l2_year.json` | `e94e351bbb93da701ad3d3046d5a63337c068f565b25aa0d74c90efa9f5804d0` |

## Pinned environment

`governance/jev_nms_1/environment.json` — SHA-256 `7d86acb5ca263f9e16a246937381be8d7db37782273edbde7e21e3917584ca62`
`governance/jev_nms_1/requirements-jev.txt` — SHA-256 `64b00470a3f8391255e7385682057cf86fc9ba8ec7e57d70448b867b4bb18655`

Pinned: Python 3.13.5 (tags/v3.13.5:6cb20a2, MSC v.1943, AMD64) · numpy 2.4.4 · pandas 2.3.3 ·
scikit-learn 1.8.0 · scipy 1.17.0 · duckdb 1.4.3 · OpenSSL 3.0.16 (11 Feb 2025) · HTTP client
stdlib `http.client.HTTPSConnection` · TypeSafe SDK not installed.
Recorded, not pinned: Windows-11-10.0.22000-SP0, AMD64, `C:\Program Files\Python313\python.exe`,
git 2.51.2.windows.1.

Transport: `POST https://api.typesafe.ai/v1/systemone` (API v1), keep-alive, model
`jev-1.13.0`, 20 s per attempt, transport-only retries (P ≤ 1 and must start ≤ t+60 s;
historical ≤ 3 with 2/4/8 s back-off; never after HTTP 200 or other 4xx; identical bytes,
same key).

## Boundaries fixed by F₁

- H-exposed: 2026-01-01 → last session dated ≤ 2026-09-18.
- Buffer: sessions dated > 2026-09-18 and ≤ F₂ (F₂ not yet set).
- P: first eligible session dated > F₂.

## State at freeze

- **No Jev calls have been made under JEV-NMS-1.** No S0, no L1/L2/L3, no development scoring.
- The earlier infrastructure qualification probes (connectivity, repeatability, keep-alive
  latency) used synthetic states only and are not part of this experiment.
- Sealed files carry `-text` git attributes; the committed blob hashes equal the values above.
- Next: the §28 pre-Jev sequence (eligibility → draws → D-fit scales/thresholds → B0–B3 →
  persist and hash artifacts → verify), then S0 → L1/L2/L3 → development.
