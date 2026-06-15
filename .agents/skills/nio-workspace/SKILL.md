---
name: nio-workspace
description: Navigate and work within the NIO/Mobileum telecom analytics workspace. This skill provides architecture maps, coding patterns, build workflows, and operational checklists for the multi-repo NIO platform. Use this skill whenever working with any of the NIO repositories (nio-analytics, nio-api3, nio-base, nio-python-libs, nio-python3-libs, nio-analytics-c-tools, nio-storage), when dealing with rbuild, autotools, Flask API endpoints, data pipelines, XDR columns, alerts, tracing, or any telecom analytics task in this workspace. Even if the user just mentions a file path starting with /Volumes/vidzdatastore/work/mobileum_source, consult this skill.
---

# NIO Workspace Navigator

This skill helps you work effectively in the NIO/Mobileum telecom analytics platform — a multi-repo C/Python codebase for deep packet inspection, mobile network analytics, and subscriber intelligence.

## Workspace Root

`/Volumes/vidzdatastore/work/mobileum_source`

## Repository Map

| Repository | Language | Purpose |
|---|---|---|
| `nio-analytics` | C + Bash + Python | Core analytics pipelines: ETL scripts, data aggregation tools, cron jobs, ClickHouse/PostgreSQL loaders |
| `nio-analytics-c-tools` | C | Low-level C tools for data processing (preaggregators, cube aggregators) |
| `nio-api3` | Python 3.12 (Flask) | REST API platform — XDR, alerts, tracing, KPIs, external endpoints, dashboards |
| `nio-base` | Python + Config | Shared configs, generated CDL definitions (e.g. `cdl_xanalyzer.json`), libexec scripts |
| `nio-python-libs` | Python 2 | Legacy shared Python libraries (avoid for new code) |
| `nio-python3-libs` | Python 3 | Shared Python 3 libraries: `niolib` with 34+ modules (database, alerts, mailer, CSV, encryption, etc.) |
| `nio-storage` | Python | Storage layer and data persistence utilities |
| `nio-build-deps` | Mixed | Build dependencies and offline tooling |
| `nio-virtualenv-python` | Config | Python virtualenv setup for the platform |
| `rbuild` | Bash | Remote build tool: edit locally on macOS, build on remote Linux server |

## Key Dependency Chain

```
nio-api3 ──depends on──▶ nio-python3-libs (niolib)
nio-api3 ──depends on──▶ nio-base (configs, CDL definitions)
nio-analytics ──depends on──▶ nio-analytics-c-tools (C binaries)
nio-analytics ──uses──▶ nio-python3-libs (niolib for Python ETL scripts)
All C repos ──built via──▶ rbuild + autotools
```

## Build System (`rbuild`)

The workspace uses `rbuild` — an edit-locally-build-remotely workflow. The developer edits on macOS and builds on a remote Linux server via SSH+rsync.

**Quick reference:**
- `rbuild -sb` — Stage source + build (most common, the default)
- `rbuild -sAab` — Full setup: stage + autoreconf + configure + build
- `rbuild -o` — Build with "optimized" environment (`-e optimized`)
- `rbuild -t` — Run `make check` (tests)
- `rbuild -c` — Clean build directory

**Config:** `rbuild.conf` at workspace root defines `BUILD_HOST`, `INSTALL_DIR`, compiler flags, `PKG_CONFIG_PATH`, and build environments (debug vs optimized).

For more details, read `references/build_system.md`.

## Typical Development Workflow (`nio-analytics`)

Use this as the default workflow for routine `nio-analytics` development unless the user asks for a different path:

1. Implement the code change locally in `nio-analytics`.
2. Build from the workspace root:
```bash
cd source_code
./rbuild.sh nio-analytics -saAb
```
3. Run the relevant unit tests after the build. Prefer targeted tests first, then broader coverage when the change is cross-cutting.
4. Create a custom RPM through Jenkins when package-level validation is needed:
   - Job: `https://jbuilder.niometrics.com/job/testing-rocky8/job/nio-analytics/`
   - Action: `Build with Parameters`
   - `changeset`: use either the Git commit SHA (for example `2b21e24a18e90404ceacbf9489247107e7785417`) or the branch name
5. Wait for the Jenkins build to complete successfully before attempting installation.
6. Install the custom RPM on the target test host when requested:
   - Host: `pocket-ath-munp1`
```bash
sudo yum update nio-analytics -y
```
7. Perform manual validation on the target environment after installation. Use the deployed system plus the Jenkins job page to confirm the tested package matches the requested build.

### Workflow Notes

- Treat the `rbuild` step and unit-test step as the default validation gate before requesting a custom RPM.
- If the user asks for package validation, include the Jenkins job URL in the handoff/report.
- If a manual test host is involved, state which host received the RPM and which build or changeset was installed.
- The environment references provided for this workflow are:
  - Jenkins: `jbuilder.niometrics.com`
  - Build job: `https://jbuilder.niometrics.com/job/testing-rocky8/job/nio-analytics/`
  - Test host: `pocket-ath-munp1`
  - Access/contact hints may be team-specific; do not invent credentials or assume access that is not already available.

## API Development (`nio-api3`)

The API is a Python 3.12 Flask service. Every endpoint is a controller class inheriting from `BaseApi`.

**Key patterns:**
- Database: `PgHelper` wraps PostgreSQL — use `sql_query()`, `sql_insert_map()`, `sql_execute()`
- Controllers: inherit `BaseApi`, use `@base_api_decorator` with `NioParam` for Swagger docs
- Routing: add entries to `api_routes` array in `src/nioapi/api/routes.py`
- Responses: `handle_response_json()`, `handle_exception()`

**Running tests:**
```bash
# From the rbuild build directory on the remote server:
./run_tests.sh                                    # all tests
./run_tests.sh -- -p "*<filename>_"               # specific test file
./run_tests.sh -d -- -p "*<filename>_"             # without database
./run_tests.sh -d -c -- -p "*<filename>_"          # without database & component check
TEST_LOGLEVEL=DEBUG ./run_tests.sh ...            # with debug logging
```

**Running the API:**
```bash
./run_api.sh -p <port>
```

For full API patterns (BaseApi, PgHelper, route registration, XDR/PCCT config), read `references/api_patterns.md`.

## Data Pipelines

NIO pipelines follow a **decentralized collection → centralized processing** architecture:

1. **Probes (NCORE/NLIVE)** — Deep Packet Inspection captures raw data
2. **Cubing** — Data reduced/aggregated on-probe
3. **Transport** — `lz4`-compressed files queued via `task -import-broker`
4. **MRS Aggregation** — `nio cube aggregator` merges data from all probes
5. **Correlation** — Pipeline-specific logic (TLS matching in SCV, VOIP signal matching in OTTCall)
6. **Persistence** — `postgres_insert3` bulk loads into PostgreSQL

**Standard intervals:** 30-minute "unit" intervals and daily "day" intervals.

**Key pipeline scripts** live in `nio-analytics/src/libexec/`:
- `etl_runner.sh` / `etl_utils.sh` — ETL framework
- `scp_day.sh` / `scp_week.sh` — SCV pipeline
- `clickhouse_loader.sh` / `clickhouse_cron.sh` — ClickHouse data loading
- `historical.sh` — Historical data reprocessing
- `mrs_fallback_*.sh` — HA failover sync scripts

For full pipeline architecture and core tools, read `references/pipeline_architecture.md`.

## Operational Checklists

These checklists are critical to follow when making certain changes. They're documented in `nio-api3/README.md` but summarized here:

## Logs and Runtime Debugging

Use these first when troubleshooting ETL jobs, scheduled tasks, triggers, or runtime issues on a deployed NIO system:

```bash
# Most logs live here
ls -lah /var/opt/nio/log/

# Main task/scheduler log
tail -f /var/opt/nio/log/task.log

# ETL logs
tail -f /var/opt/nio/log/etl.log

# Performance logs
ls /var/opt/nio/log/perf/

# Syslog entries (for scripts using logger)
journalctl -t nio --since "1 hour ago"

# Triggers service
journalctl -u nio-triggers.service -f
```

### Adding XDR Columns

1. Add column definition to `nio-base/config/generated/cdl_xanalyzer.json`
2. Sync confluence: `nio-build-deps/offline/scripts/cdltool_update_confluence.sh`
3. If column has mapping array → update `build_info_mapping.py` and `pcct_config.py` (procedure/cause patterns)
4. If column is a simple mapped column → add to `config.py` `COLUMNS_MAPPED`

### Supporting New XDR Interface

1. If reusing existing protocol → just add interface to `pcct_config.py`
2. If new protocol → add to `pcct_config.py`, `xdr/build_info_mapping.py`, and `trace/build_info_mapping.py`
3. If new columns with mappings → update `pcct_config.py` and `config.py`
4. [NCORE] Update `/opt/nio/share/trace_mappings.json`

### Adding Alert Dimensions/KPIs

1. Create migration SQL in `nio-analytics`
2. Add to `nio-python-libs/src/niolib/alerts/alerts_mappings.py`
3. Update enumerations

### Adding External Endpoints

1. Define group config in `nio-conf-templates/conf-templates.d/defaults.tmpl`
2. Define endpoint config in same template
3. Add permission in `nio-api-auth/etc/permissions.conf.json`
4. Add to KrakenD config in `nio-api-external.krakend.json.tmpl`

## Shared Library: `niolib` (nio-python3-libs)

Located at `nio-python3-libs/src/niolib/`, this is the core shared Python library used by `nio-api3` and Python-based analytics scripts. Key modules:

| Module | Purpose |
|---|---|
| `database/` | Database helpers, connection management |
| `alerts/` | Alert definitions, mappings, notification logic |
| `clients/` | API clients, ZMQ clients |
| `conf/` | Configuration management |
| `csv/` | CSV reading/writing utilities |
| `data_filters/` | Data filtering and transformation |
| `encryption/` | Encryption utilities |
| `loggers/` | Structured logging |
| `mailer/` | Email notification |
| `time/` | Time utilities, intervals |
| `timeseries/` | Time-series data handling |
| `mergers/` | Data merging logic |

## File Navigation Tips

- **API endpoint code:** `nio-api3/src/nioapi/api/<domain>/` (e.g., `xdr/`, `alerts/`, `trace/`)
- **API routes:** `nio-api3/src/nioapi/api/routes.py` (internal) and `routes_external.py` (external)
- **Shared helpers:** `nio-api3/src/nioapi/api/lib/` (base_api, postgres_config, exceptions, codes)
- **ETL scripts:** `nio-analytics/src/libexec/`
- **Test files:** Each repo has a `tests/` directory; API tests at `nio-api3/tests/`
- **Build configs:** `configure.ac` and `Makefile.am` in each repo root
- **CDL definitions:** `nio-base/config/generated/`
