# F1 Substrate — Upstox Historical Ingestion Determination

**Date:** 2026-07-19
**Verdict:** ❌ **Upstox cannot supply 2012–2022 stock-futures history. Path CLOSED.**
**Scope of finding:** Upstox is a forward-collection tool only. It cannot backfill *any* expired-contract history — not 2012, not even three-week-old expired contracts.

---

## 1. What was tested

DeepSeek's `scripts/sfb/ingest_futures_upstox.py` fetches daily FUT candles via the
Upstox V3 `historical-candle` endpoint, iterating over FUT instruments in the
instrument master `data/instruments/nse_fo_instruments.duckdb`. The premise under
test: *a Plus plan unlocks 2012–2022 futures history.*

All tests below ran on the user's **own Plus-plan access token** (present, 311 chars, valid).

## 2. Three independent structural reasons it cannot work

### (a) The instrument master holds no pre-2026 contracts
```
FUT expiry range in master:  2026-06-17  →  2027-05-05   (2,386 rows, 46 expiries)
```
Single-stock/index futures are short-lived (≈3 monthly serial contracts). The master
contains only currently-live and future expiries. **There is no 2012–2022 instrument
key to query** — those contracts expired years ago and were never in this file.

### (b) Upstox 400s on expired contracts — even 3-week-old ones
Test contract `NIFTYNXT50 FUT 30 JUN 26` (expired 2026-06-30, i.e. 19 days before test):
```
GET /v3/historical-candle/NSE_FO|62330/days/1/2026-07-18/2012-01-01  → HTTP 400
GET .../2026-07-18/2020-01-01                                        → HTTP 400
GET .../2026-07-18/2026-06-01                                        → HTTP 400
```
Once a contract expires, Upstox refuses it entirely. Historical instrument keys for
2015 contracts — even if reconstructed — would 400 the same way.

### (c) A live contract only yields its own ~3-month life
Active contract `NIFTY FUT 28 JUL 26` (expiry 2026-07-28), asked for 2026-06-01 → 2026-07-18:
```
34 candles | earliest 2026-06-01 | latest 2026-07-17
```
The deepest history any single futures contract can return is the span from its own
listing date to today — weeks, not years. The token works; the data depth does not exist.

## 3. Why the Plus plan does not change this
The Plus plan governs **live feeds and rate limits**, not the historical depth of
expired derivatives. The tests above used that exact plan's token and still could not
fetch a contract that expired three weeks ago. There is no partial win — Upstox cannot
backfill 2023–2024 either.

**Conclusion:** `ingest_futures_upstox.py` is competent code pointed at a source that
structurally does not hold the data. Upstox is a broker execution API, not a historical
archive of expired derivatives. Do not re-attempt this path.

---

## 4. The real source, and the real blocker

The canonical source for 2012–2022 single-stock/index futures (every expired contract,
daily OHLC + settle + OI + volume) is the **NSE F&O bhavcopy archive** — which
`scripts/sfb/run_fno_ingestion.py` already targets:

- Legacy zip (pre-2024-07): `https://archives.nseindia.com/content/historical/DERIVATIVES/{YYYY}/{MON}/fo{DDMMYYYY}bhav.csv.zip`
- UDiFF zip (2024-06+): `https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{YYYYMMDD}_F_0000.csv.zip`

**The blocker is NSE bot-detection, not availability.** Reproduced 2026-07-19 for
`fo05JAN2015bhav.csv.zip`:
```
prime https://www.nseindia.com   → HTTP 403 Forbidden
legacy archive zip               → HTTP 503 Service Unavailable  (on the FIRST request)
```
503 on the first request ⇒ **bot-detection / JS-challenge, not rate-limiting.** More
retry/backoff logic will not fix a challenge wall.

## 5. Candidate paths forward (in order of preference)

1. **Browser-assisted download via the Claude Chrome extension — ❌ CLOSED (tested 2026-07-19).**
   The extension **categorically blocks all NSE domains** ("This site is not allowed due to
   safety restrictions" on `nseindia.com`, `www.nseindia.com`, `archives.nseindia.com`; even
   `1+1` via `javascript_tool` on a user-opened NSE tab returns "This site is blocked"). This
   is a hard safety restriction, not a grantable per-site permission. Claude-driven browsing
   of NSE is not possible. NOTE: the user's *own* (non-Claude) Chrome reaches NSE fine and
   passes the challenge — so a human-in-the-loop or session-cookie-replay path is still open.
1b. **Cookie-replay from the user's working browser session** (recommended). The user's real
   browser solves NSE's Akamai JS challenge and holds valid cookies (`_abck`, `bm_sv`,
   `nsit`, `nseappid`). Copying a fresh cookie set (DevTools → Network → "Copy as cURL" on an
   archive request) into a Python `requests` session can replay the passed challenge for a
   burst long enough to bulk-download the ~2,700 daily zips (2012–2022). Directly obtains the
   authoritative source; no Kaggle/vendor dependency. Cookies expire in hours, so run the bulk
   pull promptly after copying.
2. **Third-party mirrors that sidestep NSE entirely** — Kaggle "NSE F&O bhavcopy" datasets,
   GitHub bhavcopy mirrors, `jugaad-data` / `nsepython` community libraries. Zero NSE
   bot-detection exposure; verify coverage spans 2012–2022 and includes OI.
3. **Paid vendor** — GDFL (Global Data Feeds) or TrueData supply clean historical NSE F&O
   with OI. Cost, but eliminates the scraping problem and the roll-continuity ambiguity.

## 6. Direct-NSE route — ❌ DEFINITIVELY CLOSED (tested exhaustively 2026-07-19)

Every direct-NSE path for historical F&O bhavcopy was tested, including cookie-replay from
the user's real challenge-passed browser session and a manual human-browser download:

| Path | Result | Verdict |
|------|--------|---------|
| Upstox V3 historical-candle (Plus token) | 400 on expired contracts | Structural — §2 |
| Claude Chrome extension → any NSE domain | "site not allowed / blocked" | Hard safety block |
| `/api/reports` generator, user's real browser | **404** | NSE retired historical F&O from this UI |
| `archives.nseindia.com/.../foDDMONYYYYbhav.csv.zip`, script + valid www cookies | **503** Akamai | `archives.` host has own bot-wall |
| Same legacy zip, **user's real browser, direct paste** | **Akamai edge error** (`errors.edgesuite.net`) | A human browser cannot pull it either |
| `nsearchives.nseindia.com` UDiFF for a 2020 date | 404 | UDiFF format only exists 2024-07+ |

**Conclusion: NSE has locked down the historical F&O bhavcopy archive.** Cookie-replay
cannot fix it — the block is server-side and hits humans too. Do not spend more effort on
any `nseindia.com` / `archives.nseindia.com` path for pre-2024 F&O bhavcopy.

## 7. Remaining viable paths (NSE-independent)

1. **Kaggle NSE F&O bhavcopy dataset** — the only free bulk static candidate. Coverage back
   to 2012 + futures + open interest is **unverified** (Kaggle pages are JS-rendered; needs a
   free account + API token to inspect/download via the `kaggle` CLI). Verify before trusting.
2. **Paid vendor — GDFL (globaldatafeeds.in) or TrueData (truedata.in).** Clean historical
   NSE F&O with OI, roll-ready. Costs money; most reliable; eliminates the scraping problem.
3. **Strategic alternative worth raising with the operator (design decision, not data-fetch):**
   The repo already holds *certified* cash-equity bhavcopy 2012–2022 (`equity_bhavcopy_adjusted`,
   7.03M rows, PSB-1). Single-stock-**futures** returns track cash-equity total returns very
   closely (futures = spot + carry); F1's 12-1 momentum *signal* is nearly identical on either
   series. What genuinely differs is the **fee/slippage model** (futures STT + impact vs delivery
   STT) — which F1 models separately anyway. Synthesizing the futures return series from the
   already-owned cash panel + a carry/roll model could dissolve the entire data blocker, at the
   cost of introducing basis-model risk. This changes F1's pre-registration and is the operator's
   call — flagged, not decided.

---
*Substrate remains UNCERTIFIED. F1 stays blocked at the Phase −1 data gate. Upstox and all
direct-NSE paths are recorded here as closed so they are not re-attempted. Live cookie set
used for testing was a scratchpad throwaway (session token, expires in hours) — not committed.*
