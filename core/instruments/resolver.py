"""
InstrumentResolver — the only reader of the instrument-master SSOT
(CANONICAL_INSTRUMENT_ARCHITECTURE.md §D7).

Reads the DuckDB master read-only and returns CanonicalInstrument objects.
Deterministic and point-in-time: every lookup resolves the snapshot effective at
`as_of` (the row with the greatest snapshot_date <= as_of, else the earliest
available), so backtests get historically-correct lot/tick values (§D7.4).
Results are memoized per (query, as_of). When the master is absent it logs once
and returns None — it never returns a silently-wrong instrument.

Broker bridges (resolve_broker_key / resolve_broker_position) are deferred to the
broker-mapping slice (4C.4); this slice owns canonical resolution over the master.
"""
import logging
from datetime import date
from pathlib import Path
from typing import Optional, Union

import duckdb

from core.instruments.canonical import AssetClass, CanonicalInstrument
from core.instruments.identity import normalize_underlying
from core.instruments.option import OptionType

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path(__file__).parent.parent.parent / "data" / "instruments" / "nse_fo_instruments.duckdb"

_TYPE_TO_ASSET = {
    "CE": AssetClass.OPTION, "PE": AssetClass.OPTION,
    "FUT": AssetClass.FUTURE, "EQ": AssetClass.EQUITY, "INDEX": AssetClass.INDEX,
}

_COLS = (
    "instrument_key, tradingsymbol, name, expiry, strike, instrument_type, "
    "lot_size, exchange, isin, tick_size, snapshot_date"
)


class InstrumentResolver:
    def __init__(self, db_path: Path = _DEFAULT_DB, as_of: Optional[date] = None):
        self._db_path = Path(db_path)
        self._as_of = as_of
        self._loaded = self._db_path.exists()
        self._cache: dict = {}
        if not self._loaded:
            logger.warning(
                "[InstrumentResolver] master DB absent at %s — resolution returns None",
                self._db_path,
            )

    # --- public API -------------------------------------------------------

    def resolve_equity(self, isin_or_symbol: str, as_of: Optional[date] = None):
        key = ("EQ", isin_or_symbol, self._eff_iso(as_of))
        if key in self._cache:
            return self._cache[key]
        rows = self._query(
            "(isin = ? OR tradingsymbol = ?) AND instrument_type = 'EQ'",
            [isin_or_symbol, isin_or_symbol],
        )
        ci = self._build(self._pick_effective(rows, as_of))
        self._cache[key] = ci
        return ci

    def resolve_index(self, name: str, as_of: Optional[date] = None):
        token = normalize_underlying(name)
        key = ("IDX", token, self._eff_iso(as_of))
        if key in self._cache:
            return self._cache[key]
        rows = [r for r in self._query("instrument_type = 'INDEX'", [])
                if normalize_underlying(r[2]) == token
                or normalize_underlying(r[1]) == token]
        ci = self._build(self._pick_effective(rows, as_of))
        self._cache[key] = ci
        return ci

    def resolve_future(self, underlying: str, as_of: Optional[date] = None):
        token = normalize_underlying(underlying)
        as_of_eff = self._eff(as_of)
        key = ("FUT", token, as_of_eff.isoformat())
        if key in self._cache:
            return self._cache[key]
        rows = [r for r in self._query("instrument_type = 'FUT'", [])
                if normalize_underlying(r[2]) == token
                and r[3] and r[3] >= as_of_eff.isoformat()]
        # nearest active expiry, then effective snapshot for that contract
        ci = None
        if rows:
            nearest_expiry = min(r[3] for r in rows)
            same = [r for r in rows if r[3] == nearest_expiry]
            ci = self._build(self._pick_effective(same, as_of))
        self._cache[key] = ci
        return ci

    def resolve_option(self, underlying: str, expiry: date, strike: float,
                       option_type: Union[OptionType, str], as_of: Optional[date] = None):
        token = normalize_underlying(underlying)
        ot = option_type.value if isinstance(option_type, OptionType) else str(option_type).upper()
        exp_iso = expiry.isoformat()
        key = ("OPT", token, exp_iso, float(strike), ot, self._eff_iso(as_of))
        if key in self._cache:
            return self._cache[key]
        rows = [r for r in self._query(
                    "instrument_type = ? AND expiry = ?", [ot, exp_iso])
                if normalize_underlying(r[2]) == token and abs(r[4] - strike) < 0.01]
        ci = self._build(self._pick_effective(rows, as_of))
        self._cache[key] = ci
        return ci

    def resolve_by_instrument_key(self, instrument_key: str, as_of: Optional[date] = None):
        """Map a broker instrument_key to its CanonicalInstrument (broker bridge)."""
        key = ("IKEY", instrument_key, self._eff_iso(as_of))
        if key in self._cache:
            return self._cache[key]
        rows = self._query("instrument_key = ?", [instrument_key])
        ci = self._build(self._pick_effective(rows, as_of))
        self._cache[key] = ci
        return ci

    def latest_snapshot_date(self) -> Optional[date]:
        """The most recent snapshot on disk (MAX(snapshot_date)), or None when the
        master is absent/empty. The single freshness fact all consumers read
        (MASTER_MATERIALIZATION_POLICY.md §3) — never re-derive MAX elsewhere."""
        if not self._loaded:
            return None
        con = duckdb.connect(str(self._db_path), read_only=True)
        try:
            row = con.execute("SELECT MAX(snapshot_date) FROM instruments").fetchone()
        except Exception:
            return None
        finally:
            con.close()
        return date.fromisoformat(row[0]) if row and row[0] else None

    def segment_row_count(self, segment: str) -> int:
        """Rows for `segment` in the latest snapshot — a coverage FACT (MM.4,
        MASTER_MATERIALIZATION_POLICY.md §3). 0 when the master is absent/empty.
        Facts only: the FRESH/WARN/BLOCK verdict is the readiness module's, never
        the resolver's (MM.4_DESIGN_REVIEW.md §3-impl)."""
        if not self._loaded:
            return 0
        con = duckdb.connect(str(self._db_path), read_only=True)
        try:
            row = con.execute(
                "SELECT COUNT(*) FROM instruments WHERE exchange = ? AND "
                "snapshot_date = (SELECT MAX(snapshot_date) FROM instruments)",
                [segment],
            ).fetchone()
        except Exception:
            return 0
        finally:
            con.close()
        return int(row[0]) if row and row[0] else 0

    def active_expiry_present(self, underlying: str, on_or_after: date) -> bool:
        """True when the latest snapshot carries a FUT/CE/PE for `underlying` with
        expiry >= `on_or_after` — the active contract set a live derivative order
        needs (coverage FACT, MM.4). False when the master is absent/empty. Facts
        only — no verdict."""
        if not self._loaded:
            return False
        token = normalize_underlying(underlying)
        con = duckdb.connect(str(self._db_path), read_only=True)
        try:
            rows = con.execute(
                "SELECT name FROM instruments WHERE instrument_type IN "
                "('FUT','CE','PE') AND expiry >= ? AND "
                "snapshot_date = (SELECT MAX(snapshot_date) FROM instruments)",
                [on_or_after.isoformat()],
            ).fetchall()
        except Exception:
            return False
        finally:
            con.close()
        return any(normalize_underlying(r[0]) == token for r in rows)

    # --- internals --------------------------------------------------------

    def _eff(self, as_of: Optional[date]) -> date:
        return as_of or self._as_of or date.today()

    def _eff_iso(self, as_of: Optional[date]) -> str:
        return self._eff(as_of).isoformat()

    def _query(self, where: str, params: list):
        if not self._loaded:
            return []
        con = duckdb.connect(str(self._db_path), read_only=True)
        try:
            return con.execute(f"SELECT {_COLS} FROM instruments WHERE {where}", params).fetchall()
        finally:
            con.close()

    def _pick_effective(self, rows: list, as_of: Optional[date]):
        if not rows:
            return None
        as_of_iso = self._eff_iso(as_of)
        eligible = [r for r in rows if r[10] <= as_of_iso]
        if eligible:
            return max(eligible, key=lambda r: r[10])
        earliest = min(rows, key=lambda r: r[10])
        logger.warning(
            "[InstrumentResolver] as_of %s precedes all snapshots; falling back to "
            "earliest snapshot %s — attributes (lot_size/tick_size) may be wrong",
            as_of_iso, earliest[10],
        )
        return earliest

    def _build(self, row) -> Optional[CanonicalInstrument]:
        if row is None:
            return None
        (_ikey, tsym, name, expiry, strike, itype, lot_size,
         exchange, isin, tick_size, _snap) = row
        asset_class = _TYPE_TO_ASSET.get((itype or "").upper())
        if asset_class is None:
            return None
        exch_token = (exchange or "").split("_")[0] or "NSE"
        is_option = asset_class == AssetClass.OPTION
        is_equity = asset_class == AssetClass.EQUITY
        return CanonicalInstrument(
            asset_class=asset_class,
            exchange=exch_token,
            underlying=None if is_equity else (name or None),
            expiry=date.fromisoformat(expiry) if expiry else None,
            strike=strike if is_option else None,
            option_type=OptionType(itype) if itype in ("CE", "PE") else None,
            lot_size=int(lot_size) or 1,
            tick_size=float(tick_size or 0.0),
            isin=isin or None,
            segment=exchange or None,
            display_symbol=tsym or None,
        )
