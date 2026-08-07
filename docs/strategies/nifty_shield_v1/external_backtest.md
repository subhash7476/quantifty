# External Backtest — `nifty_shield_v1` (FILED, NOT GRADED)

**Status:** Stage 0 evidence of *intent* (MM12.5 §4.0(d), §9.2). **Filed, not graded** — the
platform hosts no research and does not validate alpha (ADR-002, §1.1). These numbers are
**not** a promotion criterion and are **not** platform evidence of profitability.
**Date:** 2026-08-07
**Datasheet:** `docs/strategies/nifty_shield_v1/datasheet.md` §8
**Spec of record:** `docs/reports/NIFTY_SHIELD_ADOPTION_ASSESSMENT.md`

---

## 1. What is filed

The claim carried in the source bundle (`F:\nifty_research_bundle\README.md` §3c), produced on
the retired `D:\BOT\root` platform:

| Metric | Reported value |
|---|---|
| Trades | 400 |
| Win rate | 97.5% |
| Sharpe | 9.40 |
| Net P&L | +Rs 26L |
| Structure | 4 walk-forward windows |
| Backtest period | **Not specified in the bundle** |

## 2. Provenance and reproducibility — read before citing

**The primary artifacts do not exist in the repository or the bundle.** The backtest harness
(`nifty_shield_backtest.py`, `--walkforward`), the per-window breakdown, and the trade log were
**not shipped** (README: "not in this bundle … they exist in the old repo"). What is filed here
is the README's **summary claim only** — a reported number, not reproducible evidence. It cannot
be independently reconstructed or verified from anything in this repository. This is the honest
Stage-0 status: *intent asserted*, not *intent demonstrated*.

## 3. Why the numbers are optimistic and unvalidated — by construction

The bundle's own caveat (README §3c), preserved here so it travels with the number:

- **Flat IV** — priced at `VIX/100`, **no volatility smile**. A short-premium book's edge and
  its tail both live in the smile; a flat surface flatters both.
- **Synthetic Black-76 pricing** — no real option marks; the fills never met a real bid/ask.
- **No gap or slippage modeling** — the 2× stop is assumed to fill at its level.
- **Paper-only** — no live Upstox order placement was ever wired.

A 97.5% win rate with Sharpe 9.40 is the signature of a premium-selling curve measured **without
the cost of its own tail** — exactly what flat IV + synthetic marks + no slippage removes. Treat
the magnitude as an artifact of the assumptions, not a forecast.

## 4. Governance disposition

- **Not graded** (§1.1, §3.2): recorded as intent, never used as a pass/fail gate.
- **Referenced, not re-run, at Stage 3→4**: the Account Owner may weigh it as *context* in the
  capital decision, alongside the **actual** Stage 2 PAPER P&L facts, which are the real evidence.
- **The mandated revalidation is forward PAPER** (§7.3) — on live/near-real option marks,
  out-of-sample by construction, with real gaps and slippage. Forward paper *is* the "revalidate
  on real marks" step the README asks for; it replaces, and must not be substituted by, any
  historical re-run.
- **PROHIBITION (assessment §3):** this backtest must **never** be re-run over the OSC-preserved
  unread Nifty index-options window (2016-02-11 → 2022-12-31). Doing so spends a sealed research
  window on an ungated read — the one concrete protocol breach available in this work.

## 5. If the primary artifacts are ever recovered

Should the old-repo harness and per-window results be retrieved, they may be **committed
alongside this file** to upgrade it from *reported claim* to *reproducible filing* — but the
governance disposition in §4 is unchanged: still filed, still not graded, still no historical
re-run over the OSC window. Recovery improves provenance, not standing.
