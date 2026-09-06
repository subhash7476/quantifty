# F1 — How Much Data Does the Current Construct Need?

*Author: Claude (Lead Quant Architect — analysis). Date: 2026-07-19.*
*Question: for F1 as pre-registered (weekly-formation, ≤10-name, 12-1 momentum, bracketed,
portfolio-level block-bootstrap evaluation), how much history is required?*
*Status: a priori sizing — no strategy return series exists yet (and the sealed window must
stay unread), so these are design-time requirements, not fitted estimates.*

---

## Answer up front

- **Statistical floor to run the machinery honestly:** ~3 years / ~150 weekly formations.
  Enough for a non-degenerate bracket-grid CV and a bootstrap with real blocks — but
  underpowered for anything short of a huge effect, and blind to momentum crashes.
- **What the construct actually needs:** the **full 2012–2022 pre-sealed span (~11 years,
  ~570 weekly formations)**, split 7yr TRAIN / 4yr HOLDOUT, exactly as the pre-reg §8 pins it.
- **What the current panel gives:** 13 months, 100% in the sealed window → powers nothing and
  can't be developed on anyway (see `F1_PHASE_MINUS1_INGESTION_REVIEW.md`).

The binding constraint is **not** the number of observations for a mean test — it is **regime
coverage for max-drawdown / tail**, because a concentrated momentum book's defining risk is the
momentum crash. That is a *coverage* requirement (must span ≥1 crash), not a pure-N requirement,
and it is what makes 11 years the right target rather than 3.

---

## Channel 1 — Power for the primary expectancy test

Weekly formation, one-week non-overlapping hold → ~52 observations/year. For the mean-return
t-test the noncentrality is:

> **t ≈ SR_annual × √(N_years)**

For 80% power at two-sided α=0.05 you need t ≈ 2.80, i.e. **N_years ≥ (2.80 / SR_annual)²**:

| Assumed **net** annual Sharpe | Years for 80% power |
|--:|--:|
| 1.5 | ~3.5 |
| 1.0 | ~7.8 |
| 0.8 | ~12.3 |
| 0.6 | ~21.8 |
| 0.5 | ~31 |

A ≤10-name single-name momentum book, **net of impact**, realistically lands at **SR ≈ 0.5–1.0**.
So the standalone-viability test wants **~8–22 years** — and even the full 2012–2022 (11 yr) is
marginal if net Sharpe < 0.9. This is the sobering number and the reason to pull *all* the
pre-sealed history, not a convenient recent slice.

## Channel 2 — Power for the paired bracket-vs-calendar test (F1's actual falsifiable prediction)

Pre-reg §5.3's committed prediction is **paired**: same signal, same formations, exit rule the
only difference (brackets must beat calendar on expectancy AND MaxDD). Pairing cancels the base
factor's own edge and variance, so the *difference* series has much lower SD than either leg.
This test is **cheaper** — roughly **3–5 years** to resolve a real bracket effect — because you
are detecting Δ(exit rule), not Δ(has edge at all). It is not the binding channel.

## Channel 3 — Regime / tail coverage for MaxDD (the one that actually binds)

MaxDD and the block-bootstrap tail are driven by the **worst episode observed**, so they are
estimable only if the window has *seen* a representative bad episode. For 12-1 momentum the
signature risk is the **momentum crash / sharp reversal** (2009, March 2020). You cannot
characterize the drawdown of a momentum book from a benign trend period at any sample size.

This is why the pre-reg deliberately puts a crash in each region: TRAIN 2012–2018 spans the
2013 taper tantrum and 2015–16 selloff; **HOLDOUT 2019–2022 contains the March-2020 crash and
its momentum reversal**. A window that omits every crash is *coverage-degenerate* for MaxDD
regardless of how many weekly observations it holds — which is precisely the defect of the
current sealed-only panel.

## Channel 4 — Universe availability (a hard gate on whether early years are even usable)

The ≤10-name book must select from a pool of **≥10 liquid single-stock futures at every
formation date** (realistically ≥40–50 eligible names to form a stable top-decile). Indian SSF
liquidity thins going back in time. **Before committing to TRAIN 2012–2018, verify empirically**
that `build_fo_universe.py`'s ≥100-median-contract floor yields enough eligible names per
formation week across 2012–2018. If the eligible pool is < ~40 names in the early years, the
usable TRAIN window shrinks from the front and Channel 1's already-tight budget gets worse.

---

## The design tension worth surfacing

**Concentration (≤10 names) is what makes the data budget brutal.** A 10-name book leaves
idiosyncratic risk undiversified → higher portfolio variance → lower Sharpe → more years needed
(Channel 1). A broader 30–50 name book would raise Sharpe and cut the requirement — but the
pre-reg chose concentration precisely to keep **market impact** testable in a small book
(§7's binding cost). So there is a real trade: concentration buys impact-realism at the cost of
statistical data-efficiency. This is a legitimate item to reconsider at §11 freeze — not a
defect, but the operator should choose it with the data cost in view.

---

## Bottom line for the re-acquisition

Pull the **entire 2012–2022 pre-sealed history** (both windows), not a recent slice. The
requirement is set by regime coverage (must span the 2020 momentum crash in HOLDOUT) and by a
realistic sub-1.0 net Sharpe (Channel 1), both of which demand the long window. The sealed 2023+
data you already have does not count toward development at all. Before freezing on 2012 as the
TRAIN start, confirm the eligible-universe count holds up in the early years (Channel 4).
