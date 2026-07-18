"""MTO parser unit tests — 4 fixture classes:
1. Standard pre-2020 format (7-field data rows, 6-col header)
2. 2020-era Trade Date variant (shorter settlement line)
3. Malformed/rejected lines
4. Non-EQ series pass-through
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "parse_mto", ROOT / "scripts" / "csmp" / "parse_mto.py")
parse_mto = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parse_mto)

parse_mto_file = parse_mto.parse_mto_file


# ── 1. Standard pre-2020 format ──────────────────────────────────────────────

STD_HEADER = """\
Security Wise Delivery Position - Compulsory Rolling Settlement
10,MTO,15012015,465541077,0001541
Trade Date <15-JAN-2015>,Settlement Type <N>,Settlement No <2015011>,Settlement Date <19-JAN-2015>
Record Type,Sr No,Name of Security,Quantity Traded,Deliverable Quantity(gross across client level),% of Deliverable Quantity to Traded Quantity
"""

STD_DATA = """\
20,1,20MICRONS,EQ,127717,68086,53.31
20,2,3IINFOTECH,EQ,213,,
20,3,3MINDIA,EQ,289,204,70.59
"""


def test_pre2020_standard():
    rows, rejects = parse_mto_file(STD_HEADER + STD_DATA)
    assert len(rejects) == 0
    assert len(rows) == 3
    assert rows[0] == ("20MICRONS", "EQ", 127717, 68086, 53.31)
    assert rows[1] == ("3IINFOTECH", "EQ", 213, None, None)
    assert rows[2] == ("3MINDIA", "EQ", 289, 204, 70.59)


# ── 2. 2020-era Trade Date variant (shorter settlement line) ─────────────────

VAR_2020 = """\
Security Wise Delivery Position - Compulsory Rolling Settlement
10,MTO,15012020,400000000,0001000
Trade Date <15-JAN-2020>,Settlement Type <N>,Settlement Date <17-JAN-2020>
Record Type,Sr No,Name of Security,Quantity Traded,Deliverable Quantity(gross across client level),% of Deliverable Quantity to Traded Quantity
20,1,ABB,EQ,5000,2500,50.00
20,2,ACC,EQ,10000,8000,80.00
"""


def test_2020_variant():
    rows, rejects = parse_mto_file(VAR_2020)
    assert len(rejects) == 0
    assert len(rows) == 2
    assert rows[0] == ("ABB", "EQ", 5000, 2500, 50.00)
    assert rows[1] == ("ACC", "EQ", 10000, 8000, 80.00)


# ── 3. Malformed/rejected lines ──────────────────────────────────────────────

MALFORMED = """\
Security Wise Delivery Position - Compulsory Rolling Settlement
10,MTO,15012015,465541077,0001541
Trade Date <15-JAN-2015>,Settlement Type <N>,Settlement No <2015011>,Settlement Date <19-JAN-2015>
Record Type,Sr No,Name of Security,Quantity Traded,Deliverable Quantity(gross across client level),% of Deliverable Quantity to Traded Quantity
20,1,VALID,EQ,100,50,50.00
20,2,,EQ,100,50,50.00
20,3,BADSYMBOL,,abc,def,ghi
20,4,BADDELIV,EQ,100,bad,50.00
20,5,VALID2,EQ,200,100,50.00
20,6,TOOMANY,EQ,100,50,25.00,extra,fields
"""


def test_malformed_rejected():
    rows, rejects = parse_mto_file(MALFORMED)
    assert len(rows) == 2
    assert rows[0] == ("VALID", "EQ", 100, 50, 50.00)
    assert rows[1] == ("VALID2", "EQ", 200, 100, 50.00)
    assert len(rejects) >= 4
    reject_reasons = [r[2] for r in rejects]
    assert any("empty symbol" in r for r in reject_reasons)
    assert any("bad qty_traded" in r for r in reject_reasons)
    assert any("bad deliv_qty" in r for r in reject_reasons)
    assert any("too many fields" in r for r in reject_reasons)


# ── 4. Non-EQ series pass-through ────────────────────────────────────────────

NON_EQ = """\
Security Wise Delivery Position - Compulsory Rolling Settlement
10,MTO,15012015,465541077,0001541
Trade Date <15-JAN-2015>,Settlement Type <N>,Settlement No <2015011>,Settlement Date <19-JAN-2015>
Record Type,Sr No,Name of Security,Quantity Traded,Deliverable Quantity(gross across client level),% of Deliverable Quantity to Traded Quantity
20,1,SGBJAN28,GB,10,10,100.00
20,2,SHRIRAMPPS,SM,5000,4500,90.00
20,3,RELIANCE,EQ,100000,50000,50.00
"""


def test_non_eq_series():
    rows, rejects = parse_mto_file(NON_EQ)
    assert len(rejects) == 0
    assert len(rows) == 3
    assert rows[0] == ("SGBJAN28", "GB", 10, 10, 100.00)
    assert rows[1] == ("SHRIRAMPPS", "SM", 5000, 4500, 90.00)
    assert rows[2] == ("RELIANCE", "EQ", 100000, 50000, 50.00)


# ── 5. Empty file ────────────────────────────────────────────────────────────

def test_empty_file():
    rows, rejects = parse_mto_file("")
    assert len(rows) == 0
    assert len(rejects) == 0


# ── 6. Real file parse (integration) ─────────────────────────────────────────

def test_real_mto_file():
    path = ROOT / "data" / "mto_probe" / "MTO_15012015.DAT"
    if not path.exists():
        pytest.skip("MTO_15012015.DAT not found — run probe first")
    text = path.read_text(encoding="utf-8", errors="replace")
    rows, rejects = parse_mto_file(text)
    assert len(rows) > 1000
    assert len(rejects) == 0
    eq_rows = [r for r in rows if r[1] == "EQ"]
    assert len(eq_rows) > 1000
    non_eq = [r for r in rows if r[1] != "EQ"]
    assert len(non_eq) > 0
