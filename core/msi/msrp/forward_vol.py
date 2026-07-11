"""HAR-RV+VIX authoring utilities for the forward-volatility PublishedArtifact v2.

Implements exactly the frozen MSRP Phase-1 Research Dossier (commit ``d9233b1``):
  - RV construction from intraday 1m log-returns (dossier S5)
  - HAR daily/weekly/monthly aggregates (dossier S6 feature library)
  - OLS fit of ``log RV_{t+1} ~ b0 + b1 log RV_d + b2 log RV_w + b3 log RV_m + b4 log VIX``
    on the development window only (dossier S7)
  - residual sigma for the log-normal point estimate and state-dependent uncertainty

This module is RESEARCH AUTHORING tooling (A1). It is NOT executed at runtime; the
runtime artifact is the frozen ``PublishedArtifact`` it produces. No research decisions
are made here beyond what the frozen dossier specifies.
"""

from typing import Dict, Mapping, Tuple

import numpy as np
import pandas as pd

# --- Frozen, dossier-mandated constants -------------------------------------

WEEKLY_WINDOW = 5      # RV^{(w)}: mean of RV over the last 5 trading days (dossier S6)
MONTHLY_WINDOW = 22    # RV^{(m)}: mean of RV over the last 22 trading days (dossier S6)
FEATURE_NAMES: Tuple[str, ...] = ("rv_daily", "rv_weekly", "rv_monthly", "vix_close")


def compute_daily_rv(closes_by_day: Mapping[pd.Timestamp, np.ndarray]) -> pd.Series:
    """Daily realized volatility from intraday 1m closes (dossier S5).

    ``RV_t = sqrt( sum_k r_{t,k}^2 )`` with ``r_{t,k} = ln(P_{t,k} / P_{t,k-1})``.

    Intraday only: the overnight return (previous close -> today's open) is EXCLUDED.
    Scale-invariant (no annualization). Days with fewer than two 1m prints produce no
    usable RV and are dropped.

    Args:
        closes_by_day: mapping of trading-day timestamp -> 1m close prices for that day,
            in chronological order.

    Returns:
        Series indexed by trading day of intraday realized volatility ``RV_t``.
    """
    rv: Dict[pd.Timestamp, float] = {}
    for day, closes in closes_by_day.items():
        prices = np.asarray(closes, dtype=float)
        if prices.size < 2:
            continue
        log_returns = np.log(prices[1:] / prices[:-1])
        rv[day] = float(np.sqrt(np.sum(log_returns ** 2)))
    return pd.Series(rv, name="rv").sort_index()


def compute_har_features(rv: pd.Series) -> pd.DataFrame:
    """HAR daily / weekly / monthly aggregates (dossier S6).

    All aggregates are as-of the close of day ``t`` (trailing, leak-free):
      - ``rv_daily``   = RV_t                          (1-day)
      - ``rv_weekly``  = mean of RV over last 5 days   (includes t)
      - ``rv_monthly`` = mean of RV over last 22 days  (includes t)

    The first usable row begins once the 22-day monthly aggregate is defined
    (dossier S6: "~22 trading days into the series").
    """
    features = pd.DataFrame(index=rv.index)
    features["rv_daily"] = rv
    features["rv_weekly"] = rv.rolling(window=WEEKLY_WINDOW, min_periods=WEEKLY_WINDOW).mean()
    features["rv_monthly"] = rv.rolling(window=MONTHLY_WINDOW, min_periods=MONTHLY_WINDOW).mean()
    return features.dropna()


def fit_har_rv_vix(
    rv: pd.Series, vix: pd.Series, dev_start: str, dev_end: str
) -> Dict[str, float]:
    """Fit the frozen HAR-RV+VIX log specification by OLS on the dev window (dossier S7/S8).

    Model::

        log RV_{t+1} = b0 + b1 log RV^{(d)}_t + b2 log RV^{(w)}_t
                     + b3 log RV^{(m)}_t + b4 log VIX_t + e_t

    Fitting uses ONLY the development window ``[dev_start, dev_end]``. The target
    ``RV_{t+1}`` requires the next trading day to exist within the dev window, so the
    last dev day contributes no row — and, critically, a target whose date ``t+1`` falls
    in the sealed held-out window (``> dev_end``) is NEVER used (dossier S1 invariant:
    held-out is sealed). India VIX is inner-joined to the RV index by trading day
    (dossier S12.2: holiday mismatch drops the day, no forward-fill).

    Returns:
        Dict with frozen keys ``b0..b4`` and ``sigma`` (residual std of the log-space
        residuals, ``sqrt(SSR/(n-p))``, the standard OLS estimator). These are the only
        quantities the runtime artifact needs.
    """
    features = compute_har_features(rv)

    vix_aligned = vix.reindex(features.index)
    design = features.join(vix_aligned.rename("vix"))
    design = design.loc[(design.index >= dev_start) & (design.index <= dev_end)]
    design = design.dropna(subset=["rv_daily", "rv_weekly", "rv_monthly", "vix"])

    # Target: log RV_{t+1} aligned so features are as-of close of day t (leak-free).
    # The target RV series is clamped to <= dev_end BEFORE shifting, so the held-out
    # window is never touched as a target (dossier S1: held-out sealed). The last dev
    # day (dev_end) thus has no in-window t+1 -> NaN -> dropped.
    rv_in_window = rv.loc[rv.index <= pd.Timestamp(dev_end)]
    next_rv = rv_in_window.shift(-1).reindex(design.index)
    design = design.assign(target_log_rv_next=np.log(next_rv))
    design = design.dropna(subset=["target_log_rv_next"])

    X = np.column_stack(
        [
            np.ones(len(design)),
            np.log(design["rv_daily"].to_numpy()),
            np.log(design["rv_weekly"].to_numpy()),
            np.log(design["rv_monthly"].to_numpy()),
            np.log(design["vix"].to_numpy()),
        ]
    )
    y = design["target_log_rv_next"].to_numpy()

    # Closed-form OLS (numpy lstsq). Uniquely determined; no solver degrees of freedom.
    coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)
    residuals = y - X @ coeffs
    n_obs, n_params = X.shape
    sigma = float(np.sqrt(np.sum(residuals ** 2) / (n_obs - n_params)))

    return {
        "b0": float(coeffs[0]),
        "b1": float(coeffs[1]),
        "b2": float(coeffs[2]),
        "b3": float(coeffs[3]),
        "b4": float(coeffs[4]),
        "sigma": sigma,
        "n_obs": int(n_obs),
    }


def linear_predictor(coeffs: Mapping[str, float], rv_daily: float, rv_weekly: float,
                     rv_monthly: float, vix: float) -> float:
    """Log-space linear predictor ``mu = x_t . b`` (dossier S7).

    Equivalent (rank-equivalent) discriminant score for AUC; the runtime ``evaluate()``
    uses this to build the log-normal point estimate.
    """
    return (
        coeffs["b0"]
        + coeffs["b1"] * np.log(rv_daily)
        + coeffs["b2"] * np.log(rv_weekly)
        + coeffs["b3"] * np.log(rv_monthly)
        + coeffs["b4"] * np.log(vix)
    )


def point_estimate(mu: float, sigma: float) -> float:
    """``E[RV_{t+1}] = exp(mu + sigma^2 / 2)`` under the log-normal residual
    assumption (dossier S7)."""
    return float(np.exp(mu + (sigma ** 2) / 2.0))


def predictive_uncertainty(value: float, sigma: float) -> float:
    """State-dependent predictive spread (dossier S7 / Phase-2 finding Mo2).

    The log-normal predictive standard deviation, ``value * sqrt(exp(sigma^2) - 1)``.
    Derived from the SAME log-normal assumption that yields the point estimate
    ``E[RV] = exp(mu + sigma^2/2)``: under log-normality the standard deviation of
    ``RV_{t+1}`` is ``sqrt((exp(sigma^2)-1) * exp(2*mu + sigma^2))`` = ``value *
    sqrt(exp(sigma^2)-1)``. It therefore (a) scales with the predicted level and (b)
    widens in high-vol states, exactly as Mo2 requires. It uses residual spread only
    (parameter-estimation uncertainty is out of scope per finding Mo3). Not a research
    decision: the consequence of the frozen log-normal assumption.
    """
    return float(value * np.sqrt(np.exp(sigma ** 2) - 1.0))
