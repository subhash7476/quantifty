from dataclasses import dataclass


@dataclass(frozen=True)
class Estimate:
    """Estimate DTO (MSI-002 §4.7).

    An inferred approximation of a Latent Variable derived from Evidence.
    Carries both a value and quantified uncertainty per MSI-OD-005.
    """

    latent_variable: str
    value: float
    uncertainty: float
    dimension: str