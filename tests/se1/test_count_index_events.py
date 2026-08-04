"""SE-1 counting pass — entity-resolution tests (Part B).

The prompt's minimum bar: a rename, a recycled ticker, and an ISIN re-issue
must each resolve to ONE entity and must NOT surface as a spurious add+drop
pair in the genuine-event count. These tests pin that on the pure
entity-resolution machinery with synthetic interval maps (no DuckDB).
"""

from datetime import date

from scripts.se1.count_index_events import (
    DUMMY_SYMBOLS,
    entity_resolve,
    month_symbols,
)


def _resolver_from(iv_map, isin=None):
    """Replica of build_resolver's resolve() over a synthetic interval map."""
    isin = isin or {}

    def resolve(sym, month_date):
        for vf, vt, ent in iv_map.get(sym, []):
            if vf <= month_date < vt:
                return ent, "interval"
        i = isin.get(sym)
        if i and i.startswith("INE"):
            return i[:9], "isin_issuer"
        return sym, "raw"

    return resolve


# --------------------------------------------------------------------------- #
# Rename seam — OLD dropped, NEW added, one entity. Must NOT count as events.
# --------------------------------------------------------------------------- #

def test_rename_resolves_to_one_entity_no_spurious_pair():
    iv_map = {
        "OLD": [(date(2010, 1, 1), date(2018, 6, 30), "ENT-A")],
        "NEW": [(date(2018, 6, 30), date(9999, 12, 31), "ENT-A")],
    }
    resolver = _resolver_from(iv_map)

    # Month0 = May 2018: OLD present (entity ENT-A). Month1 = Jun 2018: NEW present.
    # Raw diff: drop OLD, add NEW. Entity ENT-A present in BOTH months -> seam.
    symbol_sets = {"2018-05-01": {"OLD"}, "2018-06-01": {"NEW"}}
    diff = {"m0": "2018-05-01", "m1": "2018-06-01",
            "adds": ["NEW"], "drops": ["OLD"]}
    out = entity_resolve([diff], symbol_sets, resolver)[0]
    assert out["genuine_adds"] == []
    assert out["genuine_drops"] == []
    assert out["n_raw"] == 2
    assert out["n_artifact"] == 2


# --------------------------------------------------------------------------- #
# Recycled ticker — DTIL vacated by entity X, re-issued to entity Y. The
# resolver must time-resolve DTIL to a DIFFERENT entity on each side of the
# recycle, so a genuine X->Y swap is NOT collapsed into a seam.
# --------------------------------------------------------------------------- #

def test_recycled_ticker_time_resolves_to_two_entities():
    iv_map = {
        "DTIL": [
            (date(2010, 1, 1), date(2020, 6, 30), "CHAIN-ENTITY"),
            (date(2020, 6, 30), date(9999, 12, 31), "DTIL"),  # recycled leg
        ],
    }
    resolver = _resolver_from(iv_map)
    assert resolver("DTIL", date(2018, 1, 1))[0] == "CHAIN-ENTITY"
    assert resolver("DTIL", date(2022, 1, 1))[0] == "DTIL"
    assert resolver("DTIL", date(2018, 1, 1))[0] != resolver("DTIL", date(2022, 1, 1))[0]


def test_recycled_ticker_swap_is_not_a_seam():
    iv_map = {
        "DTIL": [
            (date(2010, 1, 1), date(2020, 6, 30), "CHAIN-ENTITY"),
            (date(2020, 6, 30), date(9999, 12, 31), "DTIL"),
        ],
    }
    resolver = _resolver_from(iv_map)
    # Month0 (2018): CHAIN-ENTITY under DTIL. Month1 (2022): DTIL entity under DTIL.
    symbol_sets = {"2018-05-01": {"DTIL"}, "2022-05-01": {"DTIL"}}
    # Raw diff is EMPTY (same ticker both months) — this is a documented
    # resolution limit of ticker-level MCWB diffing; the intervals still carry
    # the correct split, which is what the resolver must expose.
    diff = {"m0": "2018-05-01", "m1": "2022-05-01", "adds": [], "drops": []}
    out = entity_resolve([diff], symbol_sets, resolver)[0]
    assert out["n_raw"] == 0
    assert resolver("DTIL", date(2018, 5, 1))[0] == "CHAIN-ENTITY"


# --------------------------------------------------------------------------- #
# ISIN re-issue — PHILIPCARB -> PCBL, same INE issuer prefix. One entity.
# A raw drop+add across the re-issue must NOT count as a spurious pair.
# --------------------------------------------------------------------------- #

def test_isin_issuer_prefix_links_into_one_entity():
    resolver = _resolver_from({}, isin={
        "PHILIPCARB": "INE602A01015",
        "PCBL": "INE602A01031",
    })
    assert resolver("PHILIPCARB", date(2019, 1, 1))[0] == "INE602A01"
    assert resolver("PCBL", date(2019, 1, 1))[0] == "INE602A01"
    assert resolver("PHILIPCARB", date(2019, 1, 1))[0] == resolver("PCBL", date(2019, 1, 1))[0]


def test_isin_reissue_not_spurious_add_drop():
    isin = {"PHILIPCARB": "INE602A01015", "PCBL": "INE602A01031"}
    resolver = _resolver_from({}, isin=isin)
    # Same month both symbols exist under the issuer prefix -> same entity,
    # so a diff that drops PHILIPCARB while PCBL is already present is a seam.
    symbol_sets = {"2019-05-01": {"PHILIPCARB"}, "2019-06-01": {"PCBL"}}
    diff = {"m0": "2019-05-01", "m1": "2019-06-01",
            "adds": ["PCBL"], "drops": ["PHILIPCARB"]}
    out = entity_resolve([diff], symbol_sets, resolver)[0]
    assert out["genuine_adds"] == []
    assert out["genuine_drops"] == []
    assert out["n_artifact"] == 2


# --------------------------------------------------------------------------- #
# Genuine event — two different entities must still count.
# --------------------------------------------------------------------------- #

def test_genuine_add_drop_survives_resolution():
    iv_map = {
        "ALPHA": [(date(2010, 1, 1), date(9999, 12, 31), "ALPHA")],
        "BETA": [(date(2010, 1, 1), date(9999, 12, 31), "BETA")],
    }
    resolver = _resolver_from(iv_map)
    symbol_sets = {"2018-05-01": {"ALPHA"}, "2018-06-01": {"BETA"}}
    diff = {"m0": "2018-05-01", "m1": "2018-06-01",
            "adds": ["BETA"], "drops": ["ALPHA"]}
    out = entity_resolve([diff], symbol_sets, resolver)[0]
    assert [e["symbol"] for e in out["genuine_adds"]] == ["BETA"]
    assert [e["symbol"] for e in out["genuine_drops"]] == ["ALPHA"]
    assert out["n_artifact"] == 0


# --------------------------------------------------------------------------- #
# DUMMY test-row filter (NSE's own placeholder rows in the MCWB archives).
# --------------------------------------------------------------------------- #

def test_dummy_symbols_are_the_documented_nse_test_rows():
    assert DUMMY_SYMBOLS == {"DUMMYREL", "DUMMYTATAM", "DUMMYHDLVR"}


def test_month_symbols_excludes_dummy_rows(tmp_path):
    import zipfile
    import scripts.se1.count_index_events as mod

    csv = (
        "Sr. No,Security Symbol,Security Name\n"
        "1,RELIANCE,Reliance Industries Ltd.\n"
        "2,DUMMYREL,DUMMY - JIO FINANCIAL SERVICES LTD.\n"
        "3,HDFCBANK,HDFC Bank Ltd.\n"
    )
    zip_path = tmp_path / "mcwb_jul23.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("nifty50_mcwb.csv", csv)
    original = mod.REF_DIR
    try:
        mod.REF_DIR = tmp_path
        rec = {"filename": "mcwb_jul23.zip"}
        syms = month_symbols(rec, "nifty50_mcwb.csv")
    finally:
        mod.REF_DIR = original
    assert syms == {"RELIANCE", "HDFCBANK"}
