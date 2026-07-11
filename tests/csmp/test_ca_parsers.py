"""Face-value and bonus-ratio parsing from NSE CF-CA PURPOSE text.

Every string below is a verbatim PURPOSE from `CF-CA-equities-*.csv`. The cases
carrying a symbol name in the comment are ones the previous integer-scanning
parser got wrong.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "ingest_ca", ROOT / "scripts" / "csmp" / "ingest_corporate_actions.py")
ingest_ca = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ingest_ca)

parse_split_clause = ingest_ca.parse_split_clause
parse_bonus_clause = ingest_ca.parse_bonus_clause


@pytest.mark.parametrize("purpose, expected", [
    ("Fv Split Rs.10 To Re.1", (10.0, 1.0)),
    ("Face Value Split From Rs.10/- To Rs.5/-", (10.0, 5.0)),
    ("Face Value Split From Rs 10 To Rs 2", (10.0, 2.0)),
    ("Face Value Split Rs.10/- To Rs.2/-", (10.0, 2.0)),
    ("Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 5/- Per Share",
     (10.0, 5.0)),
    # STLTECH — 'to' glued to the currency token
    ("Bon 1:1/Fv Spl Rs.5tors.2", (5.0, 2.0)),
    ("Bon 1:1/Fv Spl Rs.5tore.1", (5.0, 1.0)),
    # KRBL — trailing dividend amount must not be mistaken for a face value
    ("Fv Spl-Rs10tore1/Div-1.50", (10.0, 1.0)),
    # SHARONBIO — no currency prefix on either side
    ("Bonus 1:1 / Face Value Split From 10/- To Face Value 2/-", (10.0, 2.0)),
    # VERTOZ — a consolidation runs the other way and must be representable
    ("Consolidation Of Equity Shares From Re 1 Per Share To Rs 10 Per Share",
     (1.0, 10.0)),
])
def test_parses_face_values_from_the_face_value_clause(purpose, expected):
    assert parse_split_clause(purpose)[0] == expected


@pytest.mark.parametrize("purpose, expected", [
    # DPSCLTD — the 22 belongs to the bonus ratio, not the face value
    ("Bonus 22:1 And Face Value Split From Rs.10/- To Re.1/-", (10.0, 1.0)),
    # KCP — 'Rs.2.50' is a dividend; a decimal-blind scan reads it as 2 and 50
    ("1st Interim Dividend Rs.2.50 Per Share And Face Value Split From Rs.10/- "
     "To Re.1/- (Purpose Revised)", (10.0, 1.0)),
    # EMAMILTD — the Rs.6 dividend precedes the clause
    ("Dividend Rs.6/- Per Share And Face Value Split From Rs.2/- To Re.1/-",
     (2.0, 1.0)),
    # DWARKESH — a Rs 10 dividend and a 10->1 split in one string
    (" Annual General Meeting/Dividend - Rs 10 Per Share/Face Value Split "
     "(Sub-Division) - From Rs 10/- Per Share To Re 1/- Per Share (Purpose Revised)",
     (10.0, 1.0)),
])
def test_ignores_numbers_outside_the_face_value_clause(purpose, expected):
    assert parse_split_clause(purpose)[0] == expected


@pytest.mark.parametrize("purpose, reason", [
    # MONNETISPA — a reduction then a consolidation has no single price factor
    ("Capital Reduction Rs 10 To Rs 3.30 / Consolidation Rs 3.30 To Rs.10",
     "capital_reduction_ambiguous"),
    ("Capital Reduction", "capital_reduction_ambiguous"),
])
def test_rejects_rather_than_guesses(purpose, reason):
    value, why = parse_split_clause(purpose)
    assert value is None
    assert why == reason


@pytest.mark.parametrize("purpose", [
    "Annual General Meeting",
    # A bare 'Spl' abbreviates 'Special Dividend', not 'Split'.
    "Spl Div-Rs.80/- Per Share",                     # HEROMOTOCO
    "Div-Fin Rs.2 + Spl Re.1",                       # HUHTAMAKI
    "Agm/Spl Div- Rs.5/- Div-7.5/-",                 # SUNDARMFIN
    "Spl Int Div-Rs.100 P Shr Purpose Revised",      # ENGINERSIN
])
def test_no_split_clause_is_not_a_reject(purpose):
    assert parse_split_clause(purpose) == (None, "no_split_clause")


def test_degenerate_equal_face_values_are_rejected_not_stored_as_a_no_op():
    value, why = parse_split_clause("Face Value Split From Rs 10 To Rs 10")
    assert value is None
    assert why == "degenerate_equal_face_value"


@pytest.mark.parametrize("purpose, expected", [
    ("Bonus 1:1", (1, 1)),
    ("Bonus 4:1", (4, 1)),
    ("Bonus 3:4", (3, 4)),
    ("Bonus 1: 2", (1, 2)),
    ("Bonus - 1:1 And Face Value Split From Rs. 10 To Rs. 2", (1, 1)),
    ("Bonus 1 : 1 / Face Value Split From Rs 10/- Each To Rs 2/- Each", (1, 1)),
    ("Fv Spl-Rs10tors5/Bon-2:1", (2, 1)),
    ("Bonus Shares In The Ratio Of 1:1", (1, 1)),
])
def test_parses_bonus_ratio(purpose, expected):
    assert parse_bonus_clause(purpose)[0] == expected


def test_bonus_factor_convention_is_held_over_total():
    # 'Bonus a:b' issues a new shares for every b held.
    new, held = parse_bonus_clause("Bonus 22:1")[0]
    assert held / (new + held) == pytest.approx(1 / 23)


@pytest.mark.parametrize("purpose", [
    "Sch Of Agmt- Bonus Deb1:1",                     # BRITANNIA
    "Scheme Of Arrangement - Bonus Debentures 6:1",  # DRREDDY
    "Scheme Of Arrangement - Bonus Ncrps 4:1",       # TVSMOTOR
    "Bonus Preference Shares 21:1",                  # ZEEL
    "Bonus 1 Dvr : 10 Eq Share",                     # GUJNRECOKE
])
def test_non_equity_bonuses_never_produce_a_price_factor(purpose):
    value, why = parse_bonus_clause(purpose)
    assert value is None
    assert why == "non_equity_bonus"


def test_absent_bonus_is_distinguished_from_a_rejected_one():
    assert parse_bonus_clause("Face Value Split From Rs.10/- To Re.1/-") == (None, None)
