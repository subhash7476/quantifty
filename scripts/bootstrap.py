"""First-run setup and daily seed refresh for a fresh clone (Upstox, trading profile).

    python scripts/bootstrap.py init     # once: .env, credentials, dashboard user, stores, master
    python scripts/bootstrap.py seed     # after the first Upstox login, then daily (incremental)

`init` needs no Upstox token. It writes `.env` from `.env.example` (with a fresh
SECRET_KEY and NIFTY_PROFILE=trading), `config/credentials.json` from the template
(your Upstox API key/secret/redirect URI), the dashboard login user, the empty
stores that must exist before the first start, and today's instrument master.

`seed` needs a valid token. It pulls from Upstox — never from NSE bhavcopy — the
small history the two paper runners read:

  - Nifty 50 / Bank Nifty / India VIX daily candles, ~3.5 years
    -> data/market_data/nse/candles/1d/  -> data/nifty_shield/vix_history.duckdb
       (NiftyShield's VIX-percentile gate needs >= 189, ideally 756 sessions)
  - Nifty / Bank Nifty / India VIX / Sensex 1m candles, last ~10 days
    -> data/market_data/{nse,bse}/candles/1m/  (Options-Wall realized vol: 5 sessions)
  - today's NSE SPAN file -> data/span/  (margin evidence; absence only warns)

Every step is idempotent: re-running only fetches what is missing. Under
`--profile trading` the orchestrator runs `seed` as its morning catch-up.
"""
from __future__ import annotations

import argparse
import getpass
import json
import secrets
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PY = sys.executable
MIN_PYTHON = (3, 11)
ENV_EXAMPLE = ROOT / ".env.example"
ENV_FILE = ROOT / ".env"
CRED_TEMPLATE = ROOT / "config" / "credentials.template.json"
CRED_FILE = ROOT / "config" / "credentials.json"
DEFAULT_REDIRECT = "http://127.0.0.1:5000/ops/callback/upstox"
CANDLES = ROOT / "data" / "market_data" / "nse" / "candles"

DAILY_SYMBOLS = ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank", "NSE_INDEX|India VIX"]
MINUTE_SYMBOLS = DAILY_SYMBOLS + ["BSE_INDEX|SENSEX"]
DAILY_SEED_DAYS = 1300   # ~3.5 calendar years -> > 756 sessions for the VIX percentile
MINUTE_SEED_DAYS = 10    # >= 5 sessions for the Options-Wall realized vol
MIN_VIX_SESSIONS = 189   # vix_percentile.percentile() returns None below 756 // 4
MIN_RV_SESSIONS = 5      # options_wall realized vol lookback (session_realized_vol_pct)

DATA_DIRS = [
    "data/config", "data/ops", "data/instruments", "data/options", "data/span",
    "data/nifty_shield", "data/features/day_type", "data/live_buffer",
    "data/market_data/nse/candles/1m", "data/market_data/nse/candles/1d",
    "data/market_data/bse/candles/1m", "logs",
]


# --------------------------------------------------------------------------- #
# init
# --------------------------------------------------------------------------- #
def _check_python() -> None:
    if sys.version_info < MIN_PYTHON:
        raise SystemExit(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required "
                         f"(numpy/scipy/scikit-learn pins); this is {sys.version.split()[0]}")


def _write_env() -> None:
    if ENV_FILE.exists():
        print("  .env exists - left as is")
        return
    lines = []
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        if line.startswith("SECRET_KEY="):
            line = f"SECRET_KEY={secrets.token_hex(32)}"
        elif line == "UPSTOX_NOTIFY_SECRET=":
            line = f"UPSTOX_NOTIFY_SECRET={secrets.token_urlsafe(24)}"
        lines.append(line)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  .env written (fresh SECRET_KEY and UPSTOX_NOTIFY_SECRET, NIFTY_PROFILE=trading)")


def _write_credentials(api_key: Optional[str], api_secret: Optional[str],
                       redirect_uri: Optional[str]) -> None:
    if CRED_FILE.exists():
        print("  config/credentials.json exists - left as is")
        return
    cred = json.loads(CRED_TEMPLATE.read_text(encoding="utf-8"))
    for k in list(cred):
        if isinstance(cred[k], str):
            cred[k] = ""
    cred["api_key"] = api_key or input("  Upstox API key: ").strip()
    cred["api_secret"] = api_secret or getpass.getpass("  Upstox API secret: ").strip()
    cred["redirect_uri"] = (redirect_uri
                            or input(f"  Redirect URI [{DEFAULT_REDIRECT}]: ").strip()
                            or DEFAULT_REDIRECT)
    cred["token_saved_at"] = 0
    CRED_FILE.write_text(json.dumps(cred, indent=4), encoding="utf-8")
    print("  config/credentials.json written (no token yet - log in next)")


def _create_dashboard_user(username: Optional[str], password: Optional[str]) -> None:
    from core.auth.password import hash_password
    from core.database import schema
    from core.database.manager import DatabaseDomain, DatabaseManager

    db = DatabaseManager(ROOT / "data")
    with db.write(DatabaseDomain.CONFIG) as conn:
        conn.execute(schema.CONFIG_USERS_SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] and not username:
            print("  dashboard user exists - left as is")
            return
        username = username or input("  Dashboard username [admin]: ").strip() or "admin"
        while not password:
            password = getpass.getpass(f"  Dashboard password for {username}: ")
        conn.execute("INSERT OR REPLACE INTO users (username, password_hash, roles) "
                     "VALUES (?, ?, ?)", [username, hash_password(password), "admin"])
    print(f"  dashboard user '{username}' ready")


def _create_stores() -> None:
    import duckdb
    from scripts.daytype import vix_percentile

    con = duckdb.connect(str(vix_percentile.CACHE))
    try:
        vix_percentile._ensure_table(con)
    finally:
        con.close()
    print("  data/ directories + vix_history store ready "
          "(chain, wall, facts and trade stores are created by their writers on first run)")


def _refresh_master() -> bool:
    from scripts import fetch_instrument_master as fim
    rc = fim.run_refresh(db_path=fim.DB_PATH)
    print(f"  instrument master: {'ok' if rc == fim.EXIT_OK else f'FAILED (exit {rc})'}")
    return rc == fim.EXIT_OK


def cmd_init(args) -> int:
    _check_python()
    print("bootstrap init")
    for d in DATA_DIRS:
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    _write_env()
    _write_credentials(args.api_key, args.api_secret, args.redirect_uri)
    _create_dashboard_user(args.user, args.password)
    _create_stores()
    ok = _refresh_master()
    print("\nnext: log in to Upstox once, then run  python scripts/bootstrap.py seed")
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# seed
# --------------------------------------------------------------------------- #
def _latest_file_date(directory: Path) -> Optional[date]:
    dates = []
    for p in directory.glob("*.duckdb"):
        try:
            dates.append(date.fromisoformat(p.stem))
        except ValueError:
            continue
    return max(dates) if dates else None


def _window(directory: Path, seed_days: int, today: date) -> Optional[tuple]:
    """(from, to) up to yesterday; re-reads the last stored day so a partial file heals."""
    yesterday = today - timedelta(days=1)
    latest = _latest_file_date(directory)
    start = latest if latest is not None else today - timedelta(days=seed_days)
    return None if start > yesterday else (start, yesterday)


def _fetch(symbols: List[str], unit: str, start: date, end: date) -> bool:
    argv = [PY, str(ROOT / "scripts" / "fetch_upstox_historical.py"),
            "--instrument_key", ",".join(symbols), "--unit", unit, "--interval", "1",
            "--from", start.isoformat(), "--to", end.isoformat(), "--no-intraday"]
    return subprocess.run(argv, cwd=str(ROOT)).returncode == 0


def _token_ok() -> bool:
    from core.auth.credentials import credentials
    credentials._load()
    return credentials.has_upstox_token and not credentials.is_token_expired


def cmd_seed(args) -> int:
    from scripts.daytype import vix_percentile

    print("bootstrap seed")
    if not _token_ok():
        print("  no valid Upstox token - log in first (orchestrator, dashboard "
              "/ops/login/upstox, or scripts/auth_upstox_cli.py)")
        return 1
    today = date.today()
    ok = True
    for symbols, unit, directory, days in (
            (DAILY_SYMBOLS, "days", CANDLES / "1d", DAILY_SEED_DAYS),
            (MINUTE_SYMBOLS, "minutes", CANDLES / "1m", MINUTE_SEED_DAYS)):
        window = _window(directory, days, today)
        if window is None:
            print(f"  {unit}: up to date")
            continue
        print(f"  {unit}: {window[0]} -> {window[1]}")
        ok = _fetch(symbols, unit, *window) and ok
    added = vix_percentile.refresh()
    print(f"  vix_history: +{added} session(s)")
    if not args.skip_span:
        span_ok = subprocess.run([PY, str(ROOT / "scripts" / "fetch_span_params.py")],
                                 cwd=str(ROOT)).returncode == 0
        print(f"  SPAN: {'ok' if span_ok else 'unavailable (warning only)'}")
    # The fetcher logs write errors and still exits 0, so check what landed.
    return 0 if _verify_seed() and ok else 1


def _verify_seed() -> bool:
    """The runners' minimums: without them nothing errors, the strategies just
    behave differently (NiftyShield always a straddle, Options-Wall never enters)."""
    import duckdb
    from core.analytics.realized_vol import _load_sessions
    from scripts.daytype import vix_percentile

    con = duckdb.connect(str(vix_percentile.CACHE), read_only=True)
    try:
        vix_rows = con.execute("SELECT COUNT(*) FROM vix_history").fetchone()[0]
    finally:
        con.close()
    problems = []
    if vix_rows < MIN_VIX_SESSIONS:
        problems.append(f"vix_history has {vix_rows} sessions, NiftyShield's VIX gate "
                        f"needs >= {MIN_VIX_SESSIONS} (756 ideal)")
    for symbol in MINUTE_SYMBOLS:
        n = len(_load_sessions(symbol, MIN_RV_SESSIONS))
        if n < MIN_RV_SESSIONS:
            problems.append(f"{symbol}: {n} sessions of 1m bars, Options-Wall realized "
                            f"vol needs {MIN_RV_SESSIONS}")
    for line in problems:
        print(f"  SEED INCOMPLETE - {line}")
    if not problems:
        print(f"  verified: {vix_rows} VIX sessions, >= {MIN_RV_SESSIONS} 1m sessions per index")
    return not problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init", help="first-run setup (no token needed)")
    p_init.add_argument("--api-key")
    p_init.add_argument("--api-secret")
    p_init.add_argument("--redirect-uri")
    p_init.add_argument("--user", help="dashboard username (prompted if omitted)")
    p_init.add_argument("--password", help="dashboard password (prompted if omitted)")
    p_seed = sub.add_parser("seed", help="fetch/refresh the Upstox history the runners read")
    p_seed.add_argument("--skip-span", action="store_true")
    args = parser.parse_args(argv)
    return cmd_init(args) if args.command == "init" else cmd_seed(args)


if __name__ == "__main__":
    raise SystemExit(main())
