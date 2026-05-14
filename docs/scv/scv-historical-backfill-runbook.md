# SCV Historical Backfill Runbook

This page is an operator runbook for backfilling a historical SCV date when shard TLS matches are missing and the normal queued task state has already expired.

Use this when:

- one or more `scv_shard` hosts did not send `scv.day_rolling_merged_matches.partial.<host>.<date>.csv`
- the historical date is old enough that the original pending scheduler task no longer exists
- the required retained shard raw files still exist under `scv_matches/<date>/`

This runbook assumes:

- you know the targeflowchart TD
    A[Probe / NCORE\nRaw OTT traffic logs\nWhatsApp, Telegram, FaceTime, etc.] --> B[00_init_ottcall_file.sh\nMake sure raw file exists]
    B --> C[01_create_intermediate_file.sh\nPreaggregate raw log]
    C --> D[02_ottcall.json\nBuild 30-minute cube\nuser, imsi, app, event, duration, volume, match signals]
    D --> E[03_signal_mrs_to_copy.sh\nRename outputs and queue copy to MRS]
    E --> F[04_copy_tasks_backlog.sh\nRetry failed transfers]

    F --> G[MRS receives probe files]
    G --> H[00_imsi.caller.json\nAggregate probe CSVs]
    H --> I[01_app_voip.sh + 01_nssai_app_voip.sh\nInsert usage counters into DB]
    I --> J[02_pre_correlate.sh\nMerge current + previous interval raw logs\nCreate ottcall.log.active]
    J --> K[03_correlate.json\nExtract match_signal_1..8 clues]
    K --> L[04_merge_signals.json\nNormalize clues per app]
    L --> M[05_postprocess_generic_ottcall.sh\nMatch two sides of the same call/chat]

    M --> N[Internal / On-net output\nBoth sides belong to customer network]
    M --> O[External / Off-net output\nOnly one side belongs to customer network]
    O --> P[IP enrichment\nAdd network/country info for outside party]
    N --> Q[06_combine_output_files.sh\nCombine all app outputs]
    P --> Q

    Q --> R[Final 30-minute outputs\nottcall_internal_YYYYMMDD_HHMM.csv\nttcall_external_YYYYMMDD_HHMM.csv]

    R --> S[Day pipeline on MRS]
    S --> T[00_imsi.caller.json\nAggregate all unit files for the day]
    T --> U[Daily DB loaders\napp overall, NSSAI overall, VoIP summaries]
    U --> V[03_ott_rabm.sh + 04_roamers_imsi_rabm.json\nRoaming and monthly summary outputs]

    R -. optional .-> W[mrs_fallback_ottcall_sync.sh\nSync final files to fallback MRS]t date    flowchart LR
        A[Deployment Config Values\nnio.machines, customer settings, feature toggles] --> B[nio-conf-templates\nTemplate Engine]
        B --> C1[ncore config]
        B --> C2[nlive config]
        B --> C3[nio-api config]
        B --> C4[nginx/firewall/other configs]
    
        C1 --> D1[ncore service starts]
        C2 --> D2[nlive service starts]
        C3 --> D3[nio-api service starts]
        C4 --> D4[infra services start]
    
        D1 --> E[Raw traffic logs]
        E --> F[nio-analytics ETL pipelines]
        F --> G[DB/API/UI outputs]        flowchart LR
            A[Deployment Config Values\nnio.machines, customer settings, feature toggles] --> B[nio-conf-templates\nTemplate Engine]
            B --> C1[ncore config]
            B --> C2[nlive config]
            B --> C3[nio-api config]
            B --> C4[nginx/firewall/other configs]
        
            C1 --> D1[ncore service starts]
            C2 --> D2[nlive service starts]
            C3 --> D3[nio-api service starts]
            C4 --> D4[infra services start]
        
            D1 --> E[Raw traffic logs]
            E --> F[nio-analytics ETL pipelines]
            F --> G[DB/API/UI outputs]            flowchart LR
                A[Deployment Config Values\nnio.machines, customer settings, feature toggles] --> B[nio-conf-templates\nTemplate Engine]
                B --> C1[ncore config]
                B --> C2[nlive config]
                B --> C3[nio-api config]
                B --> C4[nginx/firewall/other configs]
            
                C1 --> D1[ncore service starts]
                C2 --> D2[nlive service starts]
                C3 --> D3[nio-api service starts]
                C4 --> D4[infra services start]
            
                D1 --> E[Raw traffic logs]
                E --> F[nio-analytics ETL pipelines]
                F --> G[DB/API/UI outputs]                flowchart LR
                    A[Deployment Config Values\nnio.machines, customer settings, feature toggles] --> B[nio-conf-templates\nTemplate Engine]
                    B --> C1[ncore config]
                    B --> C2[nlive config]
                    B --> C3[nio-api config]
                    B --> C4[nginx/firewall/other configs]
                
                    C1 --> D1[ncore service starts]
                    C2 --> D2[nlive service starts]
                    C3 --> D3[nio-api service starts]
                    C4 --> D4[infra services start]
                
                    D1 --> E[Raw traffic logs]
                    E --> F[nio-analytics ETL pipelines]
                    F --> G[DB/API/UI outputs]                    flowchart LR
                        A[Deployment Config Values\nnio.machines, customer settings, feature toggles] --> B[nio-conf-templates\nTemplate Engine]
                        B --> C1[ncore config]
                        B --> C2[nlive config]
                        B --> C3[nio-api config]
                        B --> C4[nginx/firewall/other configs]
                    
                        C1 --> D1[ncore service starts]
                        C2 --> D2[nlive service starts]
                        C3 --> D3[nio-api service starts]
                        C4 --> D4[infra services start]
                    
                        D1 --> E[Raw traffic logs]
                        E --> F[nio-analytics ETL pipelines]
                        F --> G[DB/API/UI outputs]
- you know which shard hosts were missing
- `scv_master` already has some shard partials for that date
- you want a scheduler-aware rerun path whenever possible

## Fast Path

Use this section when you already know the SCV flow and only need the minimum recovery steps.

1. On each missing shard host, verify `/var/opt/nio/aggregations/scv_matches/<date>/` still contains the retained `scv.unit_merged_matches_raw.*.csv` files.
2. Protect those files from retention cleanup with `find ... -exec touch {} +`.
3. Rerun only the missing shard host(s), preferably with `task -import` and `count = 0`, or use `task -reload-task <id>` if the failed historical unit task already exists in audit.
4. On `scv_master`, confirm all `scv.day_rolling_merged_matches.partial.*.<date>.csv` files are now present.
5. Find the fresh historical `matches_scv_master` waiting task. If it shows `2/5`, bump it 3 times to account for the 3 shard partials that already existed on master.
6. After `matches_scv_master` completes, check the final historical `scv` task. If it is still waiting, bump it 2 more times for historical `userkey_scv_master` and `subintel_scv_master`.
7. Verify the rerun in `task -pretty-list-audit`, `scv_master_day.log`, and regenerated `/var/opt/nio/feeds/scv/home_analytics.<date>.log` outputs.

Fast reminders:

- old historical waiting tasks are expected to expire from the active queue
- retained files can still exist even when the old queue state is gone
- `count = 0` creates a runnable task now
- `task -bump <id>` adds `+1` toward the threshold of a waiting task

## Core Idea

For a historical date, the original queued `3/5` or similar waiting task is expected to be gone already.

What must still exist instead is:

- the shard raw EOD inputs on the missing shard host(s)
- the already-produced shard partial output files on `scv_master`

When you rerun only the missing shard hosts, the scheduler creates a fresh pending task for that old date using only the newly arrived shard bumps. If `scv_master` already has other shard partial files physically present for that date, you must manually `task -bump` the fresh pending task to account for those already-present files.

## Scheduler Counter Semantics

### What `count` means in `task -import`

The scheduler treats `count` as follows:

- `count = 0`: create a new queued task and make it immediately runnable
- `count > 0`: bump the count of the matching task by that amount, or create it with that count if it does not exist yet

So yes:

- `count = 1` is equivalent to one bump
- `count = 2` is equivalent to two bumps
- `count = 3` is equivalent to three bumps

Practical meaning:

- use `count = 0` when you want to queue a task to run now
- use `task -bump <id>` or a nonzero `count` import when you want to advance a waiting counter toward its threshold

### How queued task status looks

Illustrative `task -pretty-list` output for an immediate runnable task:

```text
ID     ACTION  SOURCE         INTERVAL START      INTERVAL  CREATED           CNT   STATUS  PID  CONFLICT                  ARG   ROLE
118999 cubes   tls_scv_shard  2026-04-27 23:30   unit      2026-05-04 10:12  0/0   Ready        cubes:tls_scv_shard:unit unit  scv_shard
```

Illustrative output for a waiting historical fan-in task:

```text
ID     ACTION  SOURCE              INTERVAL START    INTERVAL  CREATED           CNT   STATUS              PID  CONFLICT            ARG   ROLE
119010 cubes   matches_scv_master  2026-04-27 00:00 day       2026-05-04 10:35  2/5   Waiting (09:54:12)      matches_scv_master day  scv_master
```

In this example, the task has only seen the two newly rerun shard bumps so far.

## Before You Start

Collect these facts first:

- target historical date, for example `2026-04-27`
- missing shard hosts, for example `bcpmrshabrnpapp2` and `bcpmrshabrnpapp3`
- `scv_master` hostname, for example `bcpmrshabrnpapp1`

Check retention before promising a rerun.

If the shard raw files for that date are gone, this runbook will not work.

## Step 1. Verify shard raw EOD inputs still exist

Run on each missing `scv_shard` host:

```bash
sudo -iu nio
ls -lahtr /var/opt/nio/aggregations/scv_matches/2026-04-27 | tail -10
```

Illustrative output:

```text
-rw-r--r-- 1 nio nio  76M Apr 29 21:14 scv.unit_merged_matches_raw.2026-04-27-23-30.csv
-rw-r--r-- 1 nio nio 136M Apr 29 21:14 scv.unit_merged_matches_raw.2026-04-27-23-00.csv
-rw-r--r-- 1 nio nio 144M Apr 29 21:14 scv.unit_merged_matches_raw.2026-04-27-22-30.csv
```

If the files are missing, stop here and reassess the recovery path.

## Step 2. Protect retained files from retention cleanup

Run on each missing shard host:

```bash
sudo -iu nio
find /var/opt/nio/aggregations/scv_matches/2026-04-27 -maxdepth 1 -name 'scv.unit_merged_matches_raw.2026-04-27-*.csv' -exec touch {} +
```

Use `find ... -exec touch` instead of a raw shell glob to avoid creating literal `*` files when the glob does not expand.

## Step 3. Choose the rerun method

There are three supported styles.

### Option A. Run ETL directly

This is the quickest operational path, but it bypasses scheduler conflicts, queueing, and post-bump behavior.

```bash
sudo -iu nio
cd /opt/nio/share/etl
/opt/nio/libexec/etl_runner.sh \
  --interval unit \
  --source tls_scv_shard \
  --timestamp $(date -d '2026-04-27 23:30:00' +%s) \
  --role scv_shard
```

Use this when speed matters more than scheduler visibility.

### Option B. Submit a task to the scheduler

This is the scheduler-aware path.

```bash
sudo -iu nio task -import '{
  "action":"cubes",
  "source":"tls_scv_shard",
  "interval":"unit",
  "arg":"unit",
  "role":"scv_shard",
  "timestamp":"2026-04-27T23:30:00",
  "count":0,
  "conflict":"cubes:tls_scv_shard:unit"
}'
```

What the key fields mean:

- `action = cubes`: queue a cube ETL task
- `source = tls_scv_shard`: run the SCV shard TLS source
- `interval = unit`: run the 30-minute unit logic
- `arg = unit`: pass the expected argument into the ETL layer
- `role = scv_shard`: run it on the shard role
- `timestamp = 2026-04-27T23:30:00`: historical unit to process
- `count = 0`: create a runnable task immediately
- `conflict = cubes:tls_scv_shard:unit`: prevent conflicting queued work of the same type

Use this when you want the rerun to be visible in the scheduler queue and audit surfaces.

### Option C. Reload a failed historical task

Use this when the exact failed historical task already exists in scheduler audit history.

First find it:

```bash
sudo -iu nio task -pretty-list-audit '{"source":"tls_scv_shard","interval":"unit","status":"failed"}'
```

Or narrow to the exact timestamp:

```bash
sudo -iu nio task -pretty-list-audit '{"source":"tls_scv_shard","interval":"unit","status":"failed","timestamp":"2026-04-27T23:30:00"}'
```

Illustrative output:

```text
ID      UUID                                  ACTION SOURCE         TIMESTAMP            STATUS ROLE
118700  7c1c0b56-....-....-....-............  cubes  tls_scv_shard  2026-04-27 23:30     failed scv_shard
```

Then rerun it:

```bash
sudo -iu nio task -reload-task 118700
```

Use this when you want to replay an actual failed task instead of creating a fresh one.

## Step 4. Observe a scheduler-submitted rerun

`task -import` queues work, but it does not stream the ETL logs into your shell.

To observe the task, use these views in parallel.

### A. Watch queued and running tasks

```bash
sudo -iu nio task -pretty-list
```

Look for:

- `SOURCE = tls_scv_shard`
- `INTERVAL START = 2026-04-27 23:30`
- `STATUS = Ready` or `Running (...)`

Illustrative line:

```text
118999 | cubes | tls_scv_shard | 2026-04-27 23:30 | unit | 2026-05-04 10:12 | 0/0 | Ready | | cubes:tls_scv_shard:unit | unit | scv_shard
```

### B. Watch task scheduler events

```bash
sudo tail -F /var/opt/nio/log/task.log | grep --line-buffered -E 'tls_scv_shard|2026-04-27T23:30:00|2026-04-27 23:30'
```

Illustrative lines:

```text
[2026-05-04 10:12:11] INFO ... Creating a new task: {"action":"cubes","source":"tls_scv_shard",...,"timestamp":"2026-04-27T23:30:00"}
[2026-05-04 10:12:43] INFO ... Running task: {"action":"cubes","source":"tls_scv_shard",...}
[2026-05-04 10:25:03] INFO ... Successfully ran task: {"action":"cubes","source":"tls_scv_shard",...}
```

### C. Watch SCV shard ETL behavior

```bash
sudo tail -F /var/opt/nio/log/scv_shard_unit.log | grep --line-buffered '2026-04-27-23-30'
```

Illustrative lines:

```text
msgtype=INFO interval=2026-04-27-23-30 script=01_schedule_day_tls_scv_shard.sh ...
msgtype=INFO ... operation=ScvShard.day_filter interval=2026-04-27 num_of_invalid_tls_keys=12345
msgtype=PERF ... operation=ScvShard.day_filter interval=2026-04-27 ...
```

### D. Check audit after completion

```bash
sudo -iu nio task -pretty-list-audit '{"source":"tls_scv_shard","interval":"unit","timestamp":"2026-04-27T23:30:00"}'
```

Illustrative result:

```text
118999 | ... | cubes | tls_scv_shard | 2026-04-27 23:30 | success | scv_shard
```

If the event is old enough to rotate out, use the rotated logs too.

## Step 5. Confirm missing shard outputs are now present on `scv_master`

On `scv_master`:

```bash
sudo -iu nio
ls -lah /var/opt/nio/aggregations/scv/2026-04-27/scv.day_rolling_merged_matches.partial.*.2026-04-27.csv
```

Illustrative output:

```text
-rw-r--r-- 1 nio nio 1.4G Apr 28 01:24 scv.day_rolling_merged_matches.partial.bcpmrshabrnpapp1.2026-04-27.csv
-rw-r--r-- 1 nio nio 1.4G May  4 10:28 scv.day_rolling_merged_matches.partial.bcpmrshabrnpapp2.2026-04-27.csv
-rw-r--r-- 1 nio nio 1.3G May  4 10:29 scv.day_rolling_merged_matches.partial.bcpmrshabrnpapp3.2026-04-27.csv
-rw-r--r-- 1 nio nio 1.4G Apr 28 01:24 scv.day_rolling_merged_matches.partial.bcpmrshabrnpapp4.2026-04-27.csv
-rw-r--r-- 1 nio nio 1.3G Apr 28 01:25 scv.day_rolling_merged_matches.partial.bcpmrshabrnpapp5.2026-04-27.csv
```

## Step 6. Locate the fresh historical `matches_scv_master` task

The old queued `3/5` task for that date is expected to be gone.

After rerunning only the missing 2 shards, you should see a fresh pending task that reflects only those 2 newly arrived shard bumps.

Check the queue:

```bash
sudo -iu nio task -pretty-list
```

Illustrative line:

```text
119010 | cubes | matches_scv_master | 2026-04-27 00:00 | day | 2026-05-04 10:35 | 2/5 | Waiting (09:54:12) | | matches_scv_master | day | scv_master
```

This does not mean the other 3 shard outputs are missing. It means the new pending task only knows about the 2 new rerun arrivals so far.

## Step 7. Manually bump the waiting `matches_scv_master` task

If `scv_master` already has the other 3 shard partial files physically present for that date, bump the pending task 3 times.

```bash
sudo -iu nio task -bump 119010
sudo -iu nio task -bump 119010
sudo -iu nio task -bump 119010
```

Meaning:

- each `task -bump <id>` adds `+1` to the pending task count
- you are accounting for the 3 historical shard outputs that already existed on the master

Illustrative progression:

```text
before: 119010 | ... | 2/5 | Waiting ...
after 1: 119010 | ... | 3/5 | Waiting ...
after 2: 119010 | ... | 4/5 | Waiting ...
after 3: 119010 | ... | 5/5 | Ready
```

## Step 8. Remember that final `scv` still needs `+2`

Even after `matches_scv_master` completes, final `scv` may still need the equivalent historical contributions of:

- `userkey_scv_master +1`
- `subintel_scv_master +1`

That means the final day `scv` task for that historical date may need 2 more manual bumps.

Check the queue:

```bash
sudo -iu nio task -pretty-list
```

Illustrative line:

```text
119020 | cubes | scv | 2026-04-27 00:00 | day | 2026-05-04 10:41 | 1/3 | Waiting (09:58:00) | | scv_master | day | scv_master
```

Then bump it twice:

```bash
sudo -iu nio task -bump 119020
sudo -iu nio task -bump 119020
```

This represents the historical `userkey_scv_master` and `subintel_scv_master` contributions for that date.

## Step 9. Verify final `scv` reran and overwrote outputs

Watch audit:

```bash
sudo -iu nio task -pretty-list-audit '{"source":"scv","interval":"day","timestamp":"2026-04-27T00:00:00"}'
```

Watch the master log:

```bash
sudo tail -F /var/opt/nio/log/scv_master_day.log | grep --line-buffered 'interval=2026-04-27'
```

Check the regenerated day outputs:

```bash
ls -lah /var/opt/nio/feeds/scv/home_analytics.2026-04-27.log
ls -lah /var/opt/nio/feeds/scv/home_analytics_distributions.2026-04-27.log
```

Illustrative output:

```text
-rw-r--r-- 1 nio nio 2.1G May  4 10:58 /var/opt/nio/feeds/scv/home_analytics.2026-04-27.log
-rw-r--r-- 1 nio nio 180M May  4 10:58 /var/opt/nio/feeds/scv/home_analytics_distributions.2026-04-27.log
```

These files are fully regenerated for that date. They are not append-only fragments.

## Quick Decision Guide

Use this summary during incidents:

- Need the fastest rerun: use direct `etl_runner.sh`
- Need scheduler visibility: use `task -import` with `count = 0`
- A failed historical audit task already exists: use `task -reload-task <audit_id>`
- Fresh historical `matches_scv_master` shows `2/5`: bump it 3 times if the other 3 shard files already exist on master
- Final `scv` still waiting after matches finishes: bump it 2 more times for historical `userkey_scv_master` and `subintel_scv_master`

## Common Operator Mistakes

- assuming the old historical waiting task should still exist
- rerunning all shard hosts instead of only the missing ones
- forgetting to protect retained `scv_matches` files from retention
- using unsafe wildcard `touch` commands that create literal `*` files
- expecting `task -import` to stream task logs directly in the current shell
- forgetting that final `scv` may still need `+2` even after `matches_scv_master` is repaired
