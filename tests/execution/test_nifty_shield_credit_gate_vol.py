"""The credit gate's reference must be priced at each leg's OWN implied vol.

Pricing every leg at India VIX overstated a 6-DTE bull put spread by ~30%, so
the 0.90 floor refused structures the market was paying 97-99% of fair value for
(`docs/reports/index_research/NIFTY_SHIELD_CREDIT_FLOOR_CALIBRATION_2026-09-09.md`).
"""
import duckdb
import pytest

from core.execution.options.nifty_shield_marks import (
    ChainSnapshotMarksSource, StaticMarksSource,
)
from core.execution.options.nifty_shield_pricing import fair_structure_credit

SPOT = 23431.5
DTE = 6.0
RATE = 0.065

# The measured 2026-09-15 put surface: near leg cheaper in vol than the far leg.
BULL_PUT_SPREAD = [
    {"side": "SELL", "strike": 23350, "option_type": "PE", "iv": 0.1019},
    {"side": "BUY", "strike": 23050, "option_type": "PE", "iv": 0.1183},
]
VIX_FLAT = 0.1159


def test_prices_each_leg_at_its_own_vol():
    credit = fair_structure_credit(BULL_PUT_SPREAD, SPOT, DTE, RATE)

    assert credit is not None
    assert credit == pytest.approx(54.2, abs=1.5)


def test_a_flat_vol_across_both_legs_overstates_the_credit():
    """Why the flat-vol parameter was removed rather than defaulted: on a
    vertical it overprices the near leg and underprices the far one, and credit
    is their difference, so the two errors compound."""
    per_leg = fair_structure_credit(BULL_PUT_SPREAD, SPOT, DTE, RATE)
    flat = fair_structure_credit(
        [{**leg, "iv": VIX_FLAT} for leg in BULL_PUT_SPREAD], SPOT, DTE, RATE)

    assert flat > per_leg * 1.25


def test_the_market_credit_clears_a_90pct_floor_only_under_per_leg_pricing():
    market_credit = 52.90                     # 23350 PE 73.90 - 23050 PE 21.00
    per_leg = fair_structure_credit(BULL_PUT_SPREAD, SPOT, DTE, RATE)
    flat = fair_structure_credit(
        [{**leg, "iv": VIX_FLAT} for leg in BULL_PUT_SPREAD], SPOT, DTE, RATE)

    assert market_credit / per_leg > 0.90     # gate passes, as it should
    assert market_credit / flat < 0.90        # the old behaviour: always refused


@pytest.mark.parametrize("bad_iv", [None, 0.0, -0.1])
def test_a_leg_with_no_usable_iv_makes_the_gate_unavailable_not_a_pass(bad_iv):
    """None means "gate unavailable" to the caller. It must never silently fall
    back to one vol for every leg — that is the defect being fixed."""
    legs = [dict(BULL_PUT_SPREAD[0]), {**BULL_PUT_SPREAD[1], "iv": bad_iv}]

    assert fair_structure_credit(legs, SPOT, DTE, RATE) is None


def test_static_source_reports_only_the_vols_it_was_given():
    src = StaticMarksSource({"A": 10.0, "B": 5.0}, implied_vols={"A": 0.11})

    assert src.implied_vols(["A", "B"]) == {"A": 0.11}


def test_chain_source_converts_the_feeds_percent_iv_to_a_decimal(tmp_path):
    """The feed publishes 11.03; Black-Scholes needs 0.1103. Getting this wrong
    is a 100x vol error that would price every reference at intrinsic."""
    db = tmp_path / "chain.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE option_chain_snapshot ("
                "snapshot_timestamp TIMESTAMP, tradingsymbol VARCHAR, "
                "ltp DOUBLE, iv DOUBLE)")
    con.execute("INSERT INTO option_chain_snapshot VALUES "
                "('2026-09-09 13:00:00', 'NIFTY23350PE', 73.90, 10.19), "
                "('2026-09-09 13:00:00', 'NIFTY23050PE', 21.00, 11.83)")
    con.close()

    got = ChainSnapshotMarksSource(str(db)).implied_vols(
        ["NIFTY23350PE", "NIFTY23050PE"])

    assert got == {"NIFTY23350PE": pytest.approx(0.1019),
                   "NIFTY23050PE": pytest.approx(0.1183)}


def test_chain_source_omits_legs_the_snapshot_has_no_iv_for(tmp_path):
    db = tmp_path / "chain.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE option_chain_snapshot ("
                "snapshot_timestamp TIMESTAMP, tradingsymbol VARCHAR, "
                "ltp DOUBLE, iv DOUBLE)")
    con.execute("INSERT INTO option_chain_snapshot VALUES "
                "('2026-09-09 13:00:00', 'HAS_IV', 73.90, 10.19), "
                "('2026-09-09 13:00:00', 'NULL_IV', 21.00, NULL), "
                "('2026-09-09 13:00:00', 'ZERO_IV', 21.00, 0.0)")
    con.close()

    got = ChainSnapshotMarksSource(str(db)).implied_vols(
        ["HAS_IV", "NULL_IV", "ZERO_IV"])

    assert list(got) == ["HAS_IV"]


def test_every_marks_implementation_must_answer_for_implied_vols():
    """A wrapper that forwards only part of the interface answers silently for
    the rest — the `instrument_keys` regression of 2026-09-08. Abstract, so a
    non-forwarding implementation fails at construction, not in a live window."""
    from core.execution.options.nifty_shield_marks import OptionMarksSource

    class Incomplete(OptionMarksSource):
        def marks(self, symbols):
            return {}

        def instrument_keys(self, symbols):
            return {}

        def snapshot_age_s(self, now=None):
            return None

    with pytest.raises(TypeError, match="implied_vols"):
        Incomplete()
