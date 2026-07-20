import hashlib
from dataclasses import dataclass

TEST_TYPES = {"one_sided", "two_sided"}
METRICS = {"rank_ic", "per_trade_pnl"}

_PROVENANCE_FIELDS = ("delta_provenance", "sd_provenance", "prior_exposure")


@dataclass(frozen=True)
class Declaration:
    name: str
    methodology_version: str
    delta_lo: float
    delta_hi: float
    sd_lo: float
    sd_hi: float
    delta_provenance: str
    sd_provenance: str
    prior_exposure: str
    n_available: int
    cadence: str
    window: str
    test_type: str
    metric: str


def validate(decl):
    for field in _PROVENANCE_FIELDS:
        if not getattr(decl, field).strip():
            raise ValueError(f"{field} is required and must be non-empty")
    if decl.delta_lo > decl.delta_hi:
        raise ValueError("delta_lo must not exceed delta_hi")
    if decl.sd_lo > decl.sd_hi:
        raise ValueError("sd_lo must not exceed sd_hi")
    if decl.sd_lo <= 0:
        raise ValueError("sd_lo must be strictly positive")
    if decl.n_available < 2:
        raise ValueError("n_available must be at least 2")
    if decl.test_type not in TEST_TYPES:
        raise ValueError(f"test_type must be one of {sorted(TEST_TYPES)}")
    if decl.metric not in METRICS:
        raise ValueError(f"metric must be one of {sorted(METRICS)}")


def digest_of(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()
