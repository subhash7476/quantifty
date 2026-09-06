# MM10.5 — Primary-Source Research: NSE Margin Component Verification

**Question**: Are Exposure Margin and Extreme Loss Margin (ELM) two separate regulatory components for NSE Equity Derivatives, or the same component under different terminology?

**Method**: Primary-source research against official NSE/NSE Clearing/SEBI documentation. Research-only — no code changed.

**Access note**: `nseindia.com` blocked direct WebFetch and a text-proxy fetch on the two target URLs (`all-reports-derivatives`, `equity-derivatives-data-reports-margin`); Chrome browser automation was unavailable in this environment. Content below sourced via a reader-proxy fetch of the same NSE/NSE Clearing pages, plus direct SEBI fetches and web search. Flagged as proxy-fetched, not raw-HTTP, wherever it matters. One residual gap: recommend someone open the two URLs directly in a real browser once to eyeball the MG-12/13 field lists first-hand.

---

## 1. Primary-source findings

**SEBI (highest-authority source found)** — `sebi.gov.in/sebi_data/commondocs/riskmgmt_h.html`:
> "The term Extreme Loss Margin replaces the terms 'exposure margin' and 'second line of defence' that have been used hitherto."

This directly documents that "Exposure Margin" is the **historical name** for what's now called ELM — not a second component. Corroborated by SEBI Cir-42/2008 ("Revised Exposure Margin for Exchange Traded Equity Derivatives") still using the old term, and a 2009 NSCCL circular (`NSCCL/F&O/C&S/967`) in transition. The exact renaming circular number/date could not be pinned down — a documentation-provenance gap, not a factual one.

**NSE Clearing today** — `nseclearing.in` FAQ PDF (`NCL - FAQ RISK MANAGEMENT.pdf`, Jan 2025) + `nseclearing.in/risk-management/equity-derivatives/margins`: defines ELM (2% of notional for index derivatives, 3.5% for stock derivatives, with add-ons for deep OTM options, long-dated index options, and expiry-day index options) and **defines no separate "Exposure Margin" component anywhere**. These rates match the existing `core/risk/elm_rates.py` (`INDEX: 0.02`, `STOCK: 0.035`) exactly — corroborated, not contradicted.

**Strongest evidence — NSE's own report schemas (MG-12/MG-13)**, from `nseindia.com/static/products-services/equity-derivatives-data-reports-margin`:
- **MG-12** (Detail Margin File, Clearing Member level): *"Trade Date, Trading Member Code/CP Code, SPAN margin, Filler, Extreme Loss Margin, Delivery Margin, Margin on consolidated crystallized obligation and Total margin"*
- **MG-13** (Client Level Margin File): Total Margin = *"SPAN margin + Extreme Loss margin + Delivery margin + Margin on consolidated crystallized obligation"*
- **MG-14/MG-15** (Cross Margin Benefit reports): *"...Initial Margin Benefit and Extreme Loss Margin Benefit"*

**No "Exposure Margin" field exists in any current F&O clearing report.** NSE's actual itemization is: SPAN + ELM + Delivery + Consolidated Crystallized Obligation (+ conditional Additional Surveillance Margin, Cross-Margin Benefit).

`nseindia.com/all-reports-derivatives` does list an **"F&O-Exposure Limit file"** (.csv, daily) — but that is a position-limit (MWPL/open-interest ceiling) concept, unrelated to "Exposure Margin" as a margin-rate concept. This is a plausible source of naming confusion in secondary/broker material.

`ael.csv` and `FOVOLT` could not be confirmed to exist under current NSE naming — flagged as unconfirmed; do not build ingestion around them without independent verification.

**Surveillance-driven ELM multipliers** (`nseindia.com/static/regulations/additional-surveillance-measure-equity-derivatives`): ELM is tiered up by MWPL utilization — +50% at 70–75% MWPL, up to +300% at >90% MWPL — plus a flat +15% margin increase (capped at 100%) when a security enters the derivatives ban list. These are multipliers on ELM, not a distinct additive component, and are member/security-state-dependent.

---

## 2. Margin component table — NSE Equity Derivatives

| Component | Live for F&O? | Definition / basis | Official source |
|---|---|---|---|
| SPAN Margin | Yes | 99% 1-day VaR portfolio margin (Price Scan Range, Volatility Scan Range, Calendar Spread Charge, Short Option Minimum Charge) | NSE SPAN Risk Parameter files, MG-12/13 |
| Extreme Loss Margin (ELM) | Yes | 2% notional (index) / 3.5% notional (stock), gross open position, with OTM/tenor/expiry-day add-ons and MWPL-surveillance multipliers | NSE Clearing margins page, NCL FAQ PDF |
| "Exposure Margin" (F&O) | **No — historical name for ELM, not a live separate component** | Pre-~2009 term for the same charge now called ELM | SEBI risk-mgmt history page; SEBI Cir-42/2008 |
| Delivery Margin | Yes | Progressive margin on stock-option/futures physical-delivery exposure: 10% at E-4, 25% at E-3, 45% at E-2, 70% at E-1 | NCL FAQ PDF, MG-12/13 field list |
| Margin on Consolidated Crystallized Obligation | Yes | MTM P&L to settle, options premium payable/receivable, exercise/assignment obligations | NCL FAQ PDF, MG-12/13 field list |
| Additional Surveillance Margin | Conditional | Ban-list/promoter-pledge/MWPL-triggered overlay, up to +100% margin rate cap | NSE Additional Surveillance Margin page |
| Cross-Margin Benefit | Conditional | Offset credit for correlated index/stock positions | MG-14/MG-15 |
| Additional Margin (volatile stocks) | Conditional | Triggered by >10% intraday move for 3+ days/month or 10+ days/6 months | NCL FAQ PDF |

---

## 3. File inventory (NSE public reports)

**Retail-inaccessible tier**: MG-09 through MG-15 and cross-margin reports are downloadable only by Clearing/Trading Members via NSE's member extranet — not available to a retail trader or non-member platform. This is the direct reason a broker Margin API is needed as a live cross-check.

**Publicly downloadable tier** (`all-reports-derivatives`): SPAN files (.zip, multiple intraday snapshots + EOD), SPAN Risk Parameter files (Begin of day, 1st–4th intraday, EOD), Haircut for Approved Securities/Mutual Funds (.csv, daily), Exposure *Limit* file (.csv, daily — position-limit, not margin-rate), Client Position ≥3% MWPL (.xls, daily), Client-wise Position Limits (.lst, daily), Trading Memberwise/Marketwide/FII-MF Position Limits (.csv, daily).

The existing frozen `ParserRegistry`/`ParserV400`/`SpanRepository` stack already ingests the single most information-dense public NSE margin input (SPAN XML v4.00). No additional public NSE file carries a distinct "Exposure Margin" rate series to ingest, because that rate doesn't exist as a separate published series — it's ELM, already sourced correctly in `elm_rates.py`.

**2026-07-01 empirical check**: today's live SPAN file (`reference/span/.../nsccl.20260701.i01.spn`, PC-SPAN v4.00) was grepped case-insensitively for `exposure`, `extreme`, `elm`, `loss`, `buffer`, `defence` — zero hits on all six; only tag content present is scan-range/spread/interest-rate parameters (the sole `<exm>` occurrence is inside `<intrRate>`, an interest-rate field, unrelated). This is **orthogonal to the H-same/H-separate discriminator in `MM10_5_ARCHITECTURE_REASSESSMENT.md` §3** — a PC-SPAN file would omit these terms under either hypothesis, since it only ever encodes the SPAN-component risk arrays, never NSCCL's additive overlay charges. It does not corroborate Q2/Q3 below. It does confirm the narrower point already stated above: the public SPAN file carries no distinct Exposure Margin rate series to ingest.

---

## 4. Answers

**Q1 — Which margin components officially exist for NSE Equity Derivatives?**
Per NSE's own MG-12/MG-13 report schema: SPAN Margin, Extreme Loss Margin, Delivery Margin, Margin on Consolidated Crystallized Obligation, Total Margin — plus conditional overlays (Additional Surveillance Margin, Cross-Margin Benefit).

**Q2 — Is Exposure Margin separate from ELM, or is one derived from the other?**
Neither — they are the same component under different terminology, and "Exposure Margin" is a retired name for F&O. SEBI's own history page states ELM explicitly "replaces the term exposure margin." Current NSE F&O margin reports (MG-12/13/14/15) have no "Exposure Margin" field — only ELM. Upstox's `exposure_margin` API field ("based on ELM percentage values provided by exchange") is broker-level legacy naming sourced from NSE's current ELM percentage — consistent with, not contradicting, this finding.

**Q3 — Can MM10.5 Risk 1 now be resolved?**
Yes. SEBI's terminology statement plus NSE's current MG-12/13 field schema are unambiguous: treat "Exposure Margin" as a legacy synonym for ELM for NSE Equity Derivatives, not a second additive term. Residual gap: the exact NSE/SEBI circular that formally executed the F&O-segment renaming was not located (the 2008 "before" state and current "after" state are both documented, but not the transition circular) — a historical-documentation curiosity, not a blocker.

**Q4 — Does public NSE data suffice to improve the local margin engine?**
Partially. Public SPAN files plus the NSE Clearing margins page (already cited in `elm_rates.py`) are sufficient for what `NseMarginEngine` currently computes (SPAN + spread credits + ELM). Not publicly available: MG-09 through MG-15 themselves (member-only), so locally-computed numbers cannot be cross-checked against NSE's actual per-client margin statement — only against a broker Margin API as a downstream proxy, which is the validation role the architecture already assigns to it.

**Q5 — Should additional daily files (AEL, FOVOLT) be ingested?**
Their existence under current NSE naming could not be confirmed — don't build ingestion around unverified file names. Of confirmed files, only the Haircut file (relevant only if collateral/liquid-asset haircut modeling is ever added — outside `NseMarginEngine`'s current scope) and the Exposure *Limit*/position-limit files (relevant only if MWPL-driven ELM surveillance multipliers are ever modeled) offer incremental value, and both represent new scope, not a fix to existing behavior.

**Q6 — Re-evaluate: local deterministic engine + broker Margin API for live validation + broker RMS as order-acceptance authority.**
Findings strengthen this architecture. Since NSE's member-only reports (the actual ground truth) are unreachable outside clearing-member access, the broker Margin API remains the only real-time cross-check available — validating the existing design rather than exposing a hole in it. Refinement: any discrepancy between the local engine and Upstox's `exposure_margin` field should be attributed to naming, not a missing calculation — do not add a second "exposure margin" term to `NseMarginEngine` to chase parity with that field name.

---

## 5. Recommendations

**MM10.5**: Close Risk 1 as resolved. Record that "Exposure Margin" (as seen in broker docs/APIs) maps 1:1 onto ELM for NSE Equity Derivatives, citing (a) SEBI's terminology-history statement and (b) the absence of any "Exposure Margin" field in NSE's current MG-12/13/14/15 report schemas. Do not add an `exposure_margin` field/calculation distinct from `elm_rates.py`.

**Future data ingestion**: No new file is needed to close this gap. If MWPL-driven ELM surveillance multipliers are pursued as a future feature, the public Client-wise/Marketwide Position Limits (.csv) files are the correct inputs — new scope, not a fix.

**Documentation updates**: Add a short terminology note (SEBI quote + MG-12/13 field list) wherever the MM10.5 blocking question is tracked, so it isn't reopened. `elm_rates.py`'s existing NSCCL-source attribution is already correct — no change needed. If full provenance is later required for a compliance-facing document, flag the unresolved renaming-circular date as a known minor gap rather than inventing a circular number.
