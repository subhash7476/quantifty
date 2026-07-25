# Data Manager — Frontend Architecture

**Created:** 2026-07-24  
**Blueprint:** `data` (URL prefix `/data`)  
**Status:** Active  

---

## File Inventory

| File | Role |
|------|------|
| `app_facade/data_facade.py` | Facade — bridge between Flask and core data infrastructure |
| `flask_app/blueprints/data/__init__.py` | Blueprint definition |
| `flask_app/blueprints/data/routes.py` | All API endpoints (20 routes) |
| `flask_app/templates/data/index.html` | Full-page template (6 tabs) |
| `flask_app/__init__.py` | Blueprint registration |
| `flask_app/templates/base.html` | Sidebar navigation — "Data" link added |

---

## Architecture

```
Flask UI (templates/data/index.html)
    ↓ fetch()
Data Blueprint (flask_app/blueprints/data/routes.py)
    ↓ Facade
DataFacade (app_facade/data_facade.py)
    ↓ duckdb / subprocess
DuckDB stores + ingestion scripts
```

The template is a single-page application within Flask. All interactions use `fetch()` against the blueprint's JSON API endpoints. No page reloads.

---

## Tab Breakdown

### 1. Overview
Dashboard of all data stores. Shows every DuckDB file under `data/` with its name, description, row count, table count, file size, and last-modified timestamp. Directory-type stores (1m candles, 1d candles) show file count instead of row count.

**Endpoint:** `GET /data/api/overview`

### 2. Explorer
Universal table browser across all DuckDB stores. Left sidebar lists every table grouped by store (with row counts). Click a table to load its schema and browse data with column-level text filters and pagination.

**Endpoints:**  
- `GET /data/api/tables` — list all tables across all stores  
- `POST /data/api/schema` — get column metadata for a table  
- `POST /data/api/browse` — paginated data with filters  

### 3. Query
SQL console. Left sidebar lists all `.duckdb` files as selectable stores. Text editor with monospace font for SQL input. Supports SELECT, DESCRIBE, SHOW, PRAGMA (read-only), and DDL/DML (write). Results rendered as a table. Query history saved to localStorage with recall.

**Endpoints:**  
- `GET /data/api/stores` — list queryable DuckDB files  
- `POST /data/api/sql` — execute SQL, returns columns + rows  

### 4. Ingestion
Pipeline runner. 10 ingestion pipelines pre-registered. Each card shows name, description, script path, status, and a Run button. Running pipelines show a pulsing border. Failed pipelines show stderr output. Status auto-polls every 5 seconds when tab is active.

**Pre-registered pipelines:**
| ID | Script |
|----|--------|
| `equity_bhavcopy` | `scripts/csmp/ingest_equity_bhavcopy.py` |
| `corporate_actions` | `scripts/csmp/ingest_corporate_actions.py` |
| `index_history` | `scripts/ingest_index_history.py` |
| `futures_bhavcopy` | `scripts/sfb/ingest_futures_bhavcopy_v2.py` |
| `stock_options` | `scripts/sfb/ingest_stock_options_bhavcopy.py` |
| `instrument_master` | `scripts/fetch_instrument_master.py` |
| `intermarket_data` | `scripts/fetch_intermarket_data.py` |
| `universe` | `scripts/csmp/build_universe.py` |
| `continuous_futures` | `scripts/sfb/build_continuous_futures.py` |
| `sector` | `scripts/g2_ingest_sector_classification.py` |

**Endpoints:**  
- `GET /data/api/ingestion/pipelines` — list pipelines with status  
- `POST /data/api/ingestion/run` — trigger a pipeline  
- `GET /data/api/ingestion/status/<id>` — job status  

### 5. Downloads
Manual Upstox historical candle download. Date range with quick presets (1M–2Y), interval selector, worker count. Watchlist of symbols with search-add and Nifty 50 bulk-load button. Batch-download dispatches one background subprocess per symbol.

**Endpoints:**  
- `POST /data/api/download/historical` — dispatch download  
- `GET /data/api/nifty50-symbols` — resolved Nifty 50 instrument keys  
- `GET /data/api/historical-dates` — available candle dates  
- `GET /data/api/historical-symbols/<date>` — symbols for a date  
- `POST /data/api/historical-data` — query candle data  

### 6. Schedule
Scheduled job manager. CRUD interface for cron-triggered ingestion jobs. Each job links a pipeline to a standard 5-field cron expression (min hour day month weekday). Stored in `data/_schedule.duckdb`. Enable/disable toggle per job.

**Endpoints:**  
- `GET /data/api/schedule` — list all jobs  
- `POST /data/api/schedule` — create job  
- `PUT /data/api/schedule/<id>` — update job  
- `DELETE /data/api/schedule/<id>` — delete job  

---

## Adding a New Pipeline

Add an entry to `DataFacade.PIPELINES` in `app_facade/data_facade.py`:

```python
{
    "id": "my_pipeline",
    "name": "My Pipeline",
    "description": "What it ingests",
    "script": "scripts/my_ingest.py",
    "category": "market_data",   # or "reference", "derived"
    "params": [],                 # optional: [{name, label, type, default}]
},
```

It auto-appears in both the Ingestion and Schedule tabs.

## Adding a New Tab

1. Add the tab button in the tab navigation section of `templates/data/index.html`
2. Add the tab content `<div id="tab-content-{name}">`  
3. Add methods to the `DataUI` JavaScript object
4. Wire `switchTab()` to load the tab's data on activation

## JavaScript Conventions

- All UI state lives in `DataUI._state`
- All methods prefixed with underscore are internal; those without are event handlers
- `DataUI._esc(s)` escapes strings for HTML insertion
- Query history uses `localStorage` key `data_query_history`
- Ingestion status auto-polls only when the ingestion tab is active

## Styling Conventions

- Tailwind CDN — no build step
- Font Awesome 6 CDN for icons
- Inter font from Google Fonts
- `glass` class defined in `base.html` for card backgrounds
- Dark theme: `bg-[#0f172a]` body, `bg-[#1e293b]` sidebar
- Result tables: `text-[11px]` with `result-cell` class for overflow truncation

## Existing Database Section

The old `/database` section is preserved at its original URL. The sidebar shows:
- **Data** — new comprehensive data manager (`/data/`)  
- **DB Admin** — legacy database explorer (`/database/`)

The old section can be retired once the new one covers all its use cases.
