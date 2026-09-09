# MM10.5 — Architecture Reassessment: Broker Margin API Evidence

**Date:** 2026-07-01
**Trigger:** Upstox `/charges/margin` API response inspection (order-margin endpoint) surfaced
new evidence bearing directly on MM10.5 Spec Section 8, Risk 1 ("EM rate and component count
are UNVERIFIED — conflicting evidence found (HIGH)").
**Status:** SUPERSEDED — see 2026-07-01 update below. Risk 1 resolved as Hypothesis B (H-same)
via primary-source research; **MM10.5 formally RETIRED 2026-07-01 (ADR-012)**, proceeding without
the requested live-browser MG-12/MG-13 corroboration — `nseindia.com` is blocked by the Chrome
extension's own safety restrictions and the check is not completable through this channel; a
same-day check of today's live SPAN Risk Parameter file (`nsccl.20260701.i01.spn`) confirmed only
that no separate Exposure Margin rate series exists in that file (orthogonal to the discriminator,
not corroborating evidence for it — see `docs/reports/MM10_5_MARGIN_COMPONENT_VERIFICATION.md` §3).
**Predecessor:** `docs/reports/MM10_5_IMPLEMENTATION_SPECIFICATION.md`, ADR-011
(`docs/architecture_decisions.md`).

**2026-07-01 update — Risk 1 resolved:** `docs/reports/MM10_5_MARGIN_COMPONENT_VERIFICATION.md`
resolves the Risk 1 discriminator this document sharpened (§3 above) as **Hypothesis B
(H-same)**: SEBI's risk-management history page states ELM "replaces the terms 'exposure
margin' and 'second line of defence'"; NSE's current MG-12/MG-13 clearing report schema
itemizes SPAN Margin, Extreme Loss Margin, Delivery Margin, and Margin on Consolidated
Crystallized Obligation only — no separate Exposure Margin field. This content was recovered
via a reader-proxy fetch of nseindia.com (direct WebFetch and browser automation were both
unavailable at research time). ADR-011 (`docs/architecture_decisions.md`) has been updated
with this closure. The Technical Lead has requested one further sanity check — a live-browser
open of the MG-12/MG-13 report page with a PDF/screenshot archived to `docs/reports/` — before
MM10.5 is formally retired; that check is outstanding pending Chrome browser-extension
availability.

---

## 1. What was found

Sample Upstox order-margin responses (equity, futures, long option):

```
Futures: span_margin=57501.50, exposure_margin=12320.55, additional_margin=0,
         tender_margin implied 0, total_margin=69822.05
Option:  net_buy_premium=1950, total_margin=1950
Equity:  equity_margin=33.6, total_margin=33.6
```

All three totals reconcile exactly to the sum of their non-zero component fields, with no
residual — `57501.50 + 12320.55 = 69822.05`. There is no unexplained gap that a hidden third
component (e.g. ELM) would need to fill.

Upstox's own API documentation (`/charges/margin`, `docs.upstox.com`) gives field-level
descriptions:

| Field | Upstox's description |
|---|---|
| `span_margin` | "Upfront margin mandatory by exchange for derivatives trade. FNO only." |
| `exposure_margin` | **"Based on ELM percentage values provided by exchange. FNO only."** |
| `additional_margin` | "Applicable on MCX FNO trade for certain commodities." |
| `tender_margin` | "Applicable as the futures contract approaches its expiration date." |

The `exposure_margin` field description explicitly ties its value to **ELM percentage values**.

## 2. What this does and does not prove

**Solid, load-bearing fact:** for equity F&O, the Upstox pre-trade margin-blocking response has
exactly one non-SPAN percentage-based component (`exposure_margin`), and the total is fully
explained by `span_margin + exposure_margin` with zero residual. `additional_margin` is
documented as MCX-commodity-only and `tender_margin` as an expiry-proximity charge — neither is
a general equity-F&O ELM line. This holds regardless of how the "based on ELM percentage
values" phrase is read.

**Not proven:** that NSE's regulatory margin stack has only one component (SPAN + one
loss-buffer charge) rather than three (SPAN + Exposure Margin + ELM, as MM10.4/MM10.5 currently
assume). The `/charges/margin` endpoint returns **order-time blocked (upfront) margin only**.
It is structurally possible that ELM is a real, separate NSCCL component that is levied at
end-of-day on net open position and simply isn't represented in a pre-trade order-margin
quote — in which case its absence here proves nothing about its existence elsewhere.

Two live hypotheses, both still standing after this evidence:

- **H-same** — "Exposure Margin" and "ELM" are two names for the same regulatory component.
  Upstox's phrasing ("exposure_margin, based on ELM percentage values") is read literally: the
  exchange computes one loss-buffer charge from a percentage table historically/colloquially
  called "ELM rates," and brokers surface it under the label "Exposure Margin." Under H-same,
  MM10.4's `elm_rates.py` (2% index) already implements this component — just mislabeled — and
  MM10.5 as spec'd (`exposure_margin_rates.py`, 3% index, stacked additively on top of ELM)
  would **double-count** the same charge, inflating `get_used_margin` by roughly the EM amount.

- **H-separate** — SPAN, Exposure Margin, and ELM are three genuinely distinct NSCCL
  components. Exposure Margin is blocked at order time (hence visible in `/charges/margin`);
  ELM is levied at end-of-day / on net position and is out of scope for a pre-trade order-margin
  quote, hence invisible here. Under H-separate, MM10.4 and MM10.5 are both correct in
  principle and additive as currently designed — only the specific rate values need
  independent verification.

The evidence shifts weight toward H-same (a primary broker source, not a blog/summary, ties
"exposure_margin" directly to "ELM percentage values") but does not discriminate between the
two structurally. Rate magnitude cannot be used as a tiebreaker here either: 12320.55 is an
unknown-notional instrument, so it cannot be checked against 2% vs 3% vs 5%.

## 3. The discriminator (unchanged from Spec Risk 1, now sharpened)

Fetch an **itemized** margin breakdown for one NIFTY futures lot from a primary source:

- A Zerodha/Sensibull/Samco SPAN margin calculator UI (these typically itemize the full stack), or
- The raw NSCCL circular text (`nseclearing.in/risk-management/equity-derivatives/circulars`)
  that defines "Exposure Margin" and, separately, "Extreme Loss Margin," if both exist as named
  circulars.

**Count the non-SPAN percentage line items:**
- **Two** (SPAN + one loss-buffer line, whatever it's called) → **H-same confirmed.** Collapse
  MM10.4 and MM10.5 into a single component. `elm_rates.py`'s rate must be re-verified against
  the primary source (is 2% correct, or is 3% correct, or neither?) and MM10.5 as currently
  spec'd is retired, not merely deferred — its `_em_margin` design would be implementing a
  component that already exists under a different name.
- **Three** (SPAN + Exposure Margin + ELM, both present as separately named, separately rated
  circular items) → **H-separate confirmed.** MM10.5 may proceed, but the 3% index EM rate in
  the current spec must still be verified against the primary circular before
  `exposure_margin_rates.py` is written (Spec Section 0c already flags this; unchanged).

Broker API docs and web-search summaries — including the finding in this document — are not
sufficient to close Risk 1. Only a primary NSCCL circular or an itemized third-party breakdown
resolves it.

## 4. Answering the two architecture questions

### 4a. Does the broker API change the value proposition of MM10.5 / the margin engine?

**No — the internal `NseMarginEngine` remains the production `MarginCalculator` for LIVE F&O.**
ADR-011 stands. Two platform-level constraints rule out replacing it with a live broker call,
independent of how Risk 1 resolves:

- **Runner is Neutral** (CLAUDE.md Architecture Principle 4): the LoopDriver treats live and
  backtest data identically. A backtest has no broker session and cannot call
  `/charges/margin`. If margin sizing depended on the broker API, backtest and live would run
  on structurally different margin logic — which the platform's own constitution forbids.
- **Audit-First** (Principle 5): every trade must be explainable by exact analytical facts. A
  broker's black-box total is not decomposable into a formula; the internal engine's per-component
  breakdown (`span - credit + elm + em`) is. Relying on the broker number for sizing also makes
  the platform's risk posture depend on a rate-limited, LIVE-only network call that has no
  documented rate limit and is exactly the kind of dependency likely to degrade during the
  volatility spikes when margin correctness matters most.

The broker API's value is real but narrower than "replace the calculator": (a) it is a primary
source for settling Risk 1 (Section 3), and (b) it is a candidate input for a future **LIVE-only
pre-trade reconciliation/variance-alert layer** — call `/charges/margin` before order placement,
compare against `NseMarginEngine.get_used_margin`, log/alert on divergence beyond a tolerance.
This would be a new, additive milestone (not yet scoped) layered on top of the existing engine,
not a substitute for it.

### 4b. Should MM10.5 proceed?

**Not yet.** MM10.5 Spec Risk 1 already states implementation must not proceed until the
discriminating check resolves. This finding is new evidence for that check, not a resolution of
it — record it, don't act on it as a green light. Do not write `exposure_margin_rates.py` or
modify `nse_margin_engine.py` until Section 3's two/three-component count is settled from a
primary source.

## 5. Recommended next action

Pull an itemized single-instrument margin breakdown (NIFTY, one futures lot) from a primary
source per Section 3, and report the line-item count and rates back before any MM10.5 code is
written. This is a research step, not an implementation step — no TDD phase begins until it's
done.

---

*Ref: docs/reports/MM10_5_IMPLEMENTATION_SPECIFICATION.md §8 Risk 1; docs/architecture_decisions.md ADR-011; CLAUDE.md Architecture Principles 4–5.*

**Successor:** `docs/reports/MARGIN_AUTHORITY_ARCHITECTURE_REVIEW.md` (2026-07-01) generalizes
the "does the broker API replace the local engine" question this document answered narrowly
(§4a above) into a platform-level two-authorities model (sizing vs. order-acceptance) and
evaluates a proposed configurable validation policy and `MarginProvider` abstraction.
