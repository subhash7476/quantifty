import json
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from flask import render_template, jsonify, request, current_app

from . import data_bp
from flask_app.middleware import login_required
from app_facade.data_facade import DataFacade
from core.logging import setup_logger

logger = setup_logger("data_bp")


def _get_facade() -> DataFacade:
    return DataFacade()


# ── Page ──────────────────────────────────────────────────────────────

@data_bp.route('/')
@login_required
def index():
    return render_template('data/index.html')


# ── Overview ──────────────────────────────────────────────────────────

@data_bp.route('/api/overview')
@login_required
def overview():
    try:
        facade = _get_facade()
        stores = facade.get_store_overview()
        return jsonify({"success": True, "stores": stores})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── Explorer ──────────────────────────────────────────────────────────

@data_bp.route('/api/tables')
@login_required
def list_tables():
    try:
        facade = _get_facade()
        tables = facade.list_all_tables()
        return jsonify({"success": True, "tables": tables})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/schema', methods=['POST'])
@login_required
def table_schema():
    try:
        data = request.get_json()
        facade = _get_facade()
        result = facade.get_table_schema(data["store_path"], data["table_name"])
        if result is None:
            return jsonify({"success": False, "message": "Store not found"}), 404
        if "error" in result:
            return jsonify({"success": False, "message": result["error"]}), 500
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/browse', methods=['POST'])
@login_required
def browse_table():
    try:
        data = request.get_json()
        facade = _get_facade()
        result = facade.browse_table(
            store_path=data["store_path"],
            table_name=data["table_name"],
            page=int(data.get("page", 1)),
            page_size=int(data.get("page_size", 50)),
            filters=data.get("filters"),
            order_by=data.get("order_by"),
            order_dir=data.get("order_dir", "ASC"),
        )
        if "error" in result:
            return jsonify({"success": False, "message": result["error"]}), 500
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── Query ─────────────────────────────────────────────────────────────

@data_bp.route('/api/stores')
@login_required
def list_stores():
    try:
        facade = _get_facade()
        stores = facade.get_queryable_stores()
        return jsonify({"success": True, "stores": stores})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/sql', methods=['POST'])
@login_required
def execute_sql():
    try:
        data = request.get_json()
        facade = _get_facade()
        result = facade.execute_sql(
            store_path=data["store_path"],
            sql=data["sql"],
            limit=int(data.get("limit", 1000)),
        )
        if "error" in result:
            return jsonify({"success": False, "message": result["error"]}), 400
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── Ingestion ─────────────────────────────────────────────────────────

@data_bp.route('/api/ingestion/pipelines')
@login_required
def list_pipelines():
    try:
        facade = _get_facade()
        pipelines = facade.get_pipelines()
        return jsonify({"success": True, "pipelines": pipelines})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/ingestion/run', methods=['POST'])
@login_required
def run_pipeline():
    try:
        data = request.get_json()
        facade = _get_facade()
        result = facade.run_pipeline(data["pipeline_id"], data.get("params"))
        if "error" in result:
            return jsonify({"success": False, "message": result["error"]}), 400
        return jsonify({"success": True, "job": result})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/ingestion/status/<pipeline_id>')
@login_required
def job_status(pipeline_id):
    try:
        facade = _get_facade()
        job = facade.get_job_status(pipeline_id)
        if not job:
            return jsonify({"success": True, "job": None})
        return jsonify({"success": True, "job": job})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── Schedule ──────────────────────────────────────────────────────────

@data_bp.route('/api/schedule')
@login_required
def list_scheduled():
    try:
        facade = _get_facade()
        jobs = facade.list_scheduled_jobs()
        return jsonify({"success": True, "jobs": jobs})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/schedule', methods=['POST'])
@login_required
def create_scheduled():
    try:
        data = request.get_json()
        facade = _get_facade()
        job = facade.create_scheduled_job(data)
        return jsonify({"success": True, "job": job})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/schedule/<job_id>', methods=['PUT'])
@login_required
def update_scheduled(job_id):
    try:
        data = request.get_json()
        facade = _get_facade()
        job = facade.update_scheduled_job(job_id, data)
        if job is None:
            return jsonify({"success": False, "message": "Job not found"}), 404
        return jsonify({"success": True, "job": job})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/schedule/<job_id>', methods=['DELETE'])
@login_required
def delete_scheduled(job_id):
    try:
        facade = _get_facade()
        deleted = facade.delete_scheduled_job(job_id)
        return jsonify({"success": True, "deleted": deleted})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── Downloads (manual historical fetch) ───────────────────────────────

@data_bp.route('/api/download/historical', methods=['POST'])
@login_required
def request_download():
    try:
        data = request.get_json()
        instrument_key = data['instrument_key']

        if instrument_key != 'ALL' and ',' not in instrument_key and '|' not in instrument_key:
            from core.database.utils.symbol_utils import resolve_to_instrument_key
            resolved_key = resolve_to_instrument_key(instrument_key)
            if resolved_key:
                instrument_key = resolved_key
            else:
                return jsonify({"success": False, "message": f"Could not resolve: {data['instrument_key']}"}), 400

        workers = data.get('workers', 5)
        cmd = [
            'python', 'scripts/fetch_upstox_historical.py',
            '--instrument_key', instrument_key,
            '--unit', data['unit'],
            '--interval', str(data['interval']),
            '--from', data['from_date'],
            '--to', data['to_date'],
            '--workers', str(workers),
        ]

        logger.info(f"Download: {instrument_key} ({data['unit']} {data['interval']}) {data['from_date']}→{data['to_date']}")

        def _run():
            try:
                subprocess.run(cmd, capture_output=True, text=True)
            except Exception as e:
                logger.error(f"Download failed: {e}")

        threading.Thread(target=_run, daemon=True).start()
        return jsonify({"success": True, "message": "Download started"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/nifty50-symbols')
@login_required
def nifty50_symbols():
    try:
        csv_path = Path("data/nifty-50-stock-list.csv")
        if not csv_path.exists():
            return jsonify({"success": False, "message": "Nifty 50 CSV not found"}), 404

        import pandas as pd
        df = pd.read_csv(csv_path)
        symbols = df['Symbol'].tolist()

        facade = _get_facade()
        # Minimal resolution via a simple DuckDB query on config
        import duckdb
        config_path = Path("data") / "config.duckdb" if (Path("data") / "config.duckdb").exists() else None
        if not config_path or not config_path.exists():
            config_path = next(Path("data").rglob("config*.duckdb"), None)
        resolved = []
        if config_path:
            conn = duckdb.connect(str(config_path), read_only=True)
            chunk_size = 500
            for i in range(0, len(symbols), chunk_size):
                chunk = symbols[i:i + chunk_size]
                placeholders = ', '.join(['?'] * len(chunk))
                try:
                    rows = conn.execute(
                        f"SELECT instrument_key, trading_symbol FROM instrument_meta WHERE trading_symbol IN ({placeholders}) AND exchange = 'NSE' AND market_type = 'NSE_EQ'",
                        chunk,
                    ).fetchall()
                    for r in rows:
                        resolved.append({"instrument_key": r[0], "trading_symbol": r[1]})
                except Exception:
                    continue
            conn.close()

        return jsonify({"success": True, "data": resolved})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/historical-dates')
@login_required
def historical_dates():
    try:
        dates_dir = Path("data/market_data/nse/candles/1m")
        if not dates_dir.exists():
            return jsonify({"success": True, "dates": []})
        dates = sorted([f.stem for f in dates_dir.glob("*.duckdb")], reverse=True)
        return jsonify({"success": True, "dates": dates})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/historical-symbols/<date_str>')
@login_required
def historical_symbols(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        file_path = Path(f"data/market_data/nse/candles/1m/{date_str}.duckdb")
        if not file_path.exists():
            return jsonify({"success": False, "message": f"No data for {date_str}"}), 404
        import duckdb
        conn = duckdb.connect(str(file_path), read_only=True)
        try:
            symbols = [r[0] for r in conn.execute("SELECT DISTINCT symbol FROM candles ORDER BY symbol").fetchall()]
            return jsonify({"success": True, "symbols": symbols})
        finally:
            conn.close()
    except ValueError:
        return jsonify({"success": False, "message": "Invalid date format"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@data_bp.route('/api/historical-data', methods=['POST'])
@login_required
def historical_data():
    try:
        data = request.get_json()
        date_str = data.get('date')
        symbol = data.get('symbol')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        page_size = int(data.get('page_size', 100))
        page = int(data.get('page', 1))

        datetime.strptime(date_str, "%Y-%m-%d")
        file_path = Path(f"data/market_data/nse/candles/1m/{date_str}.duckdb")
        if not file_path.exists():
            return jsonify({"success": False, "message": f"No data for {date_str}"}), 404

        import duckdb
        conn = duckdb.connect(str(file_path), read_only=True)
        try:
            where = ["symbol = ?"]
            params = [symbol]
            if start_time:
                where.append("timestamp >= ?")
                params.append(start_time)
            if end_time:
                where.append("timestamp <= ?")
                params.append(end_time)
            where_clause = " AND ".join(where)

            total = conn.execute(f"SELECT COUNT(*) FROM candles WHERE {where_clause}", params).fetchone()[0]
            offset = (page - 1) * page_size
            cursor = conn.execute(
                f"SELECT * FROM candles WHERE {where_clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [page_size, offset],
            )
            cols = [d[0] for d in cursor.description]
            rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
            return jsonify({"success": True, "data": rows, "total": total, "page_size": page_size, "page": page})
        finally:
            conn.close()
    except ValueError:
        return jsonify({"success": False, "message": "Invalid date format"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
