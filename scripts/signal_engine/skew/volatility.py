import math
from typing import Literal, Optional
from scipy.optimize import root_scalar
from core.risk.greeks.black76_engine import Black76Engine


class VolatilityInversion:
    """
    Invert implied volatility from option prices using Black-76 model.
    
    Uses Newton-Raphson via scipy.optimize.root_scalar to find sigma
    such that Black76_price(sigma) = market_price.
    """

    @staticmethod
    def calculate_iv(
        F: float,
        K: float,
        T: float,
        r: float,
        market_price: float,
        option_type: Literal['CE', 'PE'],
        method: str = 'newton'
    ) -> Optional[float]:
        """
        Calculate implied volatility by solving Black76_price(sigma) = market_price.

        Args:
            F: Underlying price
            K: Strike price
            T: Time to expiry (years)
            r: Risk-free rate
            market_price: Observed option price (midpoint of bid/ask if available)
            option_type: 'CE' or 'PE'
            method: Optimization method ('newton' or 'brentq')

        Returns:
            Implied volatility (sigma) or None if convergence fails

        Note:
            Uses Black76 model for Indian index/stock options.
            Risk-free rate set to 0.07 (7% RBI repo rate baseline).
        """
        if T <= 0:
            return None

        if market_price <= 0:
            return None

        intrinsic = max(F - K, 0.0) if option_type == 'CE' else max(K - F, 0.0)
        if market_price < intrinsic * 0.9:
            return None

        def objective(sigma: float) -> float:
            try:
                calc_price = Black76Engine.calculate_price(F, K, T, r, sigma, option_type)
                return calc_price - market_price
            except (ValueError, ZeroDivisionError):
                return float('inf')

        try:
            if method == 'newton':
                result = root_scalar(
                    objective,
                    x0=0.2,
                    fprime=lambda sigma: Black76Engine.calculate_greeks(F, K, T, r, sigma, option_type).vega / 0.01,
                    method='newton',
                    rtol=1e-6,
                    maxiter=50
                )
            else:
                result = root_scalar(
                    objective,
                    bracket=(0.01, 3.0),
                    method='brentq',
                    rtol=1e-6,
                    maxiter=50
                )

            if result.converged:
                iv = result.root
                if iv < 0.01 or iv > 5.0:
                    return None
                return iv
            else:
                return None

        except (ValueError, RuntimeError):
            return None

    @staticmethod
    def find_strike_at_delta(
        F: float,
        T: float,
        r: float,
        sigma: float,
        target_delta: float,
        option_type: Literal['CE', 'PE'],
        strikes: list[float]
    ) -> Optional[float]:
        """
        Find the strike where delta ≈ target_delta via linear interpolation.

        Args:
            F: Underlying price
            T: Time to expiry (years)
            r: Risk-free rate
            sigma: Volatility (use ATM vol as approximation)
            target_delta: Target delta (0.25 for 25-delta)
            option_type: 'CE' or 'PE'
            strikes: Available strikes sorted ascending

        Returns:
            Interpolated strike at target_delta or None if out of range
        """
        if not strikes or T <= 0:
            return None

        deltas = []
        for K in strikes:
            try:
                greeks = Black76Engine.calculate_greeks(F, K, T, r, sigma, option_type)
                deltas.append(abs(greeks.delta))
            except (ValueError, ZeroDivisionError):
                deltas.append(None)

        valid = [(s, d) for s, d in zip(strikes, deltas) if d is not None]
        if not valid:
            return None

        valid_sorted = sorted(valid, key=lambda x: x[1])

        for i in range(len(valid_sorted) - 1):
            s1, d1 = valid_sorted[i]
            s2, d2 = valid_sorted[i + 1]

            if d1 <= target_delta <= d2:
                weight = (target_delta - d1) / (d2 - d1) if d2 != d1 else 0.5
                return s1 + weight * (s2 - s1)

        if abs(valid_sorted[0][1] - target_delta) < 0.05:
            return valid_sorted[0][0]
        if abs(valid_sorted[-1][1] - target_delta) < 0.05:
            return valid_sorted[-1][0]

        return None