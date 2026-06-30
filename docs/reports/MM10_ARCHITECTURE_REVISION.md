# MM10 — Architecture Revision Note
## Margin Responsibility Boundaries

**Date:** 2026-06-29  
**Author role:** System Architect  
**Status:** Revision to `MM10_ARCHITECTURE_ROADMAP.md` — for Technical Lead approval  
**Scope:** Architectural responsibility boundary only. No implementation code. No redesign of MM9.5 components.

---

## 1. The Question

The MM10 roadmap proposed adding calendar spread credits, ELM, and exposure margin directly to `SpanMarginCalculator`. The Technical Lead's concern is that this violates the Single Responsibility Principle — these components originate from different rule sets and one of them (spread credits) is a portfolio-level operation, not a per-position calculation.

The question is: **Is a separate aggregator a better architectural boundary?**

The answer is **yes**. The reasoning follows.

---

## 2. Analysis

### 2.1 Responsibility Separation

`SpanMarginCalculator` currently takes one external dependency: `SpanSnapshot`. Every calculation it performs is derived from that snapshot. Its one job is: translate SPAN parameters into per-position scan margin.

The proposed MM10 additions would require new constructor arguments with no connection to SPAN:
- **ELM**: sourced from NSCCL circulars, not the SPAN file
- **Exposure margin**: sourced from NSE's published margin framework, not the SPAN file

Once these enter `SpanMarginCalculator`, the class has three data sources and three sets of update triggers. The class name becomes a lie: it is no longer a SPAN calculator; it is a general NSE margin calculator that happens to contain SPAN logic.

This is a genuine SRP violation, not a cosmetic one.

### 2.2 Per-Position vs. Portfolio-Level Operations

`SpanMarginCalculator` currently loops over `PositionTracker` and applies a per-position formula. The loop is stateless between positions.

Calendar spread credits are categorically different: they require grouping positions by underlying, identifying opposite-side legs across different expiries, and performing greedy lot-matching across the group. This is a cross-position reduction, not a per-position calculation.

Putting portfolio graph traversal inside a per-position calculator conflates two distinct operational models. The spread credit computation belongs one abstraction level higher.

### 2.3 Independent Update Cycles

The three margin components update independently:

| Component | Source | Update frequency |
|-----------|--------|-----------------|
| SPAN scan risk | NSE SPAN XML file | Daily (published by NSCCL) |
| ELM | NSCCL circulars | Months to years between changes |
| Exposure margin | NSE published margin framework | Rarely; major regulatory events only |

When ELM rates change, the correct response is to update a rate table and nothing else. That is only possible if ELM lives in a class that has no other responsibility.

### 2.4 Testing Complexity

With the split:
- `SpanMarginCalculator` tests: focused entirely on SPAN scan accuracy — RA reduction, SOM floor, per-contract lookups. No ELM or exposure fixtures. Failures are unambiguous.
- `NseMarginEngine` tests: aggregation logic only. Spread credit matching, ELM, and exposure rates tested in isolation. `SpanMarginCalculator` is testable independently and can be used directly in `NseMarginEngine` integration tests.

Without the split, a failing ELM test breaks the SPAN test suite. The root cause is buried in combined fixtures.

### 2.5 Long-Term Maintainability

If NSE introduces a new margin component (additional volatility margin near expiry, SEBI's peak margin rule), the correct place is the aggregator. `SpanMarginCalculator` is not touched. The SPAN infrastructure remains stable and certified.

If Upstox applies broker-specific haircuts on top of exchange margin, the correct place is the aggregator or a thin adapter above it. The SPAN layer is not involved.

### 2.6 Future Exchange Support

This argument is acknowledged but carries low weight here. The platform is NSE-only and CLAUDE.md explicitly prohibits abstractions for hypothetical future requirements. The split is motivated by the three concrete reasons above (sources, operational models, update cycles), not by speculative exchange support.

### 2.7 Runtime Performance

Negligible. The split adds one function-call layer for `get_used_margin`. For any realistic portfolio size the overhead is microseconds.

### 2.8 Backward Compatibility

`SpanMarginCalculator` remains protocol-conformant and unchanged from its MM9.5 state after MM10.2. It can be deployed directly (scan-only margin) as a conservative fallback at any point. The `MarginTracker` rollback path is unaffected. There are no breaking changes to the composition root until MM10.3 deliberately introduces the aggregator.

---

## 3. Recommendation

**Agree with the Technical Lead.**

The split is architecturally correct for three concrete reasons:

1. `SpanMarginCalculator` should depend only on `SpanSnapshot`. ELM and exposure rates are not SPAN data; adding them to this class creates an unlabelled multi-source aggregator.
2. Calendar spread credits are a cross-position reduction. They belong one level above a per-position calculator.
3. Independent update cycles for three regulatory sources require independent change surfaces.

---

## 4. Revised Architecture

### 4.1 Naming

The new aggregator is named **`NseMarginEngine`** rather than `PortfolioMarginEngine`.

Reasoning: ELM and exposure margin are per-position calculations, not per-portfolio reductions. Only calendar spread credits are genuinely portfolio-level. "Portfolio" is therefore partially misleading. "NSE" accurately scopes the class: it computes total required margin under NSE/NSCCL regulatory rules. A future MCX implementation would be a distinct class, not a subclass of this one.

This is a naming suggestion. The Technical Lead may override it.

### 4.2 Responsibility Assignment

| Class | Responsibility | Data source |
|-------|---------------|------------|
| `SpanMarginCalculator` | Per-position SPAN scan margin only: `abs(qty) x lot_size x max(scan_risk_per_contract, SOM)` | `SpanSnapshot` only |
| `NseMarginEngine` | Total NSE required margin: scan + spread credits + ELM + exposure | `SpanMarginCalculator` + rate tables |

`SpanMarginCalculator` continues to implement the `MarginCalculator` protocol (v2). It is also the conservative rollback: deploying it directly gives correct but unoptimised margin (no spread credits, no ELM, no exposure). This is always safe — it overestimates, never underestimates.

`NseMarginEngine` implements `MarginCalculator` (v2). It is what `ExecutionHandler` receives in LIVE F&O once MM10.3 is deployed.

### 4.3 Composition Root

```
Before MM10.3:
  ExecutionHandler <- SpanMarginCalculator(position_tracker, span_snapshot)

After MM10.3:
  span_calc = SpanMarginCalculator(position_tracker, span_snapshot)
  engine    = NseMarginEngine(span_calc, elm_rates, exposure_rates)
  ExecutionHandler <- engine

Rollback at any MM10 milestone:
  ExecutionHandler <- SpanMarginCalculator(position_tracker, span_snapshot)  [scan only]
  or
  ExecutionHandler <- MarginTracker(position_tracker)                        [flat rate]
```

### 4.4 Architecture Diagram

```
MarginCalculator protocol v2
         |
         +-- MarginTracker
         |     flat rate; equity / paper / backtest
         |
         +-- SpanMarginCalculator
         |     SPAN scan margin only; per-position
         |     data source: SpanSnapshot
         |     feature-frozen after MM10.2
         |
         +-- NseMarginEngine                        (new in MM10.3)
               total NSE required margin
               data sources:
                 SpanMarginCalculator (internal, for scan)
                 ELM rate table
                 Exposure rate table
                 PositionTracker (for spread leg matching)

               Computation sequence inside get_used_margin():
                 1. scan_total     = span_calc.get_used_margin(prices)
                 2. spread_credit  = _match_spread_legs() -> float
                 3. elm_total      = sum(_elm(sym, qty, lot, price) for each position)
                 4. expo_total     = sum(_exposure(sym, qty, lot, price) for each position)
                 5. return (scan_total - spread_credit + elm_total + expo_total)
                              x margin_rate
```

### 4.5 What Changes and What Does Not

**MM9.5 certified components — no change in MM10:**

| Component | Status |
|-----------|--------|
| `ParserRegistry` | Feature-frozen, unchanged throughout MM10 |
| `ParserV400` | Feature-frozen, unchanged throughout MM10 |
| `SpanSnapshot` | Feature-frozen, unchanged throughout MM10 |
| `SpanRepository` | Feature-frozen, unchanged throughout MM10 |
| `SpanReadiness` | Feature-frozen, unchanged throughout MM10 |
| `SpanMarginCalculator` | Feature-frozen after MM10.2; scan formula unchanged |

**MM10.2 is the last milestone that touches `SpanMarginCalculator`.** Per-expiry futures RA and per-strike option RA are improvements to SPAN scan accuracy and correctly belong there. After MM10.2, the certified calculator is not modified again.

---

## 5. Updated MM10 Milestone Ownership

| Milestone | Component modified | Change from original roadmap |
|-----------|--------------------|------------------------------|
| MM10.1-S1 Hard refusal | `scripts/fno_runner.py` | Unchanged |
| MM10.1-S2 Protocol v2 | `MarginCalculator`, `MarginTracker`, `handler.py` | Unchanged |
| MM10.2-S1 Per-expiry futures RA | `SpanMarginCalculator` | Unchanged — last touch to certified calculator |
| MM10.2-S2 Per-strike option RA | `SpanMarginCalculator` | Unchanged — last touch to certified calculator |
| MM10.3 Calendar spread credits | **`NseMarginEngine`** (new class) | **Moved from `SpanMarginCalculator`** |
| MM10.4 ELM | **`NseMarginEngine`** | **Moved from `SpanMarginCalculator`** |
| MM10.5 Exposure margin | **`NseMarginEngine`** | **Moved from `SpanMarginCalculator`** |

The dependency order is unchanged. The only change is where MM10.3-5 live.

---

## 6. Revised Dependency Graph

```
MM10.1 — Safety Hardening + Protocol v2
  S1: Hard refusal for absent SPAN (fno_runner.py)
  S2: MarginCalculator protocol v2 + retire hasattr
        |
        v
     MM10.2 — Contract-Level RA (SpanMarginCalculator — final touch)
       S1: Per-expiry futures RA
       S2: Per-strike option RA
       SpanMarginCalculator is feature-frozen from this point.
               |
               v
            MM10.3 — NseMarginEngine introduced; Calendar Spread Credits
              New class; composition root switches injection to NseMarginEngine.
                       |
                       v
                    MM10.4 — NseMarginEngine: ELM added
                      elm_rates module; NseMarginEngine._elm() method
                               |
                               v
                            MM10.5 — NseMarginEngine: Exposure Margin added
                              exposure_rates module; NseMarginEngine._exposure() method
                                       |
                                       v
                                    Production-ready NSE margin
                                    NseMarginEngine: scan + spread credits + ELM + exposure
                                    SpanMarginCalculator: feature-frozen, certified
```

---

## 7. Impact on MM9.5 Components

None.

`SpanMarginCalculator` is not modified in MM10.3, MM10.4, or MM10.5. Its constructor, scan formula, and protocol conformance are unchanged. The composition root change in MM10.3 replaces `span_calc` with `NseMarginEngine(span_calc, ...)` at one construction site in `fno_runner.py`. All MM9.5 regression tests remain valid and continue to exercise `SpanMarginCalculator` directly.

---

## 8. ADR Recommendation

One new ADR is warranted at the MM10.3 design review.

**ADR-011: NseMarginEngine is the MarginCalculator for LIVE F&O**

**Purpose:** Record that `NseMarginEngine` is the production `MarginCalculator` for LIVE F&O from MM10.3 onwards, and that `SpanMarginCalculator` is its internal SPAN component — not the production calculator once ELM and spread credits are live.

**Why required:** Without this ADR, a future implementer may inject `SpanMarginCalculator` directly into a LIVE F&O session and silently omit ELM and exposure margin.

**Scope:** Defines that `NseMarginEngine` implements the `MarginCalculator` seam for production; that `SpanMarginCalculator` is a valid but conservative fallback (scan-only); that `MarginTracker` is the flat-rate fallback.

Do not write this ADR yet. Author it at the MM10.3 design review.
