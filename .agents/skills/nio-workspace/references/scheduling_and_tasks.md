# NIO Task Scheduling & Execution Model

## Overview

NIO uses a distributed, queue-driven scheduling model. Each machine runs its own local scheduler — there is no central orchestrator. Linux cron triggers scheduler commands, which load tasks into a local queue, and a separate executor processes them.

## Cron Triggers

Cron templates (installed via RPM) define these commands:

| Command | Frequency | Purpose |
|---|---|---|
| `task -1m` | Every minute | Load 1-minute interval tasks into queue |
| `task -unit` | Every 30 minutes | Load unit (30-minute) interval tasks into queue |
| `task -daily` | Once per day | Load daily interval tasks into queue |
| `task -run` | Every minute | Execute queued tasks (all interval types) |

**Key distinction**: `-1m`, `-unit`, `-daily` are *interval loaders* that enqueue work. `-run` is the *executor* that processes all queued tasks regardless of their interval.

## Task Definitions

Task definitions live in JSON config files:

- `etc/tasks.conf.ncore.json` — NCORE role tasks
- `etc/tasks.conf.nlive.json` — NLIVE role tasks
- `etc/tasks.conf.mrs.json` — MRS role tasks (if exists)

**Important**: These config files are present on ALL machines. The scheduler filters by the machine's assigned role at runtime.

### Task Config Fields

```json
{
  "Source": "ottcall",
  "Action": "cubes",
  "Conflict": "cubespreaggregate",
  "Interval": "unit",
  "Arg": "unit",
  "Role": "ncore",
  "_check": "config:ottcall.enabled"
}
```

| Field | Meaning |
|---|---|
| Source | Logical pipeline/input type (e.g., `ottcall`, `tls`, `dns`) |
| Action | Work type: `cubes` runs the ETL folder, others may exist |
| Conflict | Prevents concurrent execution of conflicting tasks |
| Interval | Time bucket: `1m`, `5m`, `unit` (30m), `hour`, `daily` |
| Arg | Argument passed to the task |
| Role | Which machine role should run this task |
| _check | Conditional enable flag — task only loads if config condition is true |

## Machine Roles

Machine roles are NOT determined by which task config files exist. They are set by ops configuration:

```
nio.machines.*.is_ncore=true
nio.machines.*.is_nlive=true
nio.machines.*.is_mrs=true
```

A machine can have multiple roles. If so, one scheduler loads and runs tasks for all its roles.

## Queue Model

Each machine maintains a local task queue:

1. Cron runs a scheduler command (e.g., `task -unit`)
2. Scheduler checks machine roles + task configs
3. Matching tasks are placed in the local queue
4. `task -run` takes tasks from queue and executes them

## Pipeline Execution (action=cubes)

When a task has `Action: cubes`, it runs the ETL folder:

```
resources/etl/<ROLE>/cubes/<INTERVAL>/<SOURCE>/
```

Steps run in filename order. The folder contains:
- Shell scripts (`.sh`) — preprocessing, checks, signaling
- JSON files (`.json`) — cube aggregation definitions

The cube engine binary comes from the `nio-cubes` RPM package (a dependency of `nio-analytics`).

### Example: ottcall unit on ncore

```
resources/etl/ncore/cubes/unit/ottcall/
  00_init_ottcall_file.sh          # Init, file checks
  01_create_intermediate_file.sh   # Preprocessing
  02_ottcall.json                  # Cube aggregation
  03_signal_mrs_to_copy.sh         # Signal MRS
  04_copy_tasks_backlog.sh         # Retry missed copies
```

## Cross-Machine Coordination

### Data Movement Patterns

- **ncore → nlive**: In-memory events (near real-time), NOT file transfers
- **ncore → MRS**: Files grouped by schema + time window, copied via task queue
- **nlive → MRS**: Processed outputs, copied similarly

### Signal Flow

1. **ncore/nlive** completes processing → adds "file ready to copy" task to MRS queue
2. **MRS** receives/copies the file → queues its own `cubes` task
3. For multi-ncore sources, **MRS waits** until all N upstream files for the same (source, interval, timestamp) arrive
4. MRS maintains a counter and only marks the cubes task as ready when all inputs are present

### Polling for Delayed Files

`notify_mrs_polling.sh` periodically checks for files that appeared after the initial scheduled task ran. This handles cases where source files are produced slightly late due to postprocessing.

## End-to-End Lifecycle Example

For `ottcall unit` on a multi-machine setup:

1. Cron runs `task -unit` on ncore
2. Scheduler loads `ottcall` ncore task into local queue
3. Cron runs `task -run` on ncore
4. Ncore executes `resources/etl/ncore/cubes/unit/ottcall/`
5. Step `03_signal_mrs_to_copy.sh` adds "copy ready" task to MRS queue
6. MRS copies the file from ncore
7. MRS queues its own cubes task
8. After all N ncore files arrive, MRS runs `resources/etl/mrs/cubes/unit/ottcall/`
9. MRS performs final aggregation across all probes

## Development Workflow

### Standard Process

1. Implement feature locally
2. Add tests (unit/functional for Python, make check for C/shell)
3. Build and validate via `rbuild` (fast feedback loop)
4. Build pre-merge RPM from PR branch via Jenkins
5. Install RPM on pocket (test host) and test in production-like environment
6. Merge PR
7. Build official RPM from master
8. Deploy and verify again

### Manual Pipeline Testing

```bash
sudo su nio
cd /opt/nio/share/etl
/opt/nio/libexec/etl_runner.sh --interval unit --source ottcall --timestamp $(date -d '2026-02-03 14:30:00' +%s) --role ncore
```

**Important**: Choose a timestamp for which source files actually exist. Current time may not have data yet — use the last 30-minute boundary or previous hour.

### Observing Results

- **Logs**: `/var/opt/nio/log/etl_cubes.<source>.<interval>.<role>`
- **Downstream**: After running ncore manually, the pipeline can auto-trigger MRS; check MRS logs
- **Natural observation**: Watch at round times (XX:00, XX:30) to see scheduler-triggered runs

### Testing Types

| Scope | Method |
|---|---|
| Single cube aggregation | Run the .json file directly with sample input |
| Full pipeline (multi-step) | Pre-merge RPM on pocket, end-to-end |
| Multi-machine pipeline | Start from producer role (ncore), observe MRS |
| All-in-one machine | Starting role matters less, but follow full sequence |
