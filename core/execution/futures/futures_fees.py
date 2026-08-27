"""NSE single-stock futures transaction-cost model (SFB Phase -1 / D4).

Per-leg (one side, one futures trade) statutory costs for NSE derivatives
segment single-stock futures at the retail tier. Rate schedules are
effective-dated so a 2012->2026 backtest applies the rate in force on each
trade date.

Futures STT is sell-side only (derivatives rate). Unlike delivery equity (0.1%
both legs), futures have lower statutory costs but potentially higher
slippage/impact in a concentrated book — that is a harness concern, not this
module.

-----------------------------------------------------------------------------
SOURCES — every rate carries its primary source + effective date. Where a primary
circular could not be fetched directly, the value is the best-documented figure
and is flagged with [VERIFY]; each is a localized constant an era-revision will
correct in one line.

STT (Securities Transaction Tax) — derivatives, SELL side only. Four tiers:
  - 2008-06-01 -> 2013-05-31: 0.0170% (Rs 17/lakh). Derivatives were brought
    into STT at this rate. NEVER PRICED BY ANY READ — the futures substrate
    starts 2016-02-11 — but pinned so the schedule is correct rather than
    merely correct-where-used. Added 2026-08-01; see below.
  - 2013-06-01 -> 2023-03-31: 0.0100% (Rs 10/lakh), Budget 2013 cut from
    0.017%. This is the rate in force for the whole usable substrate up to
    2023-03, and is unchanged by the 2026-08-01 correction.
  - 2023-04-01 -> 2024-09-30: 0.0125% (Rs 12.5/lakh), Finance Act 2023 (+25%
    over the 0.0100% rate).
  - From 2024-10-01: 0.0200% (Rs 20/lakh), Finance (No. 2) Act 2024 / Budget
    2024 (Oct-2024 derivatives STT revision).
  - This is the canonical schedule pre-registered in
    CARRY_PHASE0_PRE_REGISTRATION.md section 8 and used by the Carry research
    harnesses (run_sealed.py / run_net_spread.py); it is the single source of
    truth for research and production (CARRY_IMPLEMENTATION_BRIDGE.md section 5.1).
  - 2026-08-01 CORRECTION: the 0.0170% tier (2008-06-01 -> 2013-05-31) was
    missing; 0.0100% was applied from 2008-06-01. Every rate on and after
    2013-06-01 is UNCHANGED. This was not a research finding — it surfaced
    because arm_fe asserted a rate (0.0125% at 2008-06-01) that was itself
    wrong, and reconciling the two required establishing the real schedule.
    Both are now correct.

    WHO IS AFFECTED (measured, not assumed):
      - Futures-substrate harnesses (Carry, TS Basis, TS Basis Daily, IVOL,
        Trend, LAG) — UNAFFECTED. 0 of 3,977 dates from 2016-02-11 through
        2026-12-31 change, because futures data cannot predate 2016-02-11.
        No pre-registered or sealed number moves.
      - f1_feasibility_screen.py — AFFECTED. It is CASH-SYNTHESIZED with
        DEV_LO = 2012-01-01, so it prices dates this module could not
        otherwise reach: 517 dates in its TRAIN window (2012-01-01 ->
        2013-05-31) now carry 0.0170% instead of 0.0100% on SELL legs. Its
        HOLDOUT (2019-2022) is clean.
        Consequence: F1's TRAIN net returns get slightly WORSE, which
        strengthens rather than weakens its existing NO-GO verdict. F1 is
        CLOSED and deliberately NOT re-run, so F1_FEASIBILITY_SCREEN_REPORT.md
        no longer reproduces exactly — it was already superseded by
        F1_FEASIBILITY_SCREEN_VERDICT_REVIEW.md.
  - Sources: [caclubindia](
      https://www.caclubindia.com/articles/securities-transaction-tax-rate-hikes-on-f-amp-o-w-e-f-1st-october-24-55626.asp),
      [ICICI Direct](
      https://icicidirect.com/research/equity/finace/new-stt-rules-in-futures-and-options-trading).

NSE derivatives transaction charge — ad-valorem on turnover, both legs.
  - 0.0021% (Rs 2.10/lakh) for futures at retail tier, both sides.
    Source: NSE circulars, stable through dev window.
  - 2024-10-01 reduction to 0.00189% (Rs 1.89/lakh) under SEBI MII charge
    rationalization (SEBI board decision Aug 2024; NSE circular 2024-10-01).
    [VERIFY exact Rs/lakh against the circular number; era boundary is certain.]
  - NOTE: Futures transaction charges are lower than CM (cash market).
    NSE F&O charges are tiered by monthly turnover; this uses the retail tier.

SEBI turnover fee — ad-valorem on turnover, both legs.
  - Rs 10/crore (0.0001%), same as cash market. Source: SEBI (Turnover Fees)
    Regulations. Stable across the dev window.

Stamp duty — BUY side only, futures.
  - Post-2020-07-01: 0.002% on buyer, uniform central regime (derivatives rate).
    Indian Stamp Act 1899 as amended by Finance Act 2019 (w.e.f. 2020-07-01).
    The derivative rate is lower than delivery equity (0.003%).
  - Pre-2020-07-01: STATE-WISE, no single national rate.
    DOCUMENTED ASSUMPTION: 0.01% buyer-side, same as the Maharashtra
    representative rate used for equity delivery (conservative upper bound).

GST (post-2017) / service tax (pre-2017) — on (brokerage + exchange_txn +
  sebi_fee) ONLY. STT and stamp duty are OUTSIDE the GST base.
  Same schedule as delivery fees; mirrors the equity model exactly:
    2017-07-01: 18%  GST
    2016-06-01: 15%  (service tax + Krishi Kalyan Cess)
    2015-11-15: 14.5% (service tax + Swachh Bharat Cess)
    2015-06-01: 14%
    prior:      12.36%

Brokerage — default Rs 20 flat per executed order (discount broker, futures).
  Futures and options are typically charged on a flat-per-order basis rather
  than a percentage. Rs 20/order is a representative discount-broker value.

Clearing charge — NSE clearing corporation fee, ad-valorem on turnover.
  - 0.005% (Rs 5/lakh) for verified (non-BTST/not-guaranteed) trades, both legs.
    [VERIFY against latest NSE circular — may be included in transaction charge.]
    Currently treated as part of the transaction charge for simplicity; set to
    0 here with a documented seam to add it if verified.

Out of scope: options (different STT regime), delivery equity (0.1% STT both legs).

Documented seam: a concentration-aware slippage/impact model K is NOT part of
this module. The harness (screening or backtest) computes its own K as a function
of portfolio concentration and average daily volume; this module provides the
statutory cost layer only.
-----------------------------------------------------------------------------
"""

from dataclasses import dataclass
from datetime import date

# Brokerage default — Rs 20 flat per order (discount broker futures).
DEFAULT_BROKERAGE = 20.0

SEBI_FEE_RATE = 0.000001  # 0.0001% of turnover (Rs 10/crore) — both legs, stable.

# (effective_from, rate) — newest first; first row with effective_from <= trade_date wins.
# Futures STT sell-side only. Three tiers (canonical per CARRY_PHASE0_PRE_REGISTRATION
# section 8): 0.0100% through 2023-03-31, 0.0125% 2023-04-01 -> 2024-09-30 (Finance
# Act 2023), 0.0200% from 2024-10-01 (Finance (No.2) Act 2024). Sources: caclubindia,
# ICICI Direct.
_STT_FUTURES_SCHEDULE = (
    (date(2024, 10, 1), 0.0002),     # 0.0200% — Oct-2024 derivatives STT revision.
    (date(2023, 4, 1), 0.000125),    # 0.0125% — Finance Act 2023 (+25%).
    (date(2013, 6, 1), 0.0001),      # 0.0100% — Budget 2013 cut from 0.017%.
    (date(2008, 6, 1), 0.00017),     # 0.0170% — derivatives brought into STT.
    (date(1900, 1, 1), 0.0),         # No STT on derivatives before 2008.
)
# NSE derivatives (F&O) transaction charge — ad-valorem, both legs.
_EXCHANGE_TXN_SCHEDULE = (
    (date(2024, 10, 1), 0.0000189),  # 0.00189% — SEBI MII rationalization.
    (date(1900, 1, 1), 0.000021),    # 0.00210% — retail tier.
)
# Stamp duty — BUY side only, derivatives rate.
_STAMP_DUTY_SCHEDULE = (
    (date(2020, 7, 1), 0.00002),  # 0.002% buyer — uniform central derivatives rate.
    (date(1900, 1, 1), 0.0001),   # 0.01% buyer — Maharashtra-representative pre-regime assumption.
)
# GST / service tax on (brokerage + exchange_txn + sebi_fee) only.
_GST_SCHEDULE = (
    (date(2017, 7, 1), 0.18),
    (date(2016, 6, 1), 0.15),
    (date(2015, 11, 15), 0.145),
    (date(2015, 6, 1), 0.14),
    (date(1900, 1, 1), 0.1236),
)


def _resolve(trade_date, schedule):
    for effective_from, rate in schedule:
        if trade_date >= effective_from:
            return rate
    raise ValueError(f"trade_date {trade_date} predates the schedule")


def stt_futures_rate(trade_date):
    """STT rate for futures (sell side only, derivatives rate)."""
    return _resolve(trade_date, _STT_FUTURES_SCHEDULE)


def exchange_txn_rate(trade_date):
    """NSE derivatives transaction-charge rate (fraction of turnover)."""
    return _resolve(trade_date, _EXCHANGE_TXN_SCHEDULE)


def stamp_duty_rate(trade_date):
    """Stamp-duty rate (fraction of buy-side turnover, derivatives rate)."""
    return _resolve(trade_date, _STAMP_DUTY_SCHEDULE)


def gst_rate(trade_date):
    """GST (post-2017) / service-tax (pre-2017) rate on the statutory-services base."""
    return _resolve(trade_date, _GST_SCHEDULE)


@dataclass(frozen=True)
class FuturesFees:
    brokerage: float
    stt: float
    exchange_txn: float
    sebi_fee: float
    stamp_duty: float
    gst: float

    @property
    def total(self):
        return (self.brokerage + self.stt + self.exchange_txn + self.sebi_fee
                + self.stamp_duty + self.gst)


def futures_fees(*, side, trade_value, trade_date, brokerage=DEFAULT_BROKERAGE):
    """Fees for one executed single-stock futures leg.

    Args:
        side: "BUY" or "SELL".
        trade_value: notional traded value in Rs (price * lot_size * lots).
        trade_date: execution date — selects the statutory rates in force.
        brokerage: flat brokerage per order, Rs (default 20, discount broker).
    """
    if side not in ("BUY", "SELL"):
        raise ValueError(f"side must be BUY or SELL, got {side!r}")

    g = gst_rate(trade_date)
    stt = trade_value * stt_futures_rate(trade_date) if side == "SELL" else 0.0
    exchange_txn = trade_value * exchange_txn_rate(trade_date)
    sebi_fee = trade_value * SEBI_FEE_RATE
    stamp_duty = trade_value * stamp_duty_rate(trade_date) if side == "BUY" else 0.0
    gst = g * (brokerage + exchange_txn + sebi_fee)
    return FuturesFees(
        brokerage=brokerage,
        stt=stt,
        exchange_txn=exchange_txn,
        sebi_fee=sebi_fee,
        stamp_duty=stamp_duty,
        gst=gst,
    )


# ── Round-trip helpers (added by the A-arc cost substrate, 0f67798) ───────────
# Rebuilt on the verified per-leg primitives above. The A-arc rewrite of this
# module replaced `futures_fees` with these and shipped an UNVERIFIED rate
# schedule (self-marked "[VERIFY]") that dated the 0.0125% STT tier to
# 2019-10-01 rather than the Finance Act 2023 boundary, dropped the pre-2008
# no-STT era, and contradicted the frozen CARRY_NET_SPREAD_REPORT. The cited
# schedule is authoritative; these helpers are additive on top of it.

CANONICAL_CAPITAL = 20_000_000.0     # Rs 2 Cr — canonical paper capital
DEFAULT_BROKERAGE_CAP = 20.0         # Rs per executed order
DEFAULT_BROKERAGE_RATE = 0.0003      # 0.03% of notional


def brokerage_flat(notional, cap=DEFAULT_BROKERAGE_CAP, rate=DEFAULT_BROKERAGE_RATE):
    """Discount-broker futures brokerage: min(flat cap, rate x notional)."""
    return min(cap, rate * float(notional))


def futures_round_trip_fees(*, entry_value, exit_value, entry_date,
                            exit_date=None,
                            brokerage_cap=DEFAULT_BROKERAGE_CAP,
                            brokerage_rate=DEFAULT_BROKERAGE_RATE):
    """Full futures round trip: BUY at `entry_value`, SELL at `exit_value`.

    `exit_date` defaults to `entry_date` (square-off same session).
    """
    exit_date = exit_date or entry_date

    def _leg(side, value, d):
        brokerage = brokerage_flat(value, brokerage_cap, brokerage_rate)
        stt = value * stt_futures_rate(d) if side == "SELL" else 0.0
        exchange_txn = value * exchange_txn_rate(d)
        sebi = value * SEBI_FEE_RATE
        stamp = value * stamp_duty_rate(d) if side == "BUY" else 0.0
        gst = gst_rate(d) * (brokerage + exchange_txn + sebi)
        return FuturesFees(brokerage=brokerage, stt=stt,
                           exchange_txn=exchange_txn, sebi_fee=sebi,
                           stamp_duty=stamp, gst=gst)

    buy = _leg("BUY", entry_value, entry_date)
    sell = _leg("SELL", exit_value, exit_date)
    return FuturesFees(
        brokerage=buy.brokerage + sell.brokerage,
        stt=sell.stt,
        exchange_txn=buy.exchange_txn + sell.exchange_txn,
        sebi_fee=buy.sebi_fee + sell.sebi_fee,
        stamp_duty=buy.stamp_duty,
        gst=buy.gst + sell.gst,
    )


def breakeven_round_trip_bps(*, price, quantity, trade_date,
                             brokerage_cap=DEFAULT_BROKERAGE_CAP,
                             brokerage_rate=DEFAULT_BROKERAGE_RATE):
    """Round-trip cost in basis points of entry notional (exit at entry price)."""
    v = float(price) * float(quantity)
    fees = futures_round_trip_fees(entry_value=v, exit_value=v,
                                   entry_date=trade_date,
                                   brokerage_cap=brokerage_cap,
                                   brokerage_rate=brokerage_rate)
    return 10_000.0 * fees.total / v


def ticket_size_table(capital=CANONICAL_CAPITAL,
                      lot_sizes=(50, 75),
                      trade_date=date(2026, 8, 24),
                      price=25000.0):
    """Cost bps at the canonical notional expressed in lots of `lot_sizes`."""
    rows = []
    for lot in lot_sizes:
        notional = price * lot
        qty = int(capital // notional) or 1
        bps = breakeven_round_trip_bps(price=price, quantity=qty,
                                       trade_date=trade_date)
        rows.append({"lot_size": lot, "qty_lots": qty,
                     "notional_rs": round(notional * qty, 2),
                     "round_trip_cost_bps": round(bps, 3)})
    return rows
