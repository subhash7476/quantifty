from datetime import date

from scripts.a_index_intraday.certify_index_slice import era_for


def test_vendor_era():
    assert era_for(date(2022, 6, 1)) == "vendor"


def test_native_era():
    assert era_for(date(2024, 6, 1)) == "native"


def test_cas_era_starts_2026_08_03():
    assert era_for(date(2026, 7, 31)) == "native"
    assert era_for(date(2026, 8, 3)) == "cas"
