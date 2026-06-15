"""
Gate G1 — Wave 5 Closure Guard.

The mechanical, ADR-002-style closure proof for Gate G1 (the criterion #5 of
`docs/reports/SOLE_IDENTITY_PATH_REVIEW.md` §6): a committed guard test that FAILS
if any new `InstrumentParser.parse` / direct legacy `Option(...)` / `Future(...)`
construction becomes reachable from the live F&O order-build or post-gate-restore
path, or if a `CanonicalInstrument` ever crosses the `NormalizedOrder` /
persistence / broker-payload boundary.

It proves five things (the Wave-5 requirements), preferring executable AST / grep /
characterization checks over report prose:

  1. No LIVE F&O order path constructs identity ownership through
     `InstrumentParser.parse`, a legacy `Option(...)`, or a legacy `Future(...)`.
  2. All live derivative identity creation flows through a `CanonicalInstrument`
     and the derive-to-legacy boundary (`futures.resolve_future`,
     `canonical_restore.canonicalize_symbol`, `selector.select`).
  3. `CanonicalInstrument` never crosses `NormalizedOrder`, persistence, or the
     broker payload (it stays internal — the G1 / 4C.7 boundary).
  4. The restore path upgrades identity ONLY after MM.4 master-readiness and
     BEFORE reconciliation (Option-B post-gate canonicalization).
  5. Site #6 (`Position(symbol=)`) remains dead — no production callers.

Nothing here changes production behavior; every check reads source (via `ast`)
or drives a real `ExecutionHandler` over an isolated tmp store.
"""
import ast
import pathlib

import pytz
from datetime import datetime

import core.execution.handler as handler_mod
from core.execution.handler import ExecutionHandler, ExecutionConfig
from core.execution.persistence.execution_store import ExecutionStore
from core.instruments.canonical import CanonicalInstrument
from core.instruments.instrument_base import InstrumentType
from core.brokers.paper_broker import PaperBroker
from core.clock import ReplayClock
from core.database.manager import DatabaseManager
from core.events import SignalEvent, SignalType

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORE = ROOT / "core"

FIXED_DT = datetime(2026, 6, 9, 9, 30, tzinfo=pytz.UTC)
FUTURES_SYMBOL = "NIFTY26JUNFUT"
OPTION_UNDERLYING = "NSE_INDEX|Nifty 50"
OPTION_PRICE = 22500.0
EXPECTED_OPTION_SYMBOL = "NIFTY16JUN2622500CE"


# --------------------------------------------------------------------------- #
# AST helpers
# --------------------------------------------------------------------------- #
def _tree(rel_path):
    return ast.parse((CORE / rel_path).read_text(encoding="utf-8"))


def _callee(func):
    """Dotted callee name for an ast.Call func node, e.g. 'InstrumentParser.parse'."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        base = _callee(func.value)
        return f"{base}.{func.attr}" if base else func.attr
    return None


def _func_def(tree, name, class_name=None):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and class_name and node.name == class_name:
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == name:
                    return sub
        if class_name is None and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"function {class_name + '.' if class_name else ''}{name} not found")


def _calls(node):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)]


def _imports_name(tree, dotted_module=None, name=None):
    """True if the module imports `name` or imports from `dotted_module`."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if dotted_module and node.module == dotted_module:
                return True
            if name and any(a.name == name for a in node.names):
                return True
        if isinstance(node, ast.Import):
            if name and any(a.name == name or a.name.endswith("." + name) for a in node.names):
                return True
    return False


def _py_files():
    return [p for p in CORE.rglob("*.py") if "__pycache__" not in p.parts]


def _rel(p):
    return p.relative_to(CORE).as_posix()


# --------------------------------------------------------------------------- #
# characterization harness (a REAL handler over an isolated tmp store)
# --------------------------------------------------------------------------- #
def _build_handler(tmp_path, monkeypatch, store_path):
    monkeypatch.setattr(
        handler_mod, "ExecutionStore", lambda *a, **k: ExecutionStore(str(store_path))
    )
    return ExecutionHandler(
        db_manager=DatabaseManager(data_root=tmp_path),
        clock=ReplayClock(FIXED_DT),
        broker=PaperBroker(ReplayClock(FIXED_DT)),
        config=ExecutionConfig(),
        metrics_path=str(tmp_path / "metrics.json"),
        load_db_state=True,
    )


def _signal(symbol, quantity, metadata=None):
    meta = {
        "quantity": quantity,
        "sl_distance": 5.0,
        "risk_r": 1.0,
        "signal_id": f"g1w5-{symbol}-{quantity}",
    }
    if metadata:
        meta.update(metadata)
    return SignalEvent(
        strategy_id="g1w5",
        symbol=symbol,
        timestamp=FIXED_DT,
        signal_type=SignalType.BUY,
        confidence=1.0,
        metadata=meta,
    )


def _order_by_symbol(handler, symbol):
    for state in handler.order_tracker.order_states():
        if state.order.symbol == symbol:
            return state.order
    raise AssertionError(f"no order for {symbol}")


# =========================================================================== #
# Requirement 1 — the live F&O order-build entry constructs no identity through
#                 parse / legacy Option / legacy Future (AST on process_signal)
# =========================================================================== #
def test_process_signal_constructs_no_legacy_option_or_future_directly():
    """The order-build entry never calls `Option(...)`/`Future(...)` itself — it
    delegates identity to the derive-to-legacy boundary (selector / canonicalize)."""
    fn = _func_def(_tree("execution/handler.py"), "process_signal", "ExecutionHandler")
    offenders = [_callee(c.func) for c in _calls(fn) if _callee(c.func) in {"Option", "Future"}]
    assert offenders == []


def test_process_signal_routes_options_through_selector():
    """Option ENTRY identity comes from `OptionsContractSelector.select` (O1)."""
    fn = _func_def(_tree("execution/handler.py"), "process_signal", "ExecutionHandler")
    callees = {_callee(c.func) for c in _calls(fn)}
    assert "OptionsContractSelector" in callees          # selector instantiated
    assert "select" in callees                            # ...().select(...) invoked


def test_process_signal_derivative_identity_via_canonicalize_symbol():
    """Non-option / EXIT derivative identity comes from `canonicalize_symbol` (#1/O2)."""
    fn = _func_def(_tree("execution/handler.py"), "process_signal", "ExecutionHandler")
    callees = {_callee(c.func) for c in _calls(fn)}
    assert "canonicalize_symbol" in callees


def test_process_signal_parse_is_only_the_guarded_fallback():
    """Every `InstrumentParser.parse` in the order-build entry is the equity/
    unresolved FALLBACK — it appears only inside an `IfExp.orelse`
    (`derived if derived is not None else InstrumentParser.parse(...)`), never as
    the primary identity source."""
    fn = _func_def(_tree("execution/handler.py"), "process_signal", "ExecutionHandler")
    all_parse = [c for c in _calls(fn) if _callee(c.func) == "InstrumentParser.parse"]
    guarded = set()
    for ifexp in (n for n in ast.walk(fn) if isinstance(n, ast.IfExp)):
        for c in _calls(ifexp.orelse):
            if _callee(c.func) == "InstrumentParser.parse":
                guarded.add(id(c))
    assert all_parse, "expected the guarded fallback to exist"
    assert all(id(c) in guarded for c in all_parse)


# =========================================================================== #
# Requirement 1 (repo-wide) — every parse / legacy-construction site in core/ is
#                 classified (carve-out / dead / restore-at-construction / fallback)
# =========================================================================== #
# Files allowed to call InstrumentParser.parse, each with its G1 classification.
_PARSE_ALLOWED = {
    "execution/handler.py":
        "process_signal guarded equity fallback (#1) + process_group_signal batch "
        "boundary (#2) + _check_greek_limits transient (#3 carve-out)",
    "execution/position_tracker.py":
        "get_position FLAT default (#7 source, H5) — parse-built, master-independent "
        "(ADR-003); forward positions canonicalize at the fill seam",
    "execution/position_models.py":
        "Position(symbol=) ctor (#6) — DEAD (no live caller)",
    "execution/persistence/order_repository.py":
        "order restore-at-construction (#8, Option B) — canonicalized post-gate",
    "execution/persistence/position_repository.py":
        "position restore-at-construction (#9, Option B) + load_all dead (H6)",
    "execution/order_factory.py":
        "OrderFactory.create_order (#5) — DEAD (no live caller, Wave 1 prove-dead)",
}


def test_no_unclassified_instrumentparser_parse_site_in_core():
    """No NEW `InstrumentParser.parse` call appears outside the audited allowlist.
    A new site (a new identity-construction path) fails this guard."""
    offenders = []
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(_callee(c.func) == "InstrumentParser.parse" for c in _calls(tree)):
            rel = _rel(path)
            if rel not in _PARSE_ALLOWED:
                offenders.append(rel)
    assert offenders == [], f"unclassified InstrumentParser.parse sites: {offenders}"


def test_handler_parse_calls_confined_to_audited_functions():
    """Inside handler.py, `InstrumentParser.parse` lives ONLY in the three audited
    functions — never sneaking into a new live order path."""
    tree = _tree("execution/handler.py")
    allowed = {"process_signal", "process_group_signal", "_check_greek_limits"}
    seen = set()
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(_callee(c.func) == "InstrumentParser.parse" for c in _calls(fn)):
                seen.add(fn.name)
    assert seen <= allowed, f"parse leaked into unaudited handler functions: {seen - allowed}"


# Files allowed to CONSTRUCT a legacy Option(...) / Future(...).
_CONSTRUCT_ALLOWED = {
    "instruments/instrument_parser.py":   # the legacy parser (carve-out/dead surfaces)
        "InstrumentParser.parse internal Option(lot=1)",
    "execution/futures.py":               # whitelisted derive-to-legacy boundary
        "resolve_future → Future derived from CanonicalInstrument (ADR-003 fallback)",
    "execution/options/selector.py":      # whitelisted derive-to-legacy boundary
        "select → Option derived from CanonicalInstrument (O1; INDEX fallback)",
    "execution/canonical_restore.py":     # whitelisted derive-to-legacy boundary
        "_resolve_option → Option derived from CanonicalInstrument (#2 restore primitive)",
}


def test_no_unwhitelisted_legacy_option_future_construction_in_core():
    """Every direct `Option(...)` / `Future(...)` construction in core/ is either the
    legacy parser or a whitelisted canonical-derivation point. A new direct
    construction (identity built without going through the resolver) fails."""
    offenders = []
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(_callee(c.func) in {"Option", "Future"} for c in _calls(tree)):
            rel = _rel(path)
            if rel not in _CONSTRUCT_ALLOWED:
                offenders.append(rel)
    assert offenders == [], f"unwhitelisted legacy construction sites: {offenders}"


# =========================================================================== #
# Requirement 2 — the whitelisted derivation points really resolve a
#                 CanonicalInstrument (derive-to-legacy), not arbitrary builds
# =========================================================================== #
def test_derivation_points_resolve_through_canonical():
    """Each whitelisted derivation module sources identity from the resolver
    (InstrumentResolver + resolve_future/resolve_option) — proving live derivative
    identity flows through CanonicalInstrument and is derived to legacy, not
    hand-built from a symbol string."""
    for rel in ("execution/futures.py", "execution/canonical_restore.py",
                "execution/options/selector.py"):
        src = (CORE / rel).read_text(encoding="utf-8")
        assert "InstrumentResolver" in src, f"{rel} does not use the resolver"
        assert ("resolve_future" in src or "resolve_option" in src), \
            f"{rel} does not resolve a canonical instrument"


def test_forward_futures_order_identity_is_canonical_derived(tmp_path, monkeypatch):
    """A live futures ENTRY produces a legacy Future (derived), never the parser's
    EQUITY mistype and never a raw CanonicalInstrument on the order."""
    order = _build_handler(tmp_path, monkeypatch, tmp_path / "execution.db").process_signal(
        _signal(FUTURES_SYMBOL, 50), current_price=23000.0)
    assert order.instrument.type == InstrumentType.FUTURE
    assert type(order.instrument).__name__ == "Future"
    assert order.symbol == FUTURES_SYMBOL                 # broker-facing symbol preserved


def test_forward_option_order_identity_is_canonical_derived(tmp_path, monkeypatch):
    """A live option ENTRY produces a legacy Option via the selector, with the
    selector-computed (master-independent) symbol preserved byte-for-byte."""
    order = _build_handler(tmp_path, monkeypatch, tmp_path / "execution.db").process_signal(
        _signal(OPTION_UNDERLYING, 75, metadata={"execution_mode": "option"}),
        current_price=OPTION_PRICE)
    assert order.instrument.type == InstrumentType.OPTION
    assert type(order.instrument).__name__ == "Option"
    assert order.symbol == EXPECTED_OPTION_SYMBOL


# =========================================================================== #
# Requirement 3 — CanonicalInstrument never crosses NormalizedOrder /
#                 persistence / broker payload
# =========================================================================== #
def test_canonical_not_imported_on_order_persistence_broker_boundary():
    """Persistence repositories, paper broker, and the live adapter never import
    `CanonicalInstrument` directly — canonical identity stays internal to the
    derivation points for these files.

    4C.7 BOUNDARY CROSSING (intentional, planned):
    `order_models.py` now carries `canonical_instrument: Optional[CanonicalInstrument]`
    so the adapter can translate it to a broker identity key via `UpstoxMapping`.
    This crossing is the explicit goal of 4C.7 (PHASE_4C_IMPLEMENTATION_PLAN.md §2)
    and was pre-approved in G1_CLOSEOUT_REPORT.md §F. `order_models.py` is therefore
    excluded from this list; all other boundary files remain forbidden.

    `upstox_adapter.py` imports `UpstoxMapping` (which internally uses CI) but does
    NOT directly import `CanonicalInstrument` — the AST check below stays green for
    it, and it remains in the list as a standing invariant."""
    boundary = [
        # order_models.py intentionally omitted — 4C.7 carries canonical_instrument
        # for adapter payload translation; see rationale above.
        CORE / "execution/persistence/order_repository.py",
        CORE / "execution/persistence/position_repository.py",
        CORE / "execution/persistence/execution_store.py",
        CORE / "brokers/paper_broker.py",
        CORE / "brokers/upstox_adapter.py",
    ]
    offenders = []
    for path in boundary:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if _imports_name(tree, dotted_module="core.instruments.canonical") or \
                _imports_name(tree, name="CanonicalInstrument"):
            offenders.append(path.name)
    assert offenders == [], f"CanonicalInstrument crossed the boundary in: {offenders}"


def test_instrument_key_absent_from_execution():
    """No `instrument_key` (the canonical broker key) is referenced anywhere in
    core/execution/ — order routing is symbol-keyed (the 4C.7 line uncrossed)."""
    offenders = [
        _rel(p) for p in (CORE / "execution").rglob("*.py")
        if "__pycache__" not in p.parts and "instrument_key" in p.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_order_path_does_not_import_broker_mapping():
    """The 4C BrokerMapping projection (the only canonical→instrument_key seam) is
    NOT wired into the order path — handler.py must not import core.brokers.mapping
    (wiring it IS 4C.7, still blocked)."""
    tree = _tree("execution/handler.py")
    assert not _imports_name(tree, dotted_module="core.brokers.mapping")
    assert not any(
        isinstance(n, ast.ImportFrom) and (n.module or "").startswith("core.brokers.mapping")
        for n in ast.walk(tree)
    )


def test_forward_order_instrument_is_legacy_not_canonical(tmp_path, monkeypatch):
    """Behavioral containment: the forward F&O order carries a legacy instrument,
    never a CanonicalInstrument."""
    order = _build_handler(tmp_path, monkeypatch, tmp_path / "execution.db").process_signal(
        _signal(FUTURES_SYMBOL, 50), current_price=23000.0)
    assert not isinstance(order.instrument, CanonicalInstrument)
    assert type(order.instrument).__name__ in {"Future", "Option", "Equity"}


def test_persisted_order_schema_is_symbol_keyed():
    """The execution-truth `orders`/`positions` DDL persists a `symbol` string,
    with NO canonical identity column — a structural identity column added here
    would be a persistence leak."""
    ddl = (CORE / "execution/persistence/execution_store.py").read_text(encoding="utf-8")
    assert "symbol" in ddl
    for forbidden in ("instrument_key", "canonical_id", "lot_size"):
        assert forbidden not in ddl, f"{forbidden} must not be a persisted column"


# =========================================================================== #
# Requirement 4 — restore upgrades ONLY after MM.4 readiness, before reconcile
# =========================================================================== #
def test_canonicalize_runs_after_readiness_before_reconcile():
    """In `_run_startup_gate` the canonicalization pass is slotted strictly AFTER
    `_check_master_readiness` and strictly BEFORE `_reconcile_ledger` (Option B —
    identity is trustworthy before positions are matched through it)."""
    gate = _func_def(_tree("runtime/driver.py"), "_run_startup_gate", "LoopDriver")
    line = {}
    for c in _calls(gate):
        name = _callee(c.func)
        for target in ("_check_master_readiness", "_canonicalize_restored_ledger", "_reconcile_ledger"):
            if name and name.endswith(target):
                line[target] = c.lineno
    assert {"_check_master_readiness", "_canonicalize_restored_ledger", "_reconcile_ledger"} <= line.keys()
    assert line["_check_master_readiness"] < line["_canonicalize_restored_ledger"] < line["_reconcile_ledger"]


def test_canonicalize_gated_like_mm4_and_upgrades_both_halves():
    """`_canonicalize_restored_ledger` is gated on the SAME condition as MM.4
    (LIVE ∧ derivatives ∧ an injected master-readiness checker) and upgrades BOTH
    restored halves — positions (#7-as-restored) and orders (#8)."""
    driver_src = (CORE / "runtime/driver.py").read_text(encoding="utf-8")
    fn = _func_def(ast.parse(driver_src), "_canonicalize_restored_ledger", "LoopDriver")
    src = ast.get_source_segment(driver_src, fn)
    assert "is_live" in src and "has_derivatives" in src and "master_readiness" in src
    callees = {_callee(c.func) for c in _calls(fn)}
    assert any(c and c.endswith("canonicalize_restored_positions") for c in callees)
    assert any(c and c.endswith("canonicalize_restored_orders") for c in callees)


def test_restore_is_legacy_at_construction_then_upgrades_post_gate(tmp_path, monkeypatch):
    """Option B behavioral proof: a restored futures order is LEGACY (EQUITY) at
    construction (master-independent), and the post-gate pass — the only upgrade
    path — flips it to the canonical-derived FUTURE."""
    store_path = tmp_path / "execution.db"
    ha = _build_handler(tmp_path, monkeypatch, store_path)
    ha.process_signal(_signal(FUTURES_SYMBOL, 50), current_price=23000.0)

    hb = _build_handler(tmp_path, monkeypatch, store_path)   # reload from ledger
    assert _order_by_symbol(hb, FUTURES_SYMBOL).instrument.type == InstrumentType.EQUITY

    hb.canonicalize_restored_orders()                        # the post-gate pass
    assert _order_by_symbol(hb, FUTURES_SYMBOL).instrument.type == InstrumentType.FUTURE


# =========================================================================== #
# Requirement 5 — site #6 (Position(symbol=)) remains dead
# =========================================================================== #
def test_position_symbol_constructor_has_no_production_callers():
    """#6 stays dead: no production module constructs `Position(symbol=...)` (the
    parser-defaulting ctor branch). The definition module itself documents the
    signature in its ctor — excluded; deadness is asserted on CALLERS."""
    definition = CORE / "execution" / "position_models.py"
    offenders = [
        _rel(p) for p in _py_files()
        if p != definition and "Position(symbol=" in p.read_text(encoding="utf-8")
    ]
    assert offenders == []
