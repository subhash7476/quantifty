"""PSB-1 Prompt 5-C — the committed disposition register.

The SOLE permitted exclusion from any arm. Per name, by reason — not "default to
fragment" (Review 10 §5.3 was overruled by PSB1_CERTIFICATION_METHODOLOGY.md §8).
Exceptions are DATA, not code: every structural filter is banned, and a residue item
is excluded only by membership here.

Sources (merged into one register):
  1. ca_scope_exclusions     — gate-(b)'s documented residue, mapped to entity (D5).
  2. ca_evidence_exceptions  — gate-(b)'s open evidence failures (OMAXE + the f>=0.75
                               no-reprice class). Arm D re-surfaces these; Arm A
                               catches two whose price move is CA-shaped (KWALITY,
                               SAHPETRO).
  3. ETF_SPLITS              — ETF unit splits, legitimately absent from a
                               split/bonus register (the register covers EQUITIES;
                               an ETF unit split is a fund-level action, INE* never
                               applies — the ISIN is INF*).
  4. DEMERGERS               — corporate demergers/scheme reconstructions whose factor
                               is legitimately absent from the split/bonus register
                               (a demerger is not a face-value change; the resulting
                               price drop has no single adjustment factor).

Built by `scripts/psb1/disposition_register.py` from the enumerated Arm A residue on
the post-5-B store. If the store changes, the register must be re-enumerated and
re-committed — a new item NOT in the register HALTs.
"""
from __future__ import annotations

from datetime import date


# ──────────────────────────────────────────────────────────────────────────────
# Committed: ETF unit splits (INF* ISIN, or no-ISIN gold/silver ETFs).
# An ETF unit split is a fund scheme action; it has no INE* corporate-action factor.
# ──────────────────────────────────────────────────────────────────────────────
ETF_SPLITS = {
    ("ABSLBANETF", date(2021, 11, 25)),
    ("ABSLNN50ET", date(2021, 11, 25)),
    ("ALPL30IETF", date(2024, 5, 10)),
    ("AUTOIETF", date(2024, 3, 1)),
    ("BANKBEES", date(2019, 12, 19)),
    ("BANKNIFTY1", date(2026, 2, 27)),
    ("BSE500IETF", date(2021, 10, 28)),
    ("BSLNIFTY", date(2021, 11, 25)),
    ("BSLSENETFG", date(2021, 11, 25)),
    ("CONS", date(2026, 2, 27)),
    ("DSPQ50ETF", date(2026, 7, 3)),
    ("FMCGIETF", date(2024, 5, 10)),
    ("GOLD1", date(2021, 7, 22)),
    ("GROWWGOLD", date(2026, 2, 6)),
    ("GROWWSLVR", date(2026, 2, 6)),
    ("HBANKETF", date(2024, 2, 2)),
    ("HDFCLOWVOL", date(2023, 10, 20)),
    ("HDFCMID150", date(2023, 10, 20)),
    ("HDFCMOMENT", date(2023, 10, 20)),
    ("HDFCNEXT50", date(2023, 10, 20)),
    ("HDFCNIF100", date(2023, 10, 20)),
    ("HDFCNIFETF", date(2021, 2, 17)),
    ("HDFCPVTBAN", date(2024, 2, 2)),
    ("HDFCSENETF", date(2021, 2, 17)),
    ("HDFCSENETF", date(2024, 2, 2)),
    ("HEALTHADD", date(2026, 7, 3)),
    ("HNGSNGBEES", date(2019, 12, 19)),
    ("ICICIBANKN", date(2022, 9, 1)),
    ("ICICIM150", date(2024, 5, 10)),
    ("ICICINXT50", date(2018, 11, 16)),
    ("ICICIQTY30", date(2024, 5, 10)),
    ("ICICITECH", date(2022, 9, 1)),
    ("KOTAKMID50", date(2026, 2, 27)),
    ("KOTAKNIFTY", date(2017, 7, 27)),
    ("LOWVOLIETF", date(2024, 3, 1)),
    ("MIDSELIETF", date(2024, 5, 10)),
    ("MOLOWVOL", date(2022, 8, 11)),
    ("MOMOMENTUM", date(2022, 8, 11)),
    ("MON100", date(2021, 6, 17)),
    ("NIF100IETF", date(2024, 5, 10)),
    ("NIFTYBEES", date(2019, 12, 19)),
    ("NIFTYBETA", date(2023, 9, 25)),
    ("NV20", date(2026, 2, 27)),
    ("NV20IETF", date(2024, 3, 1)),
    ("PSUBNKBEES", date(2019, 12, 19)),
    ("QNIFTY", date(2026, 2, 13)),
}

# ──────────────────────────────────────────────────────────────────────────────
# Committed: demergers / scheme reconstructions (INE* ISIN).
# A demerger splits the company; the price drop has no single adjustment factor in
# the split/bonus register (it is not a face-value change). The resulting entity
# trades ex-demerger at a lower price — CA-shaped but legitimately factor-less.
# ──────────────────────────────────────────────────────────────────────────────
DEMERGERS = {
    ("8KMILES", date(2020, 9, 7)),
    ("BORORENEW", date(2020, 3, 6)),
    ("CREATIVEYE", date(2023, 8, 25)),
    ("DALMIACEM", date(2010, 9, 24)),
    ("HERITGFOOD", date(2023, 1, 20)),
    ("IDFC", date(2015, 10, 1)),
    ("IIFL", date(2019, 5, 30)),
    ("KAMDHENU", date(2022, 9, 6)),
    ("KESORAMIND", date(2025, 3, 10)),
    ("MID-DAY", date(2011, 1, 20)),
    ("OCCL", date(2024, 7, 1)),
    ("PIRLIFE", date(2011, 12, 23)),
    ("RAYMOND", date(2025, 5, 14)),
    ("SABEVENTS", date(2023, 7, 10)),
    ("SHILPI", date(2018, 2, 7)),
    ("SIEMENS", date(2025, 4, 7)),
    ("STAR", date(2013, 12, 19)),
    ("SUVEN", date(2020, 1, 21)),
}

# ──────────────────────────────────────────────────────────────────────────────
# Register builder: merges committed lists with the store's exception tables.
# ──────────────────────────────────────────────────────────────────────────────
# Committed: relistings with verified capital events (Arm B).
# These are cross-symbol entity handoffs that produce >20% adjusted returns even
# after the correct factor is applied, because the gap contains real economic
# changes (suspension, restructuring, re-listing). Each entry carries evidence:
# old/new ISIN, NSE rename record, capital event (or its absence), missed sessions.
# ──────────────────────────────────────────────────────────────────────────────
RE_LISTINGS = {
    ("INDOSOLAR", date(2025, 6, 19)):
        "relisting_after_suspension: INDOSOLAR (INE866K01015) -> WAAREEINDO; "
        "factor 100 applied; 1473 missed sessions; boundary +65.1% after adjustment",
    ("CLCIND", date(2026, 1, 30)):
        "relisting_after_suspension: SPENTEX (INE376C01020) -> CLCIND; "
        "factor 100 applied; 1343 missed sessions; boundary -88.1% after adjustment",
    ("NEUEON", date(2025, 12, 23)):
        "relisting_after_suspension: NTL (INE333I01036) -> NEUEON (INE333I01044); "
        "FV-only event, no factor; 315 missed sessions; boundary +110.2%",
    ("DELPHIFX", date(2020, 4, 21)):
        "relisting_after_suspension: WEIZFOREX -> EBIXFOREX (via DELPHIFX); "
        "ISIN identical, no capital event; 33 missed sessions; boundary +31.4%",
}


# ──────────────────────────────────────────────────────────────────────────────
def build_register(con):
    """Return (arm_a_excl, arm_d_excl, arm_b_excl) — the sole permitted exclusion sets.

    arm_a_excl: {(entity, move_date): reason}
    arm_d_excl: {(symbol, ex_date): reason}
    arm_b_excl: {(entity, handoff_date): reason}  (Prompt 1R4 §C/§E)
    """
    arm_a = {}
    arm_d = {}
    arm_b = {}

    # 1. Committed ETF unit splits
    for ent, dt in ETF_SPLITS:
        arm_a[(ent, dt)] = "etf_unit_split"

    # 2. Committed demergers
    for ent, dt in DEMERGERS:
        arm_a[(ent, dt)] = "demerger"

    # 3. ca_scope_exclusions mapped to entity (gate-(b) documented residue, D5)
    for ent, md in con.execute("""
            SELECT i.entity, x.move_date FROM ca_scope_exclusions x
            JOIN symbol_entity_intervals i ON i.symbol = x.symbol
                 AND x.move_date >= i.valid_from AND x.move_date < i.valid_to
    """).fetchall():
        arm_a[(ent, md)] = "documented_scope_exclusion"

    # 4. ca_evidence_exceptions — Arm D (by symbol) + Arm A (mapped to entity)
    for sym, ex in con.execute(
            "SELECT symbol, ex_date FROM ca_evidence_exceptions").fetchall():
        arm_d[(sym, ex)] = "evidence_exception"
        # Map to entity for Arm A (SAHPETRO->GULFPETRO, KWALITY stay)
        for ent, in con.execute("""
                SELECT DISTINCT i.entity FROM adjustment_factors af
                JOIN symbol_entity_intervals i ON i.symbol = af.symbol
                     AND af.ex_date >= i.valid_from AND af.ex_date < i.valid_to
                WHERE af.symbol = ? AND af.ex_date = ?
        """, [sym, ex]).fetchall():
            arm_a[(ent, ex)] = "evidence_exception"

    # 5. Committed relistings (Arm B — Prompt 1R4 §E)
    for (ent, dt), reason in RE_LISTINGS.items():
        arm_b[(ent, dt)] = reason

    return arm_a, arm_d, arm_b
