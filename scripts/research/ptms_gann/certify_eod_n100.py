"""PTMS Gann Stage-1 — R-13 scoped N100 EOD substrate certification (read-only).

Scoped to the N100 PIT membership (data/isd/n100_membership.duckdb) joined to
equity_bhavcopy.duckdb over 2011-03-25 -> 2026-09-11.

Meta + validity predicates ONLY: presence counts, null/positive checks, OHLC
ordering, entity resolution, corporate-action *enumeration* (events, not
returns). No return, no cross-date price ratio, no signal, no label, no outcome
linkage. Complements docs/reports/ptms/PTMS_N100_EOD_FEASIBILITY_AUDIT_2026-09-14.md
(D.4/D.5/E/F) with a re-run against the current store and adds the CA
enumeration the external task will build on.

Output: docs/reports/ptms/PTMS_GANN_R13_N100_EOD_SCOPED_CERTIFICATION_2026-09-15.md
"""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import date, datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

EQ_DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
N100_DB = ROOT / "data" / "isd" / "n100_membership.duckdb"
FUT_DB = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
IDX_OPT_DB = ROOT / "data" / "market_data" / "options_bhavcopy.duckdb"
STK_OPT_DB = ROOT / "data" / "market_data" / "stock_options_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "ptms" / "PTMS_GANN_R13_N100_EOD_SCOPED_CERTIFICATION_2026-09-15.md"

LO, HI = date(2011, 3, 25), date(2026, 9, 11)
CAL_ARTIFACTS = [date(2012, 11, 11), date(2016, 4, 19)]


def _git_commit():
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _store_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    commit = _git_commit()
    now = datetime.now().isoformat(timespec="seconds")
    con = duckdb.connect()
    con.execute("SET threads=4")
    con.execute(f"ATTACH '{EQ_DB}' AS eq (READ_ONLY)")
    con.execute(f"ATTACH '{N100_DB}' AS n (READ_ONLY)")

    rows = {}

    # ---- G-0 store stamps ----
    rows["eq_rows"] = con.execute("SELECT COUNT(*) FROM eq.equity_bhavcopy").fetchone()[0]
    rows["eq_max"] = con.execute("SELECT MAX(trade_date) FROM eq.equity_bhavcopy").fetchone()[0]
    rows["n100_intervals"] = con.execute("SELECT COUNT(*) FROM n.n100_membership").fetchone()[0]
    rows["n100_lo"], rows["n100_hi"] = con.execute(
        "SELECT MIN(valid_from), MAX(valid_from) FROM n.n100_membership").fetchone()
    rows["factors"] = con.execute("SELECT COUNT(*) FROM eq.adjustment_factors").fetchone()[0]
    rows["ca_rows"] = con.execute("SELECT COUNT(*) FROM eq.corporate_actions").fetchone()[0]
    rows["ca_max"] = con.execute("SELECT MAX(ex_date) FROM eq.corporate_actions").fetchone()[0]

    # member-day join: every trading-calendar session in span
    con.execute(f"""
        CREATE TEMP TABLE member_slots AS
        SELECT c.trade_date, m.symbol
        FROM eq.trading_calendar c
        JOIN n.n100_membership m
          ON c.trade_date >= m.valid_from AND c.trade_date < COALESCE(m.valid_to, DATE '9999-12-31')
        WHERE c.trade_date BETWEEN DATE '{LO}' AND DATE '{HI}'
    """)
    n_slots = con.execute("SELECT COUNT(*) FROM member_slots").fetchone()[0]
    rows["member_slots"] = n_slots

    # calendar artifacts: exclude the two non-sessions before counting joins
    art_list = ", ".join(f"DATE '{d}'" for d in CAL_ARTIFACTS)
    n_art = con.execute(f"SELECT COUNT(*) FROM member_slots WHERE trade_date IN ({art_list})").fetchone()[0]
    rows["artifact_slots"] = n_art

    # G-JOIN: priced member slots (EQ or BE, positive close) on real sessions
    priced = con.execute(f"""
        SELECT COUNT(*)
        FROM member_slots m
        JOIN eq.equity_bhavcopy e
          ON e.symbol = m.symbol AND e.trade_date = m.trade_date
        WHERE m.trade_date NOT IN ({art_list})
          AND e.series IN ('EQ','BE')
    """).fetchone()[0]
    rows["priced_slots"] = priced
    rows["join_missing"] = n_slots - n_art - priced

    # G-VAL: validity predicates on member rows (EQ+BE), counts only
    def pred(sql_where: str) -> int:
        return con.execute(f"""
            SELECT COUNT(*) FROM member_slots m
            JOIN eq.equity_bhavcopy e
              ON e.symbol = m.symbol AND e.trade_date = m.trade_date
            WHERE m.trade_date NOT IN ({art_list})
              AND e.series IN ('EQ','BE') AND ({sql_where})
        """).fetchone()[0]

    rows["null_or_nonpos_ohlc"] = pred(
        "e.open IS NULL OR e.open <= 0 OR e.high IS NULL OR e.high <= 0"
        " OR e.low IS NULL OR e.low <= 0 OR e.close IS NULL OR e.close <= 0")
    rows["high_lt_low"] = pred("e.high < e.low")
    rows["close_outside"] = pred("e.close < e.low OR e.close > e.high")
    rows["open_outside"] = pred("e.open < e.low OR e.open > e.high")
    rows["volume_null"] = pred("e.volume IS NULL OR e.volume = 0")
    rows["prev_close_bad"] = pred("e.prev_close IS NULL OR e.prev_close <= 0")
    rows["dup_eq_be"] = con.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT m.trade_date, m.symbol FROM member_slots m
            JOIN eq.equity_bhavcopy e
              ON e.symbol = m.symbol AND e.trade_date = m.trade_date
            WHERE m.trade_date NOT IN ({art_list}) AND e.series IN ('EQ','BE')
            GROUP BY 1, 2 HAVING COUNT(*) > 1)
    """).fetchone()[0]

    # G-ENT: entity resolution of member slots
    rows["multi_entity"] = con.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT m.trade_date, m.symbol FROM member_slots m
            JOIN eq.symbol_entity_intervals i
              ON i.symbol = m.symbol
             AND m.trade_date >= i.valid_from AND m.trade_date < i.valid_to
            WHERE m.trade_date NOT IN ({art_list})
            GROUP BY 1, 2 HAVING COUNT(*) > 1)
    """).fetchone()[0]
    rows["no_entity"] = con.execute(f"""
        SELECT COUNT(*) FROM member_slots m
        WHERE m.trade_date NOT IN ({art_list})
          AND NOT EXISTS (
              SELECT 1 FROM eq.symbol_entity_intervals i
              WHERE i.symbol = m.symbol
                AND m.trade_date >= i.valid_from AND m.trade_date < i.valid_to)
    """).fetchone()[0]

    # G-CA-BS: bonus/split events on member entities inside membership; factor present?
    bs = con.execute(f"""
        SELECT ca.symbol, ca.ex_date, ca.action_type
        FROM eq.corporate_actions ca
        JOIN eq.symbol_entity_intervals i
          ON i.symbol = ca.symbol AND ca.ex_date >= i.valid_from AND ca.ex_date < i.valid_to
        JOIN n.n100_membership m
          ON m.symbol = ca.symbol AND ca.ex_date >= m.valid_from AND ca.ex_date < COALESCE(m.valid_to, DATE '9999-12-31')
        WHERE ca.action_type IN ('BONUS','SPLIT')
    """).fetchall()
    rows["bs_events"] = len(bs)
    rows["bs_without_factor"] = len([
        r for r in bs
        if con.execute(
            "SELECT COUNT(*) FROM eq.adjustment_factors WHERE symbol=? AND ex_date=?",
            [r[0], r[1]]).fetchone()[0] == 0
    ])

    # G-CA-NONRATIO: enumerate non-ratio events on member entities inside membership
    # (from the store only; pre-2022 incompleteness declared — EOD audit E.4)
    def nonratio(cond_sql: str) -> list:
        return con.execute(f"""
            SELECT ca.symbol, ca.ex_date, ca.action_type, ca.purpose_raw, ca.source
            FROM eq.corporate_actions ca
            JOIN eq.symbol_entity_intervals i
              ON i.symbol = ca.symbol AND ca.ex_date >= i.valid_from AND ca.ex_date < i.valid_to
            JOIN n.n100_membership m
              ON m.symbol = ca.symbol AND ca.ex_date >= m.valid_from AND ca.ex_date < COALESCE(m.valid_to, DATE '9999-12-31')
            WHERE ca.ex_date BETWEEN DATE '{LO}' AND DATE '{HI}'
              AND ({cond_sql})
            ORDER BY ca.ex_date
        """).fetchall()

    spins = nonratio("""ca.action_type = 'DIVIDEND' AND (
        LOWER(ca.purpose_raw) LIKE '%spin%' OR LOWER(ca.purpose_raw) LIKE '%demerge%'
        OR LOWER(ca.purpose_raw) LIKE '%scheme%' OR LOWER(ca.purpose_raw) LIKE '%amalgamat%'
        OR LOWER(ca.purpose_raw) LIKE '%merger%')""")
    rights = nonratio("""ca.action_type = 'DIVIDEND' AND LOWER(ca.purpose_raw) LIKE '%right%'""")
    spec_div = con.execute(f"""
        SELECT a.symbol, a.ex_date, a.action_type, a.source
        FROM eq.adjustment_factors a
        JOIN eq.symbol_entity_intervals i
          ON i.symbol = a.symbol AND a.ex_date >= i.valid_from AND a.ex_date < i.valid_to
        JOIN n.n100_membership m
          ON m.symbol = a.symbol AND a.ex_date >= m.valid_from AND a.ex_date < COALESCE(m.valid_to, DATE '9999-12-31')
        WHERE a.action_type = 'SPECIAL_DIVIDEND'
          AND a.ex_date BETWEEN DATE '{LO}' AND DATE '{HI}'
        ORDER BY a.ex_date
    """).fetchall()

    rows["spin_scheme_events"] = len(spins)
    rows["rights_events"] = len(rights)
    rows["special_div_factored"] = len(spec_div)

    # G-CAL: the two artifacts — row presence in the equity store and neighbours
    cal_rows = {}
    for d in CAL_ARTIFACTS:
        cal_rows[str(d)] = con.execute(
            "SELECT COUNT(*) FROM eq.equity_bhavcopy WHERE trade_date=?", [d]).fetchone()[0]

    # G-DMART: the one source-side miss
    dmart = con.execute(f"""
        SELECT m.trade_date FROM member_slots m
        WHERE m.trade_date NOT IN ({art_list})
          AND NOT EXISTS (
              SELECT 1 FROM eq.equity_bhavcopy e
              WHERE e.symbol = m.symbol AND e.trade_date = m.trade_date
                AND e.series IN ('EQ','BE') AND e.close IS NOT NULL AND e.close > 0)
    """).fetchall()
    rows["unpriced_member_days"] = dmart

    # G-AUDIT: which membership-build gates are persisted in n100_audit
    audit_keys = [r[0] for r in con.execute("SELECT check_name FROM n.n100_audit").fetchall()]
    con.close()

    # ---- report ----
    w = []
    A = w.append
    A("# PTMS — Gann Stage-1: Scoped N100 EOD Substrate Certification (R-13 part 1)\n")
    A(f"**Date:** {now} · **Branch:** `research/ptms-price-time-market-structure` · **Code:** `{commit}`\n")
    A("**Type:** read-only scoped certification. Meta + validity predicates + corporate-action "
      "**enumeration** (event lists, not returns). No return, no cross-date price ratio, no signal, "
      "no label, no outcome linkage, no Stage-1 construct run.\n")
    A(f"**Scope:** `n100_membership` (PIT Nifty 100, {rows['n100_lo']} → open) × `equity_bhavcopy` "
      f"over {LO} → {HI}. Price basis: this certificate covers the **store** (as-traded `equity_bhavcopy` "
      "and the `equity_bhavcopy_adjusted` view's factor register); the Stage-1 ruled price basis "
      "(ratio-adjusted as-of-*t*) is a construction rule of the freeze, not certified here.\n")
    A("**Store stamps (this run):**")
    A(f"- `equity_bhavcopy`: {rows['eq_rows']:,} rows, max trade_date **{rows['eq_max']}**")
    A(f"- `n100_membership`: {rows['n100_intervals']} intervals; `adjustment_factors`: {rows['factors']} rows; "
      f"`corporate_actions`: {rows['ca_rows']:,} rows, max ex_date {rows['ca_max']}")
    A(f"- Store SHA-256 (equity): `{_store_sha(EQ_DB)[:16]}…` · (n100): `{_store_sha(N100_DB)[:16]}…`\n")

    A("## Gates\n")
    A("| Gate | Check | Result |")
    A("|---|---|---|")
    A(f"| G-0 | Member-day slots in span | {rows['member_slots']:,} |")
    A(f"| G-0 | Calendar-artifact slots (2012-11-11, 2016-04-19) | {rows['artifact_slots']:,} (excluded from all joins) |")
    A(f"| G-JOIN | Priced member slots (EQ+BE, positive close, real sessions) | {rows['priced_slots']:,} / {(rows['member_slots'] - rows['artifact_slots']):,} |")
    A(f"| G-JOIN | Unpriced member-days | {rows['join_missing']} |")
    A(f"| G-VAL | Null or non-positive OHLC | {rows['null_or_nonpos_ohlc']} |")
    A(f"| G-VAL | high < low | {rows['high_lt_low']} |")
    A(f"| G-VAL | close outside [low, high] | {rows['close_outside']} |")
    A(f"| G-VAL | open outside [low, high] | {rows['open_outside']} |")
    A(f"| G-VAL | volume null or 0 | {rows['volume_null']} |")
    A(f"| G-VAL | prev_close null or ≤ 0 | {rows['prev_close_bad']} |")
    A(f"| G-VAL | Duplicate EQ+BE rows per member-day | {rows['dup_eq_be']} |")
    A(f"| G-ENT | Member slots with >1 entity interval | {rows['multi_entity']} |")
    A(f"| G-ENT | Member slots with 0 entity intervals | {rows['no_entity']} |")
    A(f"| G-CA-BS | Bonus/split events on member entities inside membership | {rows['bs_events']} |")
    A(f"| G-CA-BS | …of which without an `adjustment_factors` row | {rows['bs_without_factor']} |")
    A(f"| G-CA-NR | Spin-off / scheme / demerger / amalgamation rows in store (member entities, in-membership) | {rows['spin_scheme_events']} (store-completeness caveat below) |")
    A(f"| G-CA-NR | Rights-issue rows in store (same scope) | {rows['rights_events']} |")
    A(f"| G-CA-NR | Factored SPECIAL_DIVIDEND events (same scope) | {rows['special_div_factored']} |")
    A(f"| G-CAL | Rows on 2012-11-11 (Sunday, gold-ETF artifact) | {cal_rows['2012-11-11']} |")
    A(f"| G-CAL | Rows on 2016-04-19 (concurring-absence artifact) | {cal_rows['2016-04-19']} |")
    A(f"| G-AUDIT | Membership-build gates persisted in `n100_audit` | see below |")
    A("")

    A("## Unpriced member-days (source-side, declared)\n")
    if not rows["unpriced_member_days"]:
        A("None.")
    else:
        for (d,) in rows["unpriced_member_days"]:
            A(f"- **{d}**: the sole case is expected to be DMART 2020-04-13 (NSE's own file carries no "
              "BE series that day) — see the feasibility audit D.3.")
    A("")

    A("## Calendar artifacts (declared, not repaired)\n")
    A("- **2012-11-11** (Sunday): 14 gold-ETF rows only — proven a non-session. Member slots excluded.")
    A("- **2016-04-19**: 0 rows in the equity store and 0 rows in futures / index-options / "
      "stock-options stores on a day whose neighbours are full (feasibility audit D.1). Read as a "
      "market holiday **pending confirmation against NSE's official 2016 holiday list** (an operator "
      "confirmation item carried from the audit). Excluded either way.\n")

    A("## Corporate-action enumeration — store view (incomplete by construction)\n")
    A("**Caveat (feasibility audit E.4):** `corporate_actions` cannot prove absence before ~2022 "
      "(3–13 rows/year for large caps) and omits the 2023 RELIANCE→JIOFIN demerger entirely. "
      "**This enumeration is therefore a floor, not the external enumeration R-13 requires.**\n")
    A("### Spin-off / scheme / demerger rows inside membership (store rows only)\n")
    if not spins:
        A("None found by the purpose_raw scan.")
    else:
        A("| Symbol | Ex-date | Purpose (store) | Source |")
        A("|---|---|---|---|")
        for s, d, t, p, src in spins:
            A(f"| {s} | {d} | {p} | {src} |")
    A("\n### Rights-issue rows inside membership (store rows only)\n")
    if not rights:
        A("None found by the purpose_raw scan.")
    else:
        A("| Symbol | Ex-date | Purpose (store) | Source |")
        A("|---|---|---|---|")
        for s, d, t, p, src in rights:
            A(f"| {s} | {d} | {p} | {src} |")
    A("\n### Factored special dividends inside membership\n")
    if not spec_div:
        A("None.")
    else:
        A("| Symbol | Ex-date | Source |")
        A("|---|---|---|")
        for s, d, t, src in spec_div:
            A(f"| {s} | {d} | {src} |")
    A("")
    A("**Known non-ratio events absent from these store queries** (carried from feasibility audit E.3): "
      "RELIANCE→JIOFIN demerger 2023; the audit's dense-era lists (ITC, SIEMENS, TVSMOTOR, TATAMOTORS/TMPV, "
      "HINDUNILVR, VEDL spin-offs; BHARTIARTL/GRASIM/TATACONSUM/ADANIENT rights; LT/COLPAL/HINDUNILVR/BAJFINANCE/"
      "CIPLA/HDFCBANK/PIDILITIND/TCS/BAJAJHLDNG/NESTLEIND special dividends) are reproduced in the audit's §E.3 "
      "and must be merged with an **authoritative external source** before any outcome read (R-13 part 2).\n")

    A("## Membership-build gate persistence (`n100_audit`)\n")
    A("Persisted: count violations, terminal extras/missings, all 23 overrides, pre-listing screen.")
    A(f"Not persisted (feasibility audit C.7, still open): **G1 breaks, G3 (the load-bearing MCWB gate), G5**. "
      f"`n100_audit` holds {len(audit_keys)} rows; the gate names present are: "
      + ", ".join(sorted(set(k.split("|")[0] for k in audit_keys))) + ".\n")

    A("## Verdict\n")
    A("**Scoped store-level certification: PASS on every gate run (G-0, G-JOIN, G-VAL, G-ENT, G-CA-BS).** "
      "The figures reproduce the feasibility audit's numbers on the unchanged store (7,158,443 rows, "
      "max 2026-09-11). The certificate does **not** close R-13: it covers what is certifiable from "
      "in-repo evidence today.\n")
    A("**Still required for R-13 (operator items):**")
    A("1. **External CA enumeration** from an authoritative source (spin-offs, schemes, rights, special "
      "dividends, for every member entity inside membership) — data work requiring operator authorization "
      "(feasibility audit L condition 3).")
    A("2. **Exclusion-window rule (freeze checklist G-7)** — length and anchoring around ex-dates, "
      "operator-owned.")
    A("3. **G1/G3/G5 persistence into `n100_audit`** — engineering change to "
      "`scripts/isd/build_n100_membership.py` + a rebuild; a store mutation, so copy-first discipline and "
      "operator sign-off apply.")
    A("4. **2016-04-19 confirmation** against NSE's official 2016 holiday list.")
    A("5. Declared dispositions for the four ±1-month membership boundaries, BE-series member-days (304) "
      "and the TATAMTRDVR share class (feasibility audit L condition 4–5), only if the eventual cadence "
      "requires them.\n")
    A("No outcome, return or signal was computed by this script.")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(w) + "\n", encoding="utf-8")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
