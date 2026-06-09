#!/usr/bin/env python3
"""
MM.5 — Instrument Master Materialization acceptance check (one-off / on-demand).

Downloads the live Upstox CDN master ONCE, then in order:
  1. Source-contract verification — the live payload's field shape vs what
     `parse_instruments` depends on (catches an upstream Upstox schema drift now).
  2. Materialize — the EXACT production path (`parse_instruments` + `write_snapshot`,
     snapshot_date = date.today() as `refresh()` defaults) into the real DB.
  3. Coverage validation against real data — policy §3 assertions.
  4. Spot-resolve real contracts — prove resolution returns CanonicalInstrument,
     not None (row counts can pass while a token mismatch yields None).
  5. Startup-gate validation against real data — the read-only `assess()` verdict
     the LoopDriver gate consumes, plus the absent-path BLOCK proof.

Read-only against the frozen areas (routing/resolver/gate/reconciliation): every
check is a resolver read or a pure `assess()`. Nothing is wired into a live entry
script. Materialization writes a DATA file only.
"""
import gzip
import json
from collections import Counter
from datetime import date

import duckdb
import requests

from scripts.fetch_instrument_master import (
    INSTRUMENTS_URL, DB_PATH, ACCEPTED_SEGMENTS,
    parse_instruments, write_snapshot,
)
from core.instruments.resolver import InstrumentResolver
from core.instruments.identity import normalize_underlying
from core.instruments.master_readiness import assess, ReadinessState
from core.instruments.master_freshness import expected_snapshot_date
from core.database.utils.market_hours import MarketHours

UNDERLYINGS = ["NIFTY", "BANKNIFTY"]
RULE = "=" * 72


def section(title):
    print(f"\n{RULE}\n{title}\n{RULE}")


def download_raw():
    section("DOWNLOAD")
    resp = requests.get(INSTRUMENTS_URL, timeout=60)
    resp.raise_for_status()
    raw = json.loads(gzip.decompress(resp.content))
    print(f"source            : {INSTRUMENTS_URL}")
    print(f"compressed bytes  : {len(resp.content):,}")
    print(f"total instruments : {len(raw):,}")
    return raw


def contract_check(raw):
    section("1. SOURCE-CONTRACT VERIFICATION")
    accepted = [it for it in raw
                if (it.get("segment") or it.get("exchange", "")) in ACCEPTED_SEGMENTS]
    print(f"accepted-segment rows : {len(accepted):,}")

    seg_counts = Counter((it.get("segment") or it.get("exchange", "")) for it in accepted)
    for seg in ACCEPTED_SEGMENTS:
        print(f"  {seg:<10}: {seg_counts.get(seg, 0):>8,}")

    # Fields parse_instruments reads, with the variants it accepts.
    variants = {
        "instrument_key": ["instrument_key", "key"],
        "tradingsymbol": ["tradingsymbol", "trading_symbol"],
        "name": ["name"],
        "instrument_type": ["instrument_type", "option_type"],
        "expiry": ["expiry", "expiry_date"],
        "strike": ["strike_price", "strike"],
        "isin": ["isin"],
        "lot_size": ["lot_size"],
        "tick_size": ["tick_size"],
        "segment": ["segment", "exchange"],
    }
    print("\nfield presence (variant actually populated, share of accepted rows):")
    drift = []
    for logical, keys in variants.items():
        hit = Counter()
        for it in accepted:
            for k in keys:
                if it.get(k) not in (None, ""):
                    hit[k] += 1
                    break
        share = sum(hit.values()) / len(accepted) * 100
        chosen = ", ".join(f"{k}={hit[k]:,}" for k in keys if hit[k]) or "<none>"
        print(f"  {logical:<16}: {share:6.1f}%  [{chosen}]")
        # Drift flags: load-bearing identity/typing fields must be ~universal.
        if logical in ("instrument_key", "instrument_type", "segment") and share < 99.9:
            drift.append(f"{logical} only {share:.1f}% populated")

    # expiry encoding (ms-int vs ISO string) — parse_instruments handles both.
    enc = Counter()
    for it in accepted:
        raw_exp = it.get("expiry") or it.get("expiry_date")
        if raw_exp in (None, "", 0):
            enc["absent"] += 1
        elif isinstance(raw_exp, (int, float)):
            enc["ms_int"] += 1
        elif isinstance(raw_exp, str):
            enc["iso_str"] += 1
        else:
            enc[f"other:{type(raw_exp).__name__}"] += 1
    print(f"\nexpiry encoding : {dict(enc)}")

    # instrument_type vocabulary. The resolver maps only {CE,PE,FUT,EQ,INDEX}
    # (_TYPE_TO_ASSET); NSE_EQ additionally carries equity SERIES codes
    # (BE/BZ/SM/ST/SG/GS/TB/N0...) and MCX carries its own codes — these are
    # expected tail, deliberately inert downstream, NOT schema drift. The contract
    # that matters: (a) every resolver-mapped type is present, and (b) the
    # DERIVATIVE segments are cleanly typed CE/PE/FUT (the 0-OPTION-rows risk Q7).
    RESOLVED = {"CE", "PE", "FUT", "EQ", "INDEX"}
    itypes = Counter((it.get("instrument_type") or it.get("option_type") or "").upper()
                     for it in accepted)
    print(f"resolver-mapped types  : "
          f"{{{', '.join(f'{t}={itypes.get(t,0):,}' for t in sorted(RESOLVED))}}}")
    print(f"distinct type codes    : {len(itypes)} "
          f"(equity-series + MCX tail expected)")
    missing = [t for t in RESOLVED if itypes.get(t, 0) == 0]
    if missing:
        drift.append(f"resolver-mapped type(s) ABSENT: {missing}")

    deriv_types = Counter(
        (it.get("instrument_type") or it.get("option_type") or "").upper()
        for it in accepted
        if (it.get("segment") or it.get("exchange", "")) in ("NSE_FO", "MCX_FO"))
    stray = set(deriv_types) - {"CE", "PE", "FUT"}
    print(f"derivative-segment types : {dict(deriv_types)}")
    if stray:
        drift.append(f"derivative segment carries non-CE/PE/FUT types: {stray}")

    print(f"\nCONTRACT VERDICT : {'PASS' if not drift else 'DRIFT — ' + '; '.join(drift)}")
    return not drift


def materialize(raw):
    section("2. MATERIALIZE (production path)")
    snapshot_date = date.today().isoformat()
    rows = parse_instruments(raw, snapshot_date)
    print(f"snapshot_date (date.today) : {snapshot_date}")
    print(f"parsed rows                : {len(rows):,}")
    n = write_snapshot(rows)  # default DB_PATH — the real master
    print(f"written rows               : {n:,}")
    print(f"db path                    : {DB_PATH}")
    print(f"db exists                  : {DB_PATH.exists()}")
    return snapshot_date


def coverage_check(resolver, expected):
    section("3. COVERAGE VALIDATION (policy §3, real data)")
    latest = resolver.latest_snapshot_date()
    print(f"latest_snapshot_date() : {latest}")
    print(f"expected_snapshot_date : {expected}")

    print("\nsegment_row_count() (latest snapshot):")
    seg_ok = {}
    for seg in ACCEPTED_SEGMENTS:
        c = resolver.segment_row_count(seg)
        seg_ok[seg] = c
        print(f"  {seg:<10}: {c:>8,}")

    # EQ ISIN population (equity canonical identity requires ISIN) — direct read.
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        eq_total, eq_isin = con.execute(
            "SELECT COUNT(*), COUNT(isin) FROM instruments "
            "WHERE instrument_type='EQ' AND snapshot_date=(SELECT MAX(snapshot_date) FROM instruments)"
        ).fetchone()
        itype_counts = con.execute(
            "SELECT instrument_type, COUNT(*) FROM instruments "
            "WHERE snapshot_date=(SELECT MAX(snapshot_date) FROM instruments) "
            "GROUP BY instrument_type ORDER BY 2 DESC"
        ).fetchall()
        fo_names = con.execute(
            "SELECT DISTINCT name FROM instruments WHERE exchange='NSE_FO' AND name<>'' "
            "AND snapshot_date=(SELECT MAX(snapshot_date) FROM instruments)"
        ).fetchall()
    finally:
        con.close()

    print(f"\nEQ rows / EQ-with-ISIN : {eq_total:,} / {eq_isin:,} "
          f"({(eq_isin/eq_total*100 if eq_total else 0):.1f}%)")
    print(f"instrument_type counts : {dict(itype_counts)}")

    # Underlying token reconciliation: do our assess() tokens match real FO names?
    norm_names = {normalize_underlying(r[0]) for r in fo_names}
    print(f"\ndistinct NSE_FO underlyings : {len(fo_names)}")
    for u in UNDERLYINGS:
        print(f"  token {u:<10} present in FO names : {u in norm_names}")

    print("\nactive_expiry_present() (>= expected):")
    exp_ok = {}
    for u in UNDERLYINGS:
        ok = resolver.active_expiry_present(u, expected)
        exp_ok[u] = ok
        print(f"  {u:<10}: {ok}")

    # Mirror exactly what assess() asserts for the gate (NSE_FO/MCX_FO only).
    deriv_present = (seg_ok.get("NSE_FO", 0) > 0) or (seg_ok.get("MCX_FO", 0) > 0)
    gate_coverage_ok = deriv_present and all(exp_ok.values())
    # Broader policy §3 evidence (reported, not the gate condition).
    policy_ok = (gate_coverage_ok and eq_total > 0 and eq_isin == eq_total
                 and seg_ok.get("NSE_INDEX", 0) > 0)
    print(f"\ngate coverage (NSE_FO/MCX_FO + active expiry) : {gate_coverage_ok}")
    print(f"policy §3 coverage (+ EQ-ISIN 100% + INDEX)    : {policy_ok}")
    return gate_coverage_ok


def spot_resolve(resolver):
    section("4. SPOT-RESOLVE REAL CONTRACTS")
    results = {}
    fut_n = resolver.resolve_future("NIFTY")
    fut_b = resolver.resolve_future("BANKNIFTY")
    idx = resolver.resolve_index("Nifty 50")
    # A known liquid equity ISIN (RELIANCE) — present in any NSE_EQ master.
    eq = resolver.resolve_equity("INE002A01018")
    for label, ci in [("resolve_future(NIFTY)", fut_n),
                      ("resolve_future(BANKNIFTY)", fut_b),
                      ("resolve_index(Nifty 50)", idx),
                      ("resolve_equity(RELIANCE ISIN)", eq)]:
        ok = ci is not None
        results[label] = ok
        detail = (f"{ci.asset_class.value} {ci.display_symbol} lot={ci.lot_size} "
                  f"tick={ci.tick_size}") if ci else "None"
        print(f"  {label:<32}: {'OK' if ok else 'NONE'}  {detail}")
    return all(results.values())


def gate_check(resolver):
    section("5. STARTUP-GATE VALIDATION (real data)")
    now_ist = MarketHours.get_ist_now()
    expected = expected_snapshot_date(now_ist)
    print(f"date.today() (machine local) : {date.today()}")
    print(f"MarketHours.get_ist_now()    : {now_ist.isoformat()}")
    print(f"  is_trading_day(now_ist)    : {MarketHours.is_trading_day(now_ist)}")
    print(f"expected_snapshot_date(IST)  : {expected}")
    if date.today() != now_ist.date():
        print("  ** machine-local date != IST date — snapshot stamping is off-IST **")

    verdict = assess(resolver, UNDERLYINGS, now=now_ist)
    print(f"\nassess() verdict : {verdict.state.value}"
          f"  reason={verdict.reason} latest={verdict.latest} expected={verdict.expected}")

    # Absent-path proof: the gate has teeth against a missing master.
    absent = InstrumentResolver(db_path=DB_PATH.parent / "__does_not_exist__.duckdb")
    av = assess(absent, UNDERLYINGS, now=now_ist)
    print(f"absent-path proof : {av.state.value} reason={av.reason} "
          f"(expect BLOCK/absent)")
    absent_ok = av.state is ReadinessState.BLOCK and av.reason == "absent"
    return verdict, absent_ok


def main():
    raw = download_raw()
    contract_ok = contract_check(raw)
    materialize(raw)
    resolver = InstrumentResolver()
    expected = expected_snapshot_date(MarketHours.get_ist_now())
    coverage_ok = coverage_check(resolver, expected)
    resolve_ok = spot_resolve(resolver)
    verdict, absent_ok = gate_check(resolver)

    section("SUMMARY")
    print(f"contract verification : {'PASS' if contract_ok else 'FAIL'}")
    print(f"coverage (gate)       : {'PASS' if coverage_ok else 'FAIL'}")
    print(f"spot-resolve          : {'PASS' if resolve_ok else 'FAIL'}")
    print(f"gate verdict          : {verdict.state.value}")
    print(f"absent-path BLOCK     : {'PASS' if absent_ok else 'FAIL'}")


if __name__ == "__main__":
    main()
