from datetime import date

from scripts.ptms.enumerate_nonratio_ca import classify_purpose, entity_at


def test_demerger_and_spin_off_are_demerger():
    assert classify_purpose("Demerger") == {"DEMERGER"}
    assert classify_purpose("Spin Off") == {"DEMERGER"}


def test_scheme_of_arrangement_including_misspelling():
    assert classify_purpose("Scheme of Arrangement") == {"SCHEME"}
    assert "SCHEME" in classify_purpose("Scheme of Arangement- Bonus - 1 Debenture for 1 Equity Share held")


def test_bonus_debentures_and_preference_are_in_kind_not_ratio():
    assert classify_purpose("Scheme of Arrangement - Bonus Debentures 1:1") == {"SCHEME", "IN_KIND"}
    assert classify_purpose("Bonus Preference Shares 1:1") == {"IN_KIND"}
    assert classify_purpose("1 CCDs for every 10 Equity Shares") == {"IN_KIND"}


def test_rights_issue():
    assert classify_purpose("Rights 1:18 @ Premium Rs 1255/- per share") == {"RIGHTS"}


def test_special_dividend_in_combined_purpose():
    assert classify_purpose(
        "Annual General Meeting/Dividend - Rs 8 Per Share/Special Dividend - Rs 4 Per Share"
    ) == {"SPECIAL_DIVIDEND"}
    assert classify_purpose("AGM/Spl Div- Rs 5/- Div-Rs 3/-") == {"SPECIAL_DIVIDEND"}
    assert classify_purpose("Final Dividend Rs 20/- Per Share and One Time Special Dividend Rs 10/- Per Share") == {
        "SPECIAL_DIVIDEND"
    }


def test_buyback_variants():
    for p in ["Buyback", "Buy Back", "Buy-Back", "Buy Back-Tender Offer", "Buyback of Shares"]:
        assert classify_purpose(p) == {"BUYBACK"}


def test_ratio_events_are_ratio_only():
    assert classify_purpose("Bonus 1:1") == {"RATIO"}
    assert classify_purpose("Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share") == {"RATIO"}
    assert classify_purpose("FV Splt Frm Rs 10 To Rs 2") == {"RATIO"}
    assert classify_purpose("Bonus 1:1/Dividend- Rs 3 Per Share") == {"RATIO"}


def test_ordinary_dividend_and_meetings_are_unclassified():
    assert classify_purpose("Annual General Meeting/Dividend - Rs 9 Per Share") == set()
    assert classify_purpose("Interim Dividend - Rs 15 Per Share (Purpose Revised)") == set()
    assert classify_purpose("Interest Payment") == set()


def test_entity_at_is_time_aware_for_recycled_tickers():
    intervals = [
        ("DTIL", date(2010, 1, 1), date(2019, 12, 31), "DHUNSERI_VENTURES"),
        ("DTIL", date(2020, 1, 1), date(9999, 12, 31), "DHUNSERI_TEA"),
    ]
    assert entity_at(intervals, "DTIL", date(2015, 6, 1)) == "DHUNSERI_VENTURES"
    assert entity_at(intervals, "DTIL", date(2021, 6, 1)) == "DHUNSERI_TEA"
    assert entity_at(intervals, "OTHER", date(2021, 6, 1)) is None
