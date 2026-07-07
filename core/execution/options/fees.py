"""NSE index-options transaction-cost model (MSRP Phase-7 precondition gate (b)).

Per-order (one leg, one side) statutory + broker costs for NSE index options.
Rate schedules are effective-dated so a 2023->2026 backtest applies the rate in
force on each trade date. All percentage charges apply to PREMIUM turnover
(premium x quantity in units), never notional.

Sources (verified 2026-07-07):
  - STT on sale of option (of premium): 0.05% -> 0.0625% (2023-04-01, Finance Act
    2023) -> 0.1% (2024-10-01, Finance (No.2) Act 2024) -> 0.15% (2026-04-01,
    Budget 2026).
  - NSE transaction charge (of premium): 0.0495% -> 0.03503% (2024-10-01, SEBI
    true-to-label circular).
  - SEBI turnover fee: 0.0001% (Rs 10/crore). Stamp duty: 0.003% of premium,
    buy side only. GST: 18% on (brokerage + exchange txn + SEBI fee).
  - Brokerage: Rs 20 flat per executed order (discount broker), matching the
    equity model in ExecutionHandler._calculate_fees.

Out of scope: STT on exercise (0.125% of intrinsic, buyer side) — the Phase-7 D1
design exits every position before expiry (contract selection DTE >= 2, same-day
open->close holding), so no leg is ever carried to settlement.
"""

from dataclasses import dataclass
from datetime import date

BROKERAGE_PER_ORDER = 20.0
GST_RATE = 0.18
SEBI_FEE_RATE = 0.000001        # 0.0001% of premium turnover
STAMP_DUTY_RATE_BUY = 0.00003   # 0.003% of premium turnover, buy side only

# (effective_from, rate) — newest first; first row with effective_from <= trade_date wins.
_STT_SELL_SCHEDULE = (
    (date(2026, 4, 1), 0.0015),
    (date(2024, 10, 1), 0.001),
    (date(2023, 4, 1), 0.000625),
    (date(1900, 1, 1), 0.0005),
)
_EXCHANGE_TXN_SCHEDULE = (
    (date(2024, 10, 1), 0.0003503),
    (date(1900, 1, 1), 0.000495),
)


def stt_sell_rate(trade_date: date) -> float:
    for effective_from, rate in _STT_SELL_SCHEDULE:
        if trade_date >= effective_from:
            return rate
    raise ValueError(f"trade_date {trade_date} predates the STT schedule")


def exchange_txn_rate(trade_date: date) -> float:
    for effective_from, rate in _EXCHANGE_TXN_SCHEDULE:
        if trade_date >= effective_from:
            return rate
    raise ValueError(f"trade_date {trade_date} predates the exchange txn schedule")


@dataclass(frozen=True)
class OptionOrderFees:
    brokerage: float
    stt: float
    exchange_txn: float
    sebi: float
    gst: float
    stamp_duty: float

    @property
    def total(self) -> float:
        return (self.brokerage + self.stt + self.exchange_txn
                + self.sebi + self.gst + self.stamp_duty)


def option_order_fees(*, premium: float, quantity: int, side: str,
                      trade_date: date) -> OptionOrderFees:
    """Fees for one executed option order.

    Args:
        premium: option premium per unit (Rs).
        quantity: units (lots x lot size).
        side: "BUY" or "SELL".
        trade_date: execution date — selects the statutory rates in force.
    """
    if side not in ("BUY", "SELL"):
        raise ValueError(f"side must be BUY or SELL, got {side!r}")

    turnover = premium * quantity
    stt = turnover * stt_sell_rate(trade_date) if side == "SELL" else 0.0
    exchange_txn = turnover * exchange_txn_rate(trade_date)
    sebi = turnover * SEBI_FEE_RATE
    stamp = turnover * STAMP_DUTY_RATE_BUY if side == "BUY" else 0.0
    gst = GST_RATE * (BROKERAGE_PER_ORDER + exchange_txn + sebi)
    return OptionOrderFees(
        brokerage=BROKERAGE_PER_ORDER,
        stt=stt,
        exchange_txn=exchange_txn,
        sebi=sebi,
        gst=gst,
        stamp_duty=stamp,
    )
