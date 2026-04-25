# NIO Data Pipeline Architecture

## High-Level Flow

All NIO analytics pipelines (SCV, OTTCall, app usage, etc.) follow the same pattern:

```
Probes (NCORE/NLIVE) → Cubing → Transport → MRS Aggregation → Correlation → PostgreSQL
```

### Stage 1: Detection & Capture (Probes)

- **NCORE**: Mobile network probes — Deep Packet Inspection on mobile traffic
- **NLIVE**: Fixed network probes — captures fixed-line traffic
- Probes run a `preaggregator` binary that structures raw syslog/DPI output

### Stage 2: Local Aggregation (Cubing)

- `nio cube aggregator` reduces raw data on-probe before transfer
- Dimensions: user, imsi, location, app, timestamp, etc.
- Summaries: sum, max, unique_users, etc.

### Stage 3: Transport

- Files compressed with `lz4` for bandwidth efficiency
- `add_remote_copy_task` (from `etl_utils.sh`) queues files for transfer
- `task -import-broker` fetches files from probes to MRS

### Stage 4: Central Aggregation (MRS)

- MRS = Multi-Role Server — central processing node
- Aggregates cubes from all probes into a global view
- `nio cube aggregator` or `db_aggregation_tool3` used for merging

### Stage 5: Pipeline-Specific Correlation

- **SCV (Single Customer View):** Matches TLS session keys between mobile and fixed users
- **OTTCall:** Matches VOIP signals (SSRC, XOR-MAPPED-ADDRESS) to detect OTT calls
- **App Usage:** Aggregates per-app traffic metrics

### Stage 6: Persistence

- `postgres_insert3` bulk loads CSV data into PostgreSQL
- Supports `--delete_old` for idempotent reloads
- `nio_psql_analytics` wraps psql for ad-hoc SQL

## Standard Intervals

| Interval | Duration | Used For |
|---|---|---|
| Unit | 30 minutes | Near-real-time capture, preliminary aggregation |
| Day | 24 hours | Unique subscriber counts, daily totals, maintenance |
| Week | 7 days | Weekly aggregations (e.g., `scp_week.sh`) |

## Core Tools

### Aggregation & Transformation
- **`preaggregator`** — Per-probe binary, transforms raw logs into structured format
- **`nio cube aggregator`** — Primary engine for multi-dimensional data summarization
- **`db_aggregation_tool3`** — Aggregates unit records into daily/monthly totals

### Persistence
- **`postgres_insert3`** — Bulk CSV → PostgreSQL loader with timestamp/column mapping
- **`nio_psql_analytics`** — Wrapper around `psql` for the analytics database

### Transport
- **`add_remote_copy_task`** — Shell function (sourced from `etl_utils.sh`) to queue file transfers
- **`task -import-broker`** — Triggers file fetch from remote probe
- **`lz4`** — Standard compression for data transfer

### High Availability
- **`mrs_fallback_sync`** — Primary/secondary MRS sync via scp/ssh
- **Backlog retry** — `*_backlog.sh` scripts scan for `.failed` symlinks and retry

## Key ETL Scripts (`nio-analytics/src/libexec/`)

| Script | Purpose |
|---|---|
| `etl_runner.sh` | Main ETL execution framework |
| `etl_utils.sh` | Shared ETL utilities and functions |
| `scp_day.sh` | SCV daily pipeline |
| `scp_week.sh` | SCV weekly pipeline |
| `clickhouse_loader.sh` | ClickHouse data loading |
| `clickhouse_cron.sh` | ClickHouse scheduled jobs |
| `historical.sh` | Historical data reprocessing |
| `load_feeds_daily.sh` | Daily feed loading (23KB — complex) |
| `load_feeds_weekly.sh` | Weekly feed loading |
| `alerts_checker.sh` | Alert condition evaluation |
| `events_cron.sh` | Event processing cron |
| `mrs_fallback_*.sh` | HA failover scripts |
| `pg_upgrade_db.sh` | PostgreSQL upgrade utility |
| `db_expire_partitions.sh` | Table partition expiry |
| `notify_mrs_polling.sh` | MRS polling notifications |

## Python Pipeline Code

Python-based analytics code lives in `nio-analytics/py3/src/`:
- Uses `niolib` from `nio-python3-libs` for database, config, and utility functions
- Has its own `configure.ac` / `Makefile.am` / `setup.py.in` for autotools integration
- Tests in `nio-analytics/py3/tests/`

## File Naming Conventions

Pipeline data files typically follow patterns like:
- `<pipeline>_<interval>_<timestamp>.csv.lz4` for compressed data
- `.failed` symlinks mark failed transfers for backlog retry
- `.done` markers indicate completed processing
