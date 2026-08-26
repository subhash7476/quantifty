"""NSE intraday (non-delivery) equity transaction-cost model — ISD G6a.

Per-leg statutory + broker costs for an NSE cash-market INTRADAY equity trade
(square-off same session; no delivery, no F&O, no leverage). Sibling of the frozen
`delivery_fees.py` (same effective-dated schedule style); the two models must never
be conflated — see that module's header for the delivery/intraday boundary.

SOURCES — same gate (a)/(b) discipline as delivery_fees.py: every rate carries its
source + effective date; [VERIFY] flags a best-documented figure whose primary
circular could not be fetched directly. Each is a localized constant.

STT — intraday equity: SELL side only at 0.025%.
  - Finance Act 2004 as amended; the 0.02% -> 0.025% raise by Finance Act 2006 is
    the last change in force across the ISD window (2015->2026). Zero on the buy leg.

NSE capital-market transaction charge — ad-valorem, BOTH legs:
  - 2024-10-01 onward: 0.00297% (SEBI MII rationalization; SEBI PR No. 49/2024;
    NSE circular). [VERIFY exact figure against the circular.]
  - before: 0.00345% retail tier (tiered by monthly turnover; retail tier disclosed).

SEBI turnover fee — both legs, Rs 10/crore (0.0001%). Stable.

Stamp duty — BUY side only:
  - post-2020-07-01: 0.003% (nationalized central regime).
  - pre-2020-07-01: state-wise; documented Maharashtra-representative 0.01%
    assumption (same disclosure as delivery_fees.py).

GST / service tax — on (brokerage + exchange_txn + sebi_fee) ONLY; STT and stamp
are outside the base (asserted by test). Schedule identical to delivery_fees.py.

Brokerage — discount-broker intraday: min(Rs 20 or 0.03% of trade value) per EXECUTED
order, whichever is LOWER, both legs. The flat floor dominates small tickets and
therefore sets a minimum sensible ticket size at any capital basis (spec Q4:
canonical paper capital Rs 2,00,00,000).

Out of scope: DP charges (delivery-only), STT on buyback, F&O, leverage.
"""
from dataclasses import dataclass
from datetime import date

# Canonical paper capital (operator decision Q4, ISD spec §10) — lives here so
# the cost model and its sizing basis ship together; scripts/isd re-exports.
CANONICAL_CAPITAL = 20_000_000.0

DEFAULT_BROKERAGE_CAP = 20.0        # Rs per executed order
DEFAULT_BROKERAGE_RATE = 0.0003     # 0.03% of trade value

SEBI_FEE_RATE = 0.000001

_STT_INTRADAY_SCHEDULE = (
    # Sell-side only at 0.025% since Finance Act 2006; stable through 2026.
    (date(1900, 1, 1), 0.00025),
)
_EXCHANGE_TXN_SCHEDULE = (
    (date(2024, 10, 1), 0.0000297),
    (date(1900, 1, 1), 0.0000345),
)
_STAMP_DUTY_SCHEDULE = (
    (date(2020, 7, 1), 0.00003),
    (date(1900, 1, 1), 0.0001),
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


def brokerage_flat(trade_value,
                   cap=DEFAULT_BROKERAGE_CAP,
                   rate=DEFAULT_BROKERAGE_RATE):
    """Discount-broker intraday brokerage: min(flat cap, rate x value)."""
    return min(cap, rate * float(trade_value))


def stt_intraday_rate(trade_date):
    """STT rate for intraday equity — applies to the SELL leg ONLY."""
    return _resolve(trade_date, _STT_INTRADAY_SCHEDULE)


def exchange_txn_rate(trade_date):
    return _resolve(trade_date, _EXCHANGE_TXN_SCHEDULE)


def stamp_duty_rate(trade_date):
    return _resolve(trade_date, _STAMP_DUTY_SCHEDULE)


def gst_rate(trade_date):
    return _resolve(trade_date, _GST_SCHEDULE)


@dataclass(frozen=True)
class IntradayEquityFees:
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


def round_trip_fees(*, entry_value, exit_value, entry_date, exit_date=None,
                    brokerage_cap=DEFAULT_BROKERAGE_CAP,
                    brokerage_rate=DEFAULT_BROKERAGE_RATE):
    """Full intraday round trip: BUY at `entry_value`, SELL at `exit_value`.

    `exit_date` defaults to `entry_date` (square-off same session). Returns the
    summed IntradayEquityFees over both legs.
    """
    exit_date = exit_date or entry_date

    def _leg(side, value, d):
        g = gst_rate(d)
        brokerage = brokerage_flat(value, brokerage_cap, brokerage_rate)
        stt = value * stt_intraday_rate(d) if side == "SELL" else 0.0
        exchange_txn = value * exchange_txn_rate(d)
        sebi = value * SEBI_FEE_RATE
        stamp = value * stamp_duty_rate(d) if side == "BUY" else 0.0
        gst = g * (brokerage + exchange_txn + sebi)
        return IntradayEquityFees(brokerage=brokerage, stt=stt,
                                  exchange_txn=exchange_txn, sebi_fee=sebi,
                                  stamp_duty=stamp, gst=gst)

    buy = _leg("BUY", entry_value, entry_date)
    sell = _leg("SELL", exit_value, exit_date)
    return IntradayEquityFees(
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
    fees = round_trip_fees(entry_value=v, exit_value=v, entry_date=trade_date,
                           brokerage_cap=brokerage_cap,
                           brokerage_rate=brokerage_rate)
    return 10_000.0 * fees.total / v


def ticket_size_table(capital=CANONICAL_CAPITAL,
                      book_widths=(10, 20, 40, 100),
                      trade_date=date(2026, 8, 24),
                      price=1000.0):
    """G6 report artifact: per-name ticket notional and cost bps at each book width."""
    rows = []
    for w in book_widths:
        names_per_side = max(w // 2, 1)
        ticket = capital / (2 * names_per_side)
        qty = int(ticket / price)
        bps = breakeven_round_trip_bps(price=price, quantity=max(qty, 1),
                                       trade_date=trade_date)
        rows.append({"book_width": w, "names_per_side": names_per_side,
                     "ticket_rs": round(ticket, 2), "qty_at_1000": qty,
                     "round_trip_cost_bps": round(bps, 2)})
    return rows
