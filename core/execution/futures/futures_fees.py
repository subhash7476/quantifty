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

STT (Securities Transaction Tax) — derivatives, SELL side only.
  - Pre-2024-10-01: 0.0125% (Rs 12.5/lakh) on sell side. Rate in force for
    most of the dev window (2008–2024).
  - From 2024-10-01: 0.02% (Rs 20/lakh) on sell side, raised under the
    Finance (No. 2) Act 2024 / Budget 2024 (effective 2024-10-01).
  - Sources: [caclubindia](
      https://www.caclubindia.com/articles/securities-transaction-tax-rate-hikes-on-f-amp-o-w-e-f-1st-october-24-55626.asp),
      [ICICI Direct](
      https://icicidirect.com/research/equity/finace/new-stt-rules-in-futures-and-options-trading).
    [VERIFY the pre-hike effective date against NSE/CBDT circular before committing.]

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
# Futures STT sell-side only. Finance (No. 2) Act 2024 raised to 0.02%
# effective 2024-10-01. Pre-hike rate was 0.0125% (not 0.01%).
# Sources: caclubindia, ICICI Direct.
_STT_FUTURES_SCHEDULE = (
    (date(2024, 10, 1), 0.0002),     # 0.02% — Budget 2024 F&O STT hike.
    (date(2008, 6, 1), 0.000125),    # 0.0125% — pre-hike futures rate.
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
