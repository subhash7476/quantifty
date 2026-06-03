# Architecture and Data

## Sources

- `docs/CODEBASE_OVERVIEW.md`
- `docs/DATA_PIPELINE.md`
- `docs/BREADTH_INFRASTRUCTURE.md`
- `docs/CLEANUP_AUDIT_REPORT_2026-03-13.md`

## Core conclusions

- The platform works best when market data ingestion is a single-writer path and trading logic is a read-only consumer.
- Historical data belongs in partitioned DuckDB files; operational state belongs in SQLite.
- The live buffer and the historical store should stay separate so live trading does not contaminate backtests.
- The system architecture is intentionally layered: broker adapters, ingest, database, analytics, execution, strategy, UI.
- Causal boundaries matter more than model sophistication. Features must be computed from data available at the decision time only.

## Reusable rules

- Keep ingestion isolated from execution.
- Keep backtest and live code on the same data contract.
- Route all persistence through `DatabaseManager` and the schema layer.
- Partition market data by date and instrument to keep replay fast and auditable.
- Treat operational databases as stateful infrastructure, not strategy storage.

## Common failure modes

- Mixing live cache and historical cache in the same logic path.
- Letting strategy code write market data.
- Using ad hoc data access instead of the database abstraction layer.
- Allowing feature generation to peek at future bars.

