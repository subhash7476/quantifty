"""
Data Facade
-----------
Bridge between Flask UI and core data infrastructure.
Handles store overview, SQL execution, ingestion pipeline management, and scheduling.
"""
import json
import os
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data")).resolve()


class DataFacade:
    _running_jobs: dict[str, dict] = {}
    _jobs_lock = threading.Lock()

    def __init__(self, data_root: Path | None = None):
        self._root = data_root or DATA_ROOT
        self._ensure_schedule_store()

    # ── Overview ──────────────────────────────────────────────────────

    def get_store_overview(self) -> list[dict]:
        stores: list[dict] = []
        market_data = self._root / "market_data"

        for pattern, label, description in [
            ("equity_bhavcopy.duckdb", "Equity Bhavcopy", "NSE cash market daily OHLCV + delivery"),
            ("futures_bhavcopy.duckdb", "Futures Bhavcopy", "FUTSTK/FUTIDX daily OHLCV + OI"),
            ("stock_options_bhavcopy.duckdb", "Stock Options", "OPTSTK daily data"),
            ("options_bhavcopy.duckdb", "Index Options", "OPTIDX daily data"),
            ("equity_bhavcopy_devtruncated.duckdb", "Equity (Dev-Truncated)", "Dev copy <= 2022-12-30"),
            ("equity_bhavcopy_mto_backfill.duckdb", "Equity (MTO Backfill)", "Delivery backfill from MTO"),
        ]:
            path = market_data / pattern
            stores.append(self._inspect_store(path, label, description, "market_data"))

        for name, description in [
            ("carry/nifty50.duckdb", "Carry — Nifty 50"),
            ("carry/signals.duckdb", "Carry — Signals"),
            ("carry/facts.duckdb", "Carry — Facts"),
            ("trend/continuous.duckdb", "Trend — Continuous"),
            ("trend/signals.duckdb", "Trend — Signals"),
            ("skew/signals.duckdb", "Skew — Signals"),
        ]:
            path = self._root / "signal_engine" / name
            stores.append(self._inspect_store(path, name.rsplit("/", 1)[-1].replace(".duckdb", ""), description, "signal_engine"))

        instruments_path = self._root / "instruments" / "nse_fo_instruments.duckdb"
        stores.append(self._inspect_store(instruments_path, "Instrument Master", "Upstox F&O instrument master", "instruments"))

        candle_dirs = [
            ("nse/candles/1m", "1-Minute Candles", "Per-day 1m candle files"),
            ("nse/candles/1d", "Daily Index Candles", "Per-day index close files"),
        ]
        for rel_dir, label, description in candle_dirs:
            dir_path = market_data / rel_dir
            if dir_path.exists():
                files = list(dir_path.glob("*.duckdb"))
                total_size = sum(f.stat().st_size for f in files)
                stores.append({
                    "name": label,
                    "description": description,
                    "category": "market_data",
                    "path": str(dir_path),
                    "exists": True,
                    "size_mb": round(total_size / (1024 * 1024), 2),
                    "file_count": len(files),
                    "is_directory": True,
                    "last_modified": max(f.stat().st_mtime for f in files) if files else None,
                })
            else:
                stores.append({
                    "name": label, "description": description, "category": "market_data",
                    "path": str(dir_path), "exists": False, "size_mb": 0, "file_count": 0,
                    "is_directory": True, "last_modified": None,
                })

        return stores

    def _inspect_store(self, path: Path, name: str, description: str, category: str) -> dict:
        if not path.exists():
            return {
                "name": name, "description": description, "category": category,
                "path": str(path), "exists": False, "size_mb": 0,
                "row_count": 0, "table_count": 0, "tables": [],
                "last_modified": None, "is_directory": False, "file_count": 0,
            }
        stat = path.stat()
        tables = []
        try:
            conn = duckdb.connect(str(path), read_only=True)
            rows = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
            for (tbl,) in rows:
                try:
                    cnt = conn.execute(f"SELECT COUNT(*) FROM \"{tbl}\"").fetchone()[0]
                except Exception:
                    cnt = 0
                tables.append({"name": tbl, "row_count": cnt})
            conn.close()
        except Exception:
            pass

        return {
            "name": name, "description": description, "category": category,
            "path": str(path), "exists": True,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "row_count": sum(t["row_count"] for t in tables),
            "table_count": len(tables), "tables": tables,
            "last_modified": stat.st_mtime,
            "is_directory": False, "file_count": 1,
        }

    # ── SQL Query ─────────────────────────────────────────────────────

    def get_queryable_stores(self) -> list[dict]:
        stores: list[dict] = []
        for root, _, files in os.walk(self._root):
            for f in files:
                if f.endswith(".duckdb") or f.endswith(".db"):
                    full = Path(root) / f
                    rel = str(full.relative_to(self._root))
                    size = round(full.stat().st_size / (1024 * 1024), 2)
                    stores.append({"label": f"{rel} ({size:.1f} MB)", "value": rel, "path": str(full), "size_mb": size})
        stores.sort(key=lambda s: s["label"])
        return stores

    def execute_sql(self, store_path: str, sql: str, limit: int = 1000) -> dict:
        full = (self._root / store_path).resolve()
        if not full.exists():
            return {"error": f"Store not found: {store_path}"}
        if not str(full).startswith(str(self._root)):
            return {"error": "Invalid store path"}
        read_only = not str(full).endswith(".db")  # .db files may be SQLite and need write
        conn = duckdb.connect(str(full), read_only=read_only)
        try:
            sql_upper = sql.strip().upper()
            if sql_upper.startswith("SELECT") or sql_upper.startswith("DESCRIBE") or sql_upper.startswith("SHOW") or sql_upper.startswith("PRAGMA"):
                result = conn.execute(sql).fetchall()
                cols = [d[0] for d in conn.description] if conn.description else []
                rows = [dict(zip(cols, row)) for row in result[:limit]]
                return {"columns": cols, "rows": rows, "total_rows": len(result), "truncated": len(result) > limit}
            else:
                conn.execute(sql)
                return {"columns": [], "rows": [], "affected_rows": 0, "message": "Executed successfully"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            conn.close()

    # ── Ingestion ─────────────────────────────────────────────────────

    PIPELINES = [
        {
            "id": "equity_bhavcopy",
            "name": "Equity Bhavcopy",
            "description": "NSE cash market daily OHLCV + delivery data (2010–present)",
            "script": "scripts/csmp/ingest_equity_bhavcopy.py",
            "category": "market_data",
            "params": [
                {"name": "start", "label": "Start Date", "type": "date", "default": "2010-01-01"},
                {"name": "end", "label": "End Date", "type": "date", "default": ""},
            ],
        },
        {
            "id": "corporate_actions",
            "name": "Corporate Actions",
            "description": "Splits, bonuses, dividends — full rebuild of adjusted view",
            "script": "scripts/csmp/ingest_corporate_actions.py",
            "category": "market_data",
            "params": [],
        },
        {
            "id": "index_history",
            "name": "Index History",
            "description": "NSE daily index close data (2012–present)",
            "script": "scripts/ingest_index_history.py",
            "category": "market_data",
            "params": [
                {"name": "archive_only", "label": "Archive Only", "type": "bool", "default": ""},
            ],
        },
        {
            "id": "futures_bhavcopy",
            "name": "Futures Bhavcopy",
            "description": "FUTSTK/FUTIDX daily bhavcopy (2016–present)",
            "script": "scripts/sfb/ingest_futures_bhavcopy_v2.py",
            "cli_positional": ["start", "end"],
            "category": "market_data",
            "params": [
                {"name": "start", "label": "Start Date", "type": "date", "default": "2016-02-11"},
                {"name": "end", "label": "End Date", "type": "date", "default": ""},
            ],
        },
        {
            "id": "stock_options",
            "name": "Stock Options Bhavcopy",
            "description": "OPTSTK daily bhavcopy (2016–present)",
            "script": "scripts/sfb/ingest_stock_options_bhavcopy.py",
            "cli_positional": ["start", "end"],
            "category": "market_data",
            "params": [
                {"name": "start", "label": "Start Date", "type": "date", "default": "2016-02-11"},
                {"name": "end", "label": "End Date", "type": "date", "default": ""},
            ],
        },
        {
            "id": "instrument_master",
            "name": "Instrument Master",
            "description": "Upstox instrument master refresh (NSE_FO, MCX_FO, NSE_EQ, NSE_INDEX)",
            "script": "scripts/fetch_instrument_master.py",
            "category": "reference",
            "params": [],
        },
        {
            "id": "intermarket_data",
            "name": "Intermarket Data",
            "description": "1m candles for indices and MCX commodities via Upstox",
            "script": "scripts/fetch_intermarket_data.py",
            "category": "market_data",
            "params": [
                {"name": "preset", "label": "Preset", "type": "select", "options": ["intermarket", "mcx_commodity"], "default": "intermarket"},
                {"name": "from", "label": "From", "type": "date", "default": ""},
                {"name": "to", "label": "To", "type": "date", "default": ""},
            ],
        },
        {
            "id": "universe",
            "name": "Universe Builder",
            "description": "NIFTY-200 point-in-time universe membership",
            "script": "scripts/csmp/build_universe.py",
            "category": "derived",
            "params": [],
        },
        {
            "id": "continuous_futures",
            "name": "Continuous Futures",
            "description": "Near-month continuous forward-adjusted series",
            "script": "scripts/sfb/build_continuous_futures.py",
            "category": "derived",
            "params": [],
        },
        {
            "id": "sector",
            "name": "Sector Classification",
            "description": "Three-tier sector classification (NSE taxonomy)",
            "script": "scripts/g2_ingest_sector_classification.py",
            "category": "reference",
            "params": [],
        },
    ]

    def get_pipelines(self) -> list[dict]:
        result = []
        for p in self.PIPELINES:
            job = DataFacade._running_jobs.get(p["id"])
            result.append({
                **p,
                "status": job["status"] if job else "idle",
                "last_run": job.get("started") if job else None,
                "last_result": job.get("result") if job else None,
                "job_id": job.get("job_id") if job else None,
                "detection": job.get("detection") if job else None,
                "effective_params": job.get("effective_params") if job else None,
            })
        return result

    _STORE_RANGES: dict[str, tuple[str, str, str]] = {
        "equity_bhavcopy": (DATA_ROOT / "market_data" / "equity_bhavcopy.duckdb", "equity_bhavcopy", "trade_date"),
        "futures_bhavcopy": (DATA_ROOT / "market_data" / "futures_bhavcopy.duckdb", "futures_bhavcopy", "trade_date"),
        "stock_options": (DATA_ROOT / "market_data" / "stock_options_bhavcopy.duckdb", "stock_options_bhavcopy", "trade_date"),
    }

    @staticmethod
    def _detect_latest_date(store_path: Path, table: str, col: str) -> str | None:
        try:
            if not store_path.exists():
                return None
            conn = duckdb.connect(str(store_path), read_only=True)
            row = conn.execute(f"SELECT MAX({col}) FROM \"{table}\"").fetchone()
            conn.close()
            return str(row[0])[:10] if row and row[0] else None
        except Exception as e:
            return None

    def run_pipeline(self, pipeline_id: str, params: dict | None = None) -> dict:
        import subprocess
        pipeline = next((p for p in self.PIPELINES if p["id"] == pipeline_id), None)
        if not pipeline:
            return {"error": f"Unknown pipeline: {pipeline_id}"}

        # Smart incremental detection: if no explicit params, check existing store
        resolved_params = {}
        detection_note = None
        has_range_store = pipeline["id"] in DataFacade._STORE_RANGES
        has_date_params = any(p.get("type") == "date" for p in pipeline.get("params", []))

        if not params:
            if has_range_store and has_date_params:
                store_info = DataFacade._STORE_RANGES.get(pipeline["id"])
                store_path, table, col = store_info
                latest = DataFacade._detect_latest_date(store_path, table, col)
                if latest:
                    from datetime import timedelta
                    next_date = (datetime.strptime(latest, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                    resolved_params["start"] = next_date
                    detection_note = f"auto: {latest} -> {next_date}"
                else:
                    detection_note = "no prior data, using full range"
            elif not has_date_params:
                detection_note = "full rebuild (no incremental)"
            else:
                detection_note = "date range not configured, using defaults"
        else:
            resolved_params = dict(params)
            detection_note = "explicit params"

        job_id = str(uuid.uuid4())[:8]
        job = {
            "job_id": job_id,
            "pipeline_id": pipeline_id,
            "status": "running",
            "started": datetime.now().isoformat(),
            "result": None,
            "detection": detection_note,
            "effective_params": resolved_params,
        }

        with DataFacade._jobs_lock:
            DataFacade._running_jobs[pipeline_id] = job

        def _run():
            cmd = ["python", pipeline["script"]]
            positional = pipeline.get("cli_positional")
            if positional:
                for key in positional:
                    val = resolved_params.get(key)
                    if val and val != "":
                        cmd.append(str(val))
            else:
                for k, v in resolved_params.items():
                    if v and v != "":
                        k_clean = k.lstrip("-")
                        cmd.extend([f"--{k_clean}", str(v)])

            try:
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, cwd=str(Path(__file__).parent.parent))
                result = {
                    "success": process.returncode == 0,
                    "exit_code": process.returncode,
                    "stdout": process.stdout[-2000:] if process.stdout else "",
                    "stderr": process.stderr[-2000:] if process.stderr else "",
                }
            except subprocess.TimeoutExpired:
                result = {"success": False, "exit_code": -1, "stdout": "", "stderr": "Job timed out after 1 hour"}
            except Exception as e:
                result = {"success": False, "exit_code": -1, "stdout": "", "stderr": str(e)}

            with DataFacade._jobs_lock:
                DataFacade._running_jobs[pipeline_id] = {
                    **job, "status": "completed" if result["success"] else "failed",
                    "result": result,
                    "finished": datetime.now().isoformat(),
                }

        threading.Thread(target=_run, daemon=True).start()
        return job

    def get_job_status(self, pipeline_id: str) -> dict | None:
        return DataFacade._running_jobs.get(pipeline_id)

    # ── Schedule ──────────────────────────────────────────────────────

    def _ensure_schedule_store(self):
        config_path = self._root / "_schedule.duckdb"
        conn = duckdb.connect(str(config_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_jobs (
                id VARCHAR PRIMARY KEY,
                pipeline_id VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                schedule VARCHAR NOT NULL,
                params VARCHAR DEFAULT '{}',
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_run TIMESTAMP,
                next_run TIMESTAMP
            )
        """)
        conn.close()

    def _schedule_conn(self):
        return duckdb.connect(str(self._root / "_schedule.duckdb"))

    def list_scheduled_jobs(self) -> list[dict]:
        conn = self._schedule_conn()
        rows = conn.execute(
            "SELECT id, pipeline_id, name, schedule, params, enabled, created_at, last_run, next_run FROM scheduled_jobs ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return [dict(zip(["id", "pipeline_id", "name", "schedule", "params", "enabled", "created_at", "last_run", "next_run"], [str(v) if v is not None else None for v in row])) for row in rows]

    def create_scheduled_job(self, data: dict) -> dict:
        job_id = str(uuid.uuid4())[:8]
        schedule = data.get("schedule", "0 8 * * 1-5")
        params = data.get("params", {})
        conn = self._schedule_conn()
        conn.execute(
            "INSERT INTO scheduled_jobs (id, pipeline_id, name, schedule, params, enabled) VALUES (?, ?, ?, ?, ?, ?)",
            [job_id, data["pipeline_id"], data["name"], schedule, json.dumps(params), data.get("enabled", True)],
        )
        conn.close()
        return {"id": job_id, "pipeline_id": data["pipeline_id"], "name": data["name"], "schedule": schedule, "params": params, "enabled": data.get("enabled", True)}

    def update_scheduled_job(self, job_id: str, data: dict) -> dict | None:
        conn = self._schedule_conn()
        existing = conn.execute("SELECT id FROM scheduled_jobs WHERE id = ?", [job_id]).fetchone()
        if not existing:
            conn.close()
            return None
        updates = []
        vals = []
        for field in ["name", "schedule", "params", "enabled", "pipeline_id"]:
            if field in data:
                updates.append(f"{field} = ?")
                vals.append(json.dumps(data[field]) if field == "params" else data[field])
        if updates:
            vals.append(job_id)
            conn.execute(f"UPDATE scheduled_jobs SET {', '.join(updates)} WHERE id = ?", vals)
        conn.close()
        return {"id": job_id, **data}

    def delete_scheduled_job(self, job_id: str) -> bool:
        conn = self._schedule_conn()
        conn.execute("DELETE FROM scheduled_jobs WHERE id = ?", [job_id])
        affected = conn.execute("SELECT changes()").fetchone()[0]
        conn.close()
        return affected > 0

    def compute_next_run(self, schedule: str) -> str | None:
        try:
            from croniter import croniter
            return croniter(schedule, datetime.now()).get_next(datetime).isoformat()
        except ImportError:
            return None

    # ── Data Browser ──────────────────────────────────────────────────

    def list_all_tables(self) -> list[dict]:
        tables: list[dict] = []
        for root, _, files in os.walk(self._root):
            for f in files:
                if f.endswith(".duckdb"):
                    full = Path(root) / f
                    store = str(full.relative_to(self._root))
                    try:
                        conn = duckdb.connect(str(full), read_only=True)
                        rows = conn.execute(
                            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
                        ).fetchall()
                        for (tbl,) in rows:
                            try:
                                cnt = conn.execute(f"SELECT COUNT(*) FROM \"{tbl}\"").fetchone()[0]
                            except Exception:
                                cnt = 0
                            tables.append({"name": tbl, "store": store, "row_count": cnt, "store_path": str(full)})
                        conn.close()
                    except Exception:
                        pass
        tables.sort(key=lambda t: t["name"])
        return tables

    def get_table_schema(self, store_path: str, table_name: str) -> dict | None:
        full = Path(store_path)
        if not full.exists():
            return None
        conn = duckdb.connect(str(full), read_only=True)
        try:
            cols = conn.execute(f"DESCRIBE \"{table_name}\"").fetchall()
            schema = [{"name": c[0], "type": c[1], "nullable": c[2] if len(c) > 2 else True} for c in cols]
            try:
                total = conn.execute(f"SELECT COUNT(*) FROM \"{table_name}\"").fetchone()[0]
            except Exception:
                total = 0
            return {"columns": schema, "total_rows": total}
        except Exception as e:
            return {"error": str(e)}
        finally:
            conn.close()

    def browse_table(self, store_path: str, table_name: str, page: int = 1, page_size: int = 50,
                     filters: dict | None = None, order_by: str | None = None,
                     order_dir: str = "ASC") -> dict:
        full = Path(store_path)
        if not full.exists():
            return {"error": "Store not found"}
        conn = duckdb.connect(str(full), read_only=True)
        try:
            where_clauses: list[str] = []
            params: list[Any] = []
            if filters:
                for col, val in filters.items():
                    if val is None or val == "":
                        continue
                    if isinstance(val, dict):
                        if val.get("min") is not None:
                            where_clauses.append(f"\"{col}\" >= ?")
                            params.append(val["min"])
                        if val.get("max") is not None:
                            where_clauses.append(f"\"{col}\" <= ?")
                            params.append(val["max"])
                    else:
                        where_clauses.append(f"\"{col}\"::VARCHAR ILIKE ?")
                        params.append(f"%{val}%")

            where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
            count_sql = f"SELECT COUNT(*) FROM \"{table_name}\"{where_sql}"
            total = conn.execute(count_sql, params).fetchone()[0]

            order_clause = ""
            if order_by:
                order_clause = f" ORDER BY \"{order_by}\" {order_dir}"

            offset = (page - 1) * page_size
            query = f"SELECT * FROM \"{table_name}\"{where_sql}{order_clause} LIMIT ? OFFSET ?"
            cursor = conn.execute(query, params + [page_size, offset])
            cols = [d[0] for d in cursor.description]
            rows = [dict(zip(cols, row)) for row in cursor.fetchall()]

            return {"columns": cols, "rows": rows, "total": total, "page": page, "page_size": page_size}
        except Exception as e:
            return {"error": str(e)}
        finally:
            conn.close()
