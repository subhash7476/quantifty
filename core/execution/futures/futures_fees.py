"""NSE F&O futures transaction-cost model (A construct, index intraday).

Per-leg statutory + broker costs for an NSE derivative-segment FUTURES trade
(index or stock futures; this model is instrument-agnostic — it prices the
notional). Sibling of the frozen `core/execution/equity/intraday_fees.py` and
`delivery_fees.py`; the three models must never be conflated. The A construct
(A_CONSTRUCT_DEFINITION.md) trades Nifty futures at the canonical notional and
applies this model per session.

SOURCES — same gate (a)/(b) discipline as delivery_fees.py: every rate carries
its source + effective date. [VERIFY] flags a best-documented figure whose
primary circular could not be fetched directly. Each is a localized constant.

STT (Securities Transaction Tax) — futures: SELL leg ONLY.
  - 0.02% w.e.f. 2024-10-01 (Finance (No.2) Act 2024; the STT raise that also
    took options premium STT from 0.1% to 0.2%).
  - 0.0125% 2019-10-01 -> 2024-09-30 (Finance (No.2) Act 2019).
  - 0.01% 2008-10-01 -> 2019-09-30 (Finance Act 2008 cut futures STT from
    0.017% to 0.01%). [VERIFY the 2008 boundary against the Act]
  - 0.017% before 2008-10-01 (Finance Act 2004, as amended) — outside the
    A window (store starts 2012) but carried for schedule completeness.
  Zero on the buy leg. Applies on the SELL side at exit (and on any roll).

NSE F&O transaction charge (derivative segment, futures) — both legs:
  - 0.00173% w.e.f. 2024-10-01 (SEBI MII charge rationalization; SEBI PR
    No. 49/2024, NSE circular effective 2024-10-01 — same circular that cut
    cash-segment to 0.00297%). [VERIFY exact Rs/lakh against the circular]
  - 0.0021% before 2024-10-01 (long-standing NSE futures rate card).
    [VERIFY start-of-era figure; the 2024-10-01 boundary is certain]

SEBI turnover fee — both legs, Rs 10/crore (0.0001%). Stable (same constant
as the equity models; SEBI (Turnover Fees) Regulations).

Stamp duty — BUY side only, F&O:
  - Post-2020-07-01: 0.002% uniform central regime (Finance Act 2019
    nationalization; futures stamped at the derivative-segment schedule).
  - Pre-2020-07-01: STATE-WISE (no national rate). DOCUMENTED ASSUMPTION:
    0.002% buyer-side, the Maharashtra-representative F&O schedule, disclosed
    here as an approximation (same disclosure style as delivery_fees.py).
  [VERIFY both figures against state + central schedules]

GST / service tax — on (brokerage + exchange_txn + sebi_fee) ONLY; STT and
stamp are outside the base (asserted by test). Schedule identical to the
equity models: 18% GST (2017-07-01+), 15% (2016-06), 14.5% (2015-11), 14%
(2015-06), 12.36% prior.

Brokerage — discount-broker futures: min(Rs 20 or 0.03% of notional) per
EXECUTED order, whichever is LOWER, both legs. The flat floor dominates small
tickets; at the canonical ₹2Cr notional the floor (₹20) applies and is ~0.001
bp — immaterial, but carried because 1-lot-era tickets (pre-2016, ₹5-10L)
would otherwise be undercosted.

Out of scope: options, delivery/DP charges, leverage, spread/hedge relief.
"""
from dataclasses import dataclass
from datetime import date

from core.execution.equity.intraday_fees import CANONICAL_CAPITAL

DEFAULT_BROKERAGE_CAP = 20.0        # Rs per executed order
DEFAULT_BROKERAGE_RATE = 0.0003     # 0.03% of notional

SEBI_FEE_RATE = 0.000001

_STT_FUTURES_SCHEDULE = (
    (date(2024, 10, 1), 0.0002),
    (date(2019, 10, 1), 0.000125),
    (date(2008, 10, 1), 0.0001),    # [VERIFY 2008 boundary]
    (date(1900, 1, 1), 0.00017),
)
_EXCHANGE_TXN_SCHEDULE = (
    (date(2024, 10, 1), 0.0000173),  # [VERIFY Rs/lakh vs NSE circular]
    (date(1900, 1, 1), 0.000021),    # [VERIFY start-of-era figure]
)
_STAMP_DUTY_SCHEDULE = (
    (date(2020, 7, 1), 0.00002),     # [VERIFY central F&O schedule]
    (date(1900, 1, 1), 0.00002),     # Maharashtra-representative assumption
)
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


def brokerage_flat(notional,
                   cap=DEFAULT_BROKERAGE_CAP,
                   rate=DEFAULT_BROKERAGE_RATE):
    """Discount-broker futures brokerage: min(flat cap, rate x notional)."""
    return min(cap, rate * float(notional))


def stt_futures_rate(trade_date):
    """STT rate for futures — applies to the SELL leg ONLY."""
    return _resolve(trade_date, _STT_FUTURES_SCHEDULE)


def exchange_txn_rate(trade_date):
    return _resolve(trade_date, _EXCHANGE_TXN_SCHEDULE)


def stamp_duty_rate(trade_date):
    return _resolve(trade_date, _STAMP_DUTY_SCHEDULE)


def gst_rate(trade_date):
    return _resolve(trade_date, _GST_SCHEDULE)


@dataclass(frozen=True)
class FuturesFees:
    brokerage: float
    stt: float          # sell leg only
    exchange_txn: float
    sebi_fee: float
    stamp_duty: float   # buy leg only
    gst: float

    @property
    def total(self):
        return (self.brokerage + self.stt + self.exchange_txn + self.sebi_fee
                + self.stamp_duty + self.gst)


def futures_round_trip_fees(*, entry_value, exit_value, entry_date,
                            exit_date=None,
                            brokerage_cap=DEFAULT_BROKERAGE_CAP,
                            brokerage_rate=DEFAULT_BROKERAGE_RATE):
    """Full futures round trip: BUY at `entry_value`, SELL at `exit_value`.

    `exit_date` defaults to `entry_date` (square-off same session — the A
    construct is EOD-flat). Returns the summed FuturesFees over both legs.
    """
    exit_date = exit_date or entry_date

    def _leg(side, value, d):
        g = gst_rate(d)
        brokerage = brokerage_flat(value, brokerage_cap, brokerage_rate)
        stt = value * stt_futures_rate(d) if side == "SELL" else 0.0
        exchange_txn = value * exchange_txn_rate(d)
        sebi = value * SEBI_FEE_RATE
        stamp = value * stamp_duty_rate(d) if side == "BUY" else 0.0
        gst = g * (brokerage + exchange_txn + sebi)
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
