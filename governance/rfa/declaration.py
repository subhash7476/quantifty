import hashlib
from dataclasses import dataclass
from typing import Optional

TEST_TYPES = {"one_sided", "two_sided"}
METRICS = {"rank_ic", "per_trade_pnl"}

_COUPLED_BAND_MSG = (
    "re-introduces the coupled-band defect (RFA_GATE_O1_REVIEW.md S1)."
)


@dataclass(frozen=True)
class Declaration:
    name: str
    methodology_version: str
    n_available: int
    cadence: str
    window: str
    test_type: str
    metric: str
    prior_exposure: str
    # rank_ic parameterisation (delta/sd bands)
    delta_lo: Optional[float] = None
    delta_hi: Optional[float] = None
    sd_lo: Optional[float] = None
    sd_hi: Optional[float] = None
    delta_provenance: str = ""
    sd_provenance: str = ""
    # per_trade_pnl parameterisation (Sharpe band)
    sharpe_lo: Optional[float] = None
    sharpe_hi: Optional[float] = None
    cadence_per_year: Optional[int] = None
    sharpe_provenance: str = ""


def validate(decl):
    if decl.n_available < 2:
        raise ValueError("n_available must be at least 2")
    if decl.test_type not in TEST_TYPES:
        raise ValueError(f"test_type must be one of {sorted(TEST_TYPES)}")
    if decl.metric not in METRICS:
        raise ValueError(f"metric must be one of {sorted(METRICS)}")
    if not decl.prior_exposure.strip():
        raise ValueError("prior_exposure is required and must be non-empty")

    if decl.metric == "rank_ic":
        _validate_rank_ic(decl)
    elif decl.metric == "per_trade_pnl":
        _validate_per_trade_pnl(decl)


def _validate_rank_ic(decl):
    if (decl.sharpe_lo is not None or decl.sharpe_hi is not None
            or decl.cadence_per_year is not None):
        raise ValueError(
            "rank_ic declares delta/sd bands; sharpe is derived. Supplying both "
            + _COUPLED_BAND_MSG
        )
    for field in ("delta_lo", "delta_hi", "sd_lo", "sd_hi"):
        if getattr(decl, field) is None:
            raise ValueError(f"{field} is required for rank_ic")
    for field in ("delta_provenance", "sd_provenance"):
        if not getattr(decl, field).strip():
            raise ValueError(f"{field} is required and must be non-empty")
    if decl.delta_lo > decl.delta_hi:
        raise ValueError("delta_lo must not exceed delta_hi")
    if decl.sd_lo > decl.sd_hi:
        raise ValueError("sd_lo must not exceed sd_hi")
    if decl.sd_lo <= 0:
        raise ValueError("sd_lo must be strictly positive")


def _validate_per_trade_pnl(decl):
    for field in ("delta_lo", "delta_hi", "sd_lo", "sd_hi"):
        if getattr(decl, field) is not None:
            raise ValueError(
                "per_trade_pnl declares a Sharpe band; delta/sd are derived. "
                "Supplying both " + _COUPLED_BAND_MSG
            )
    for field in ("sharpe_lo", "sharpe_hi", "cadence_per_year"):
        if getattr(decl, field) is None:
            raise ValueError(f"{field} is required for per_trade_pnl")
    if not decl.sharpe_provenance.strip():
        raise ValueError("sharpe_provenance is required and must be non-empty")
    if decl.sharpe_lo <= 0:
        raise ValueError("sharpe_lo must be strictly positive")
    if decl.sharpe_lo > decl.sharpe_hi:
        raise ValueError("sharpe_lo must not exceed sharpe_hi")
    if decl.cadence_per_year < 1:
        raise ValueError("cadence_per_year must be >= 1")


def digest_of(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()
