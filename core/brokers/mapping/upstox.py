"""
Upstox broker mapping (CANONICAL_INSTRUMENT_ARCHITECTURE.md §D6).

A projection of the instrument master: for every contract it stores
canonical_id -> broker identity (instrument_key, tradingsymbol) and the reverse,
so order routing can translate a CanonicalInstrument to the Upstox
`instrument_token`, and reconciliation can translate a broker position back to a
canonical_id. Canonical resolution itself is delegated to InstrumentResolver.
"""
import logging
from datetime import date
from pathlib import Path
from typing import Optional

import duckdb

from core.brokers.mapping.base import BrokerMapping, BrokerRef
from core.instruments.canonical import AssetClass, CanonicalInstrument
from core.instruments.resolver import InstrumentResolver, _DEFAULT_DB

logger = logging.getLogger(__name__)

# Platform product intent -> Upstox product code. Upstox has no NRML/CNC split;
# carry and delivery both route as "D", intraday as "I".
_PRODUCT = {"MIS": "I", "CNC": "D", "NRML": "D"}

# When ci.product is None (resolver never populates it; master has no product column),
# the asset class determines the safe default. FUTURE/OPTION require NRML to allow
# overnight carry; EQUITY requires CNC for funded delivery. INDEX is non-tradable.
_ASSET_DEFAULT_PRODUCT = {
    AssetClass.FUTURE: "NRML",
    AssetClass.OPTION: "NRML",
    AssetClass.EQUITY: "CNC",
}


class UpstoxMapping(BrokerMapping):
    def __init__(self, db_path: Path = _DEFAULT_DB, as_of: Optional[date] = None):
        self._db_path = Path(db_path)
        self._resolver = InstrumentResolver(db_path=db_path, as_of=as_of)
        self._ref_by_canonical: dict = {}
        self._ikey_by_tradingsymbol: dict = {}
        if self._db_path.exists():
            self._build_projection()
        else:
            logger.warning(
                "[UpstoxMapping] master DB absent at %s — mapping is empty",
                self._db_path,
            )

    def _build_projection(self):
        con = duckdb.connect(str(self._db_path), read_only=True)
        try:
            rows = con.execute(
                """SELECT instrument_key, tradingsymbol FROM instruments t
                   WHERE snapshot_date = (
                       SELECT MAX(snapshot_date) FROM instruments t2
                       WHERE t2.instrument_key = t.instrument_key)"""
            ).fetchall()
        finally:
            con.close()
        for ikey, tsym in rows:
            ci = self._resolver.resolve_by_instrument_key(ikey)
            if ci is None:
                continue
            self._ref_by_canonical[ci.canonical_id] = BrokerRef(
                instrument_key=ikey, tradingsymbol=tsym)
            if tsym:
                self._ikey_by_tradingsymbol[tsym] = ikey

    def to_broker(self, instrument: CanonicalInstrument) -> BrokerRef:
        ref = self._ref_by_canonical.get(instrument.canonical_id)
        if ref is None:
            raise LookupError(
                f"no Upstox mapping for {instrument.canonical_id}")
        product_intent = instrument.product or _ASSET_DEFAULT_PRODUCT.get(instrument.asset_class)
        return BrokerRef(
            instrument_key=ref.instrument_key,
            tradingsymbol=ref.tradingsymbol,
            exchange_token=ref.exchange_token,
            product_code=_PRODUCT.get(product_intent),
        )

    def from_broker_position(self, raw: dict) -> Optional[CanonicalInstrument]:
        ikey = raw.get("instrument_token") or raw.get("instrument_key")
        if not ikey:
            tsym = raw.get("trading_symbol") or raw.get("tradingsymbol")
            ikey = self._ikey_by_tradingsymbol.get(tsym)
        if not ikey:
            return None
        return self._resolver.resolve_by_instrument_key(ikey)

    def from_broker_order(self, raw: dict) -> Optional[CanonicalInstrument]:
        return self.from_broker_position(raw)
