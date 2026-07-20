import math

from scipy.stats import nct, t as student_t

ALPHA = 0.05


def power_at(delta, sd, n, two_sided):
    if not (sd > 0) or n < 2:
        return 0.0
    tail = ALPHA / 2 if two_sided else ALPHA
    tcrit = student_t.ppf(1 - tail, df=n - 1)
    ncp = delta * math.sqrt(n) / sd
    return float(nct.sf(tcrit, n - 1, ncp))


def n_required(delta, sd, target_power, two_sided, n_max=1_000_000):
    if power_at(delta, sd, n_max, two_sided) < target_power:
        return None
    lo, hi = 2, n_max
    while lo < hi:
        mid = (lo + hi) // 2
        if power_at(delta, sd, mid, two_sided) >= target_power:
            hi = mid
        else:
            lo = mid + 1
    return lo
