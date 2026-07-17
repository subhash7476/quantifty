"""NSE delivery-equity transaction-cost model (CSMP gate (d)).

Per-leg (one side, one delivery trade) statutory + broker costs for NSE cash-market
DELIVERY equity — the long-only monthly-rebalance construct (both legs held to
delivery; no intraday, no F&O, no leverage). Rate schedules are effective-dated so a
2012->2026 backtest applies the rate in force on each trade date, mirroring the options
model in core/execution/options/fees.py.

DELIVERY vs INTRADAY (do not conflate): the platform's intraday fee model
(ExecutionHandler._calculate_fees) applies STT on the sell side only at 0.025% (the
non-delivery rate). Delivery equity is taxed on BOTH legs at 0.1% each (see STT
below). This module is delivery-only.

------------------------------------------------------------------------------
SOURCES — every rate carries its primary source + effective date. A number may not
stand without the evidence it summarizes (gate (a)/(b) discipline). Where a primary
circular could not be fetched directly (NSE/SEBI sites block automated retrieval), the
value is the best-documented figure and is flagged with [VERIFY]; each is a localized
constant an era-revision will correct in one line without touching any past computation
(determinism / acceptance criterion 6).

STT (Securities Transaction Tax) — delivery equity, BOTH legs.
  - 0.1% on buyer AND 0.1% on seller of delivery-based equity (the rate that defines a
    transaction as delivery: physical/electronic delivery of shares).
  - Source: Finance Act 2004, clause 98 read with the STT Rules, w.e.f. 2004-10-01. The
    rate for *delivery* equity has been stable across the CSMP dev window (2012->2026);
    the STT changes in this period (Finance Act 2016, 2023, Finance (No.2) Act 2024)
    affected *derivatives and intraday*, not the delivery rate. Intraday (non-delivery)
    is sell-only at 0.025% (Finance Act 2006 raised it from 0.02% to 0.025%) — out of
    scope here but documented to prevent the delivery/intraday conflation.

NSE capital-market (cash-segment) transaction charge — ad-valorem on turnover, both legs.
  - 0.00345% (Rs 3.45/lakh), retail tier, corroborated by the platform's own
    ExecutionHandler._calculate_fees.
  - 2024-10-01 reduction to 0.00297% (Rs 2.97/lakh) under SEBI's MII charge
    rationalization (SEBI board decision Aug 2024; SEBI press release PR No. 49/2024,
    2024-08-27; NSE circular effective 2024-10-01). [VERIFY exact Rs/lakh against the
    NSE circular number; era boundary is certain, the post-Oct-2024 figure is the
    best-documented value.]
  - NOTE: NSE CM charges are tiered by monthly turnover; this uses the retail tier,
    appropriate for a single-name delivery strategy (disclosed approximation).

SEBI turnover fee — ad-valorem on turnover, both legs, Rs 10/crore (0.0001%).
  - Source: SEBI (Turnover Fees) Regulations; mirrors core/execution/options/fees.py
    (constant, stable across the dev window).

Stamp duty — BUY side only.
  - Post-2020-07-01: 0.003% on buyer, uniform central regime. Indian Stamp Act 1899,
    Schedule I Article as amended by the Finance Act 2019 (w.e.f. 2020-07-01) which
    nationalized marketable-security stamp duty on the buyer of equity delivery.
  - Pre-2020-07-01: STATE-WISE — there was no single national rate (the trickiest era
    boundary). DOCUMENTED ASSUMPTION: 0.01% buyer-side, the Maharashtra demat-equity
    schedule where the exchange clearing infrastructure sat, taken as a representative
    rate. This is an approximation disclosed here, not a national rate (acceptance
    criterion 4: a single disclosed, cited assumption is acceptable; a silent one is not).

GST (post-2017) / service tax (pre-2017) — on (brokerage + exchange_txn + sebi_fee) ONLY.
  STT and stamp duty are OUTSIDE the GST base (asserted by a test, acceptance criterion 3).
  The dev window spans the service-tax -> GST transition, so the schedule carries every
  rate era:
    2017-07-01: 18% GST (CGST + IGST; brokerage/txn/SEBI service subsumed into GST).
    2016-06-01: 15%  (service tax 14% + Krishi Kalyan Cess 0.5%).
    2015-11-15: 14.5% (service tax 14% + Swachh Bharat Cess 0.5%).
    2015-06-01: 14%  (Finance Act 2015 raised service tax from 12.36% to 14%).
    prior:      12.36% (service tax 12% + education cess 3%).

Brokerage — default Rs 0 (discount broker, ZERO brokerage on delivery; CSMP charter
  section 1). A named parameter; a non-zero schedule is representable without a code
  change (do not scatter the assumption).

DP (depository participant) charge — flat per sell scrip per day, SELL leg only, plus
  18% GST on the flat charge. Broker-recovered, not statutory; Rs 13.5 is a common
  discount-broker demat-debit charge. Parameterized; default is a representative
  discount-broker value. NOT ad-valorem (per sell line, not per rupee of turnover).

Out of scope: intraday non-delivery STT (0.025% sell), F&O, leverage, short selling,
  buyback/STT-on-buyback — none arise for a long-only monthly-rebalance delivery book.
------------------------------------------------------------------------------
"""

from dataclasses import dataclass
from datetime import date

# Brokerage default — Rs 0 (discount-broker delivery; charter section 1).
DEFAULT_BROKERAGE = 0.0
# DP flat charge (Rs, per sell scrip per day) — representative discount-broker value.
DEFAULT_DP_CHARGE_FLAT = 13.5

SEBI_FEE_RATE = 0.000001  # 0.0001% of turnover (Rs 10/crore) — both legs, stable.

# (effective_from, rate) — newest first; first row with effective_from <= trade_date wins.
# Delivery STT 0.1% on each leg, stable since 2004-10-01 (Finance Act 2004).
_STT_DELIVERY_SCHEDULE = (
    (date(2004, 10, 1), 0.001),
)
# NSE capital-market transaction charge — ad-valorem, both legs.
_EXCHANGE_TXN_SCHEDULE = (
    (date(2024, 10, 1), 0.0000297),  # 0.00297% — SEBI MII rationalization.
    (date(1900, 1, 1), 0.0000345),   # 0.00345% — retail tier.
)
# Stamp duty — BUY side only (see schedule comments above).
_STAMP_DUTY_SCHEDULE = (
    (date(2020, 7, 1), 0.00003),  # 0.003% buyer — uniform central regime.
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


def stt_delivery_rate(trade_date):
    """STT rate for delivery equity (applied to BOTH buy and sell legs)."""
    return _resolve(trade_date, _STT_DELIVERY_SCHEDULE)


def exchange_txn_rate(trade_date):
    """NSE capital-market transaction-charge rate (fraction of turnover)."""
    return _resolve(trade_date, _EXCHANGE_TXN_SCHEDULE)


def stamp_duty_rate(trade_date):
    """Stamp-duty rate (fraction of buy-side turnover)."""
    return _resolve(trade_date, _STAMP_DUTY_SCHEDULE)


def gst_rate(trade_date):
    """GST (post-2017) / service-tax (pre-2017) rate on the statutory-services base."""
    return _resolve(trade_date, _GST_SCHEDULE)


@dataclass(frozen=True)
class DeliveryEquityFees:
    brokerage: float
    stt: float
    exchange_txn: float
    sebi_fee: float
    stamp_duty: float
    gst: float
    dp_charge: float  # flat depository charge + its GST; SELL only

    @property
    def total(self):
        return (self.brokerage + self.stt + self.exchange_txn + self.sebi_fee
                + self.stamp_duty + self.gst + self.dp_charge)


def delivery_equity_fees(*, side, trade_value, trade_date,
                         brokerage=DEFAULT_BROKERAGE,
                         dp_charge_flat=DEFAULT_DP_CHARGE_FLAT):
    """Fees for one executed delivery-equity leg.

    Args:
        side: "BUY" or "SELL".
        trade_value: notional traded value in Rs (price x quantity).
        trade_date: execution date — selects the statutory rates in force.
        brokerage: flat brokerage per leg, Rs (default 0, discount delivery).
        dp_charge_flat: flat depository charge per sell scrip per day, Rs
            (default 13.5; applied on SELL only, GST added).
    """
    if side not in ("BUY", "SELL"):
        raise ValueError(f"side must be BUY or SELL, got {side!r}")

    g = gst_rate(trade_date)
    stt = trade_value * stt_delivery_rate(trade_date)
    exchange_txn = trade_value * exchange_txn_rate(trade_date)
    sebi_fee = trade_value * SEBI_FEE_RATE
    stamp_duty = trade_value * stamp_duty_rate(trade_date) if side == "BUY" else 0.0
    gst = g * (brokerage + exchange_txn + sebi_fee)
    dp_charge = dp_charge_flat * (1 + g) if side == "SELL" else 0.0
    return DeliveryEquityFees(
        brokerage=brokerage,
        stt=stt,
        exchange_txn=exchange_txn,
        sebi_fee=sebi_fee,
        stamp_duty=stamp_duty,
        gst=gst,
        dp_charge=dp_charge,
    )
