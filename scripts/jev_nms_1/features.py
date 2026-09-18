"""JEV-NMS-1 §6/§7 point-in-time features f1-f9 for one state.

Information set I_t: the session's bars stamped <= t-1 plus C_prev (the
previous session's 15:29 close from the step-1 artifact). Nothing else is read.
Values are natural-log returns in basis points; rounding per §6 (bp 1 decimal,
er_30 3 decimals, f1 integer, negative zero written as 0).
"""
from __future__ import annotations

import math
from decimal import Decimal

FIELDS = ("minutes_since_open", "gap_bp", "ret_open_bp", "ret_15_bp", "ret_30_bp",
          "rv_30_bp", "range_30_bp", "er_30", "twap_dist_bp")
BP = 1e4


def fixed(x: float, places: int) -> float:
    v = float(format(x, f".{places}f"))
    return 0.0 if v == 0 else v


def is_tie(x: float, places: int) -> bool:
    """True if the exact binary value lies exactly halfway between two outputs."""
    scaled = Decimal(x).scaleb(places)
    return scaled - scaled.to_integral_value(rounding="ROUND_FLOOR") == Decimal("0.5")


def raw_features(bars: list[tuple], t: int, c_prev: float) -> dict:
    """bars: (open, high, low, close) for minutes 0 (= 09:15) .. t-1 at least; t = slot index."""
    close = [b[3] for b in bars]
    o = bars[0][0]
    p_t = close[t - 1]
    rets = [math.log(close[i] / close[i - 1]) for i in range(t - 30, t)]
    abs_sum = sum(abs(r) for r in rets)
    f5 = math.log(p_t / close[t - 31]) * BP
    return {
        "minutes_since_open": t,
        "gap_bp": math.log(o / c_prev) * BP,
        "ret_open_bp": math.log(p_t / o) * BP,
        "ret_15_bp": math.log(p_t / close[t - 16]) * BP,
        "ret_30_bp": f5,
        "rv_30_bp": math.sqrt(sum(r * r for r in rets)) * BP,
        "range_30_bp": math.log(max(b[1] for b in bars[t - 30:t]) /
                                min(b[2] for b in bars[t - 30:t])) * BP,
        "er_30": abs(f5) / (abs_sum * BP) if abs_sum != 0 else 0.0,
        "twap_dist_bp": math.log(p_t / (sum(close[:t]) / t)) * BP,
        "_er_30_from_rounded_f5": abs(fixed(f5, 1)) / (abs_sum * BP) if abs_sum != 0 else 0.0,
    }


def rounded(raw: dict) -> dict:
    out = {}
    for k in FIELDS:
        if k == "minutes_since_open":
            out[k] = int(raw[k])
        elif k == "er_30":
            out[k] = fixed(raw[k], 3)
        else:
            out[k] = fixed(raw[k], 1)
    return out
