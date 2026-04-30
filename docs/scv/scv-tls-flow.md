# SCV TLS Flow

This page explains the deployed SCV flow from shard unit matching to master reporting.

## High-Level Path

1. Shard unit flow matches TLS keys and writes raw unit matches.
2. The shard 23:30 unit run normalizes the day's raw files into day outputs.
3. The shard day flow creates rolling partials and transition partials.
4. The shard copies those partials to scv_master.
5. The master aggregates shard partials, waits for the `3/3` gate, and runs the core SCV day flow.
6. If reporting is enabled, the master also builds domain, raw matches, and scope reports.

## Shard Unit Flow

### `scv_shard/unit/tls_scv_shard/00_tls_match_session_keys.sh`

Purpose:
Match mobile and fixed TLS session keys for the current unit and produce raw per-unit match files.

Main inputs:

- `/var/opt/nio/aggregations/scv_matches/YYYY-MM-DD/scv.tls.ctk.YYYY-MM-DD-HH-MM.<probe>.mobile.csv`
- `/var/opt/nio/aggregations/scv_matches/YYYY-MM-DD/scv.tls.stk.YYYY-MM-DD-HH-MM.<probe>.fixed.csv`
- `/var/opt/nio/aggregations/scv_matches/YYYY-MM-DD/scv.tls.cid.YYYY-MM-DD-HH-MM.<probe>.mobile.csv`
- `/var/opt/nio/aggregations/scv_matches/YYYY-MM-DD/scv.tls.sid.YYYY-MM-DD-HH-MM.<probe>.fixed.csv`
- `/etc/opt/nio/analytics.json`

Important config gates:

- `.is_scv_shard`
- `.scv.enabled`
- `.scv.config.distance_filtering`
- `.scv.config.blacklist_location.enabled`
- `.scv.config.blacklist_time.enabled`
- `.scv.config.matcher_look_back_units`

Main output:

- `/var/opt/nio/aggregations/scv_matches/YYYY-MM-DD/scv.unit_merged_matches_raw.YYYY-MM-DD-HH-MM.csv`

Why it matters:
This is the retained shard-side raw material needed by the end-of-day normalization. If these files are gone due to retention, the same-day rerun options become narrower.

### `scv_shard/unit/tls_scv_shard/01_schedule_day_tls_scv_shard.sh`

Purpose:
At `23:30`, convert the raw unit files of the day into the narrow day file used by the shard day cubes, and optionally generate reporting inputs.

Behavior:

- Runs only for the `23:30` unit.
- Normalizes all `scv.unit_merged_matches_raw.YYYY-MM-DD-??-??.csv` files into one day-level temporary raw file.
- Computes invalid TLS keys by calling `scv_domain_report --write-invalid-keys`.
- Writes the narrow day file used by the shard day cubes.
- If reporting is enabled, also writes the raw day matches and a domain report partial.
- Schedules the shard day cubes with `task -import` for source `tls_scv_shard`.

Main inputs:

- `/var/opt/nio/aggregations/scv_matches/YYYY-MM-DD/scv.unit_merged_matches_raw.YYYY-MM-DD-??-??.csv`
- legacy fallback files: `/var/opt/nio/aggregations/scv_matches/YYYY-MM-DD/scv.unit_merged_matches.YYYY-MM-DD-??-??.csv`

Main outputs:

- `/var/opt/nio/feeds/scv/scv.day_merged_matches.YYYY-MM-DD.csv`
- `/var/opt/nio/feeds/scv/scv.invalid_tls_keys.day.YYYY-MM-DD.csv`
- `/var/opt/nio/feeds/scv/scv.day_merged_matches_raw.YYYY-MM-DD.csv` when reporting is enabled
- `/var/opt/nio/feeds/scv/scv.domain_report.partial.YYYY-MM-DD.csv` when reporting is enabled and the domain-report step succeeds

Important operational note:
This is the rerun entry point Ventouras referred to in the incident thread. Re-running the shard `23:30` unit task is the practical way to regenerate the day inputs and trigger the downstream shard day flow.

## Shard Day Flow

### `scv_shard/day/tls_scv_shard/00_scv_filter_matches.sh`

Purpose:
Validate and filter the narrow day matches before rolling aggregation.

Main input:

- `/var/opt/nio/feeds/scv/scv.day_merged_matches.YYYY-MM-DD.csv`

Main output pattern:

- filtered copies used by the later rolling-window steps

### `scv_shard/day/tls_scv_shard/01_scv_create_symlinks_to_matches.sh`

Purpose:
Create the rolling-day symlink set that the day aggregators consume.

Main output pattern:

- `/var/opt/nio/feeds/scv/tmp_shard/scv.day_merged_matches.NNN.csv.filtered`

Why it matters:
If the rolling symlink set is incomplete, the count and direction cube passes will not see the expected history window.

### `scv_shard/day/tls_scv_shard/count.d/count.json`

Purpose:
Aggregate the rolling narrow day files into one shard partial for the master.

Main output:

- `/var/opt/nio/feeds/scv/tmp_shard/scv.day_rolling_merged_matches.partial.YYYY-MM-DD.csv`

Meaning:
This is the core shard contribution to the master-side match aggregation.

### `scv_shard/day/tls_scv_shard/direction.d/direction.json`

Purpose:
Produce transition partials for FBBMOB and MOBFBB.

Main outputs:

- `/var/opt/nio/feeds/scv/tmp_shard/scv.transitions.fbbmob.day_merged_matches.partial.YYYY-MM-DD.csv`
- `/var/opt/nio/feeds/scv/tmp_shard/scv.transitions.mobfbb.day_merged_matches.partial.YYYY-MM-DD.csv`

### `scv_shard/day/tls_scv_shard/04_schedule_day_matches_scv_master.sh`

Purpose:
Rename the shard day partials with the shard hostname and copy them to scv_master through `task -import-scv-master`.

Files copied:

- `scv.day_rolling_merged_matches.partial.<shard>.YYYY-MM-DD.csv`
- `scv.transitions.fbbmob.day_merged_matches.partial.<shard>.YYYY-MM-DD.csv` when transitions are enabled
- `scv.transitions.mobfbb.day_merged_matches.partial.<shard>.YYYY-MM-DD.csv` when transitions are enabled

Destination meaning on master:

- `/var/opt/nio/aggregations/scv/YYYY-MM-DD/`

Operational meaning:
This is the handoff that should show up in `task.log` as a `CopyTask End` entry for source `matches_scv_master`.

### `scv_shard/day/tls_scv_shard/05_schedule_day_scv_report_master.sh`

Purpose:
If reporting is enabled, copy the shard-side domain-report partial and raw day matches to scv_master as a separate `scv_report` datasource.

Files copied:

- `scv.domain_report.partial.<shard>.YYYY-MM-DD.csv`
- `scv.day_merged_matches_raw.partial.<shard>.YYYY-MM-DD.csv`

Destination meaning on master:

- `/var/opt/nio/aggregations/scv/YYYY-MM-DD/`

Operational meaning:
This is reporting-only handoff. It is useful for SCV report outputs, but it is distinct from the core match partial handoff used by `matches_scv_master`.

## Master Pre-Gate and Gate

### `scv_master/day/matches_scv_master/00_scv_aggregate_shards.json`

Purpose:
Aggregate the shard match partials delivered into the master aggregation directory.

Main input pattern:

- `/var/opt/nio/aggregations/scv/YYYY-MM-DD/scv.day_rolling_merged_matches.partial.*.YYYY-MM-DD.csv`

Main output:

- `/var/opt/nio/feeds/scv/tmp/scv.matches_scv_master.final.csv`

Why it matters:
This file shows whether the master actually had shard partials to aggregate.

### Bump scripts for `matches_scv_master`, `userkey_scv_master`, and `subintel_scv_master`

Purpose:
Advance the `3/3` gate required before the core `day/scv` flow runs.

Operational meaning:

- `matches_scv_master` contributes the shard TLS match side
- `userkey_scv_master` contributes fixed-device side data
- `subintel_scv_master` contributes mobile state side data

Important troubleshooting rule:
A successful `3/3` gate proves the master day flow was allowed to run. It does not prove every shard contributed the expected match partials.

## Master Core SCV Flow

### `scv_master/day/scv/00_fetch_cellmaps.sh`

Purpose:
Stage mobile and fixed cellmap JSON files into the master temp area.

Main outputs:

- `/var/opt/nio/feeds/scv/tmp/mobile_cellmap.json`
- `/var/opt/nio/feeds/scv/tmp/fixed_cellmap.json`
- `/var/opt/nio/feeds/scv/tmp/scv_report_cellmaps.YYYY-MM-DD.ready`

### `scv_master/day/scv/00_scv_final_matches.sh`

Purpose:
Turn the aggregated master match file into a mapping file after applying `min_matches` filtering.

Main input:

- `/var/opt/nio/feeds/scv/tmp/scv.matches_scv_master.final.csv`

Main output:

- `/var/opt/nio/feeds/scv/tmp/user_mobile_to_fixed_map.csv`

### `scv_master/day/scv/01_scv_merger.sh`

Purpose:
Build the final SCV device and distribution outputs using the mapping file, userkey data, subintel, cellmap-derived scopes, and SCV config.

Main outputs:

- `/var/opt/nio/feeds/scv/home_analytics.YYYY-MM-DD.log`
- `/var/opt/nio/feeds/scv/home_analytics_distributions.YYYY-MM-DD.log`

### `scv_master/day/scv/02_concatenate_transitions_partials.sh`

Purpose:
Build final transition outputs from the shard transition partials.

Main output patterns:

- `/var/opt/nio/feeds/scv/home_analytics.transitions.fbbmob.YYYY-MM-DD.log`
- `/var/opt/nio/feeds/scv/home_analytics.transitions.mobfbb.YYYY-MM-DD.log`

## Master Reporting Flow

### `scv_master/day/scv_report/00_domain_report.caller.json`

Purpose:
Combine the shard domain report partials into the final master domain report.

Main output:

- `/var/opt/nio/feeds/scv/scv.domain_report.YYYY-MM-DD.csv`

### `scv_master/day/scv_report/01_raw_matches_report.sh`

Purpose:
Build the final raw matches report using the shard raw-day-report partials and the staged cellmaps.

Main prerequisites:

- `/var/opt/nio/feeds/scv/tmp/scv_report_cellmaps.YYYY-MM-DD.ready`
- `/var/opt/nio/feeds/scv/tmp/mobile_cellmap.json`
- `/var/opt/nio/feeds/scv/tmp/fixed_cellmap.json`

Main output:

- `/var/opt/nio/feeds/scv/scv.raw_matches_report.YYYY-MM-DD.csv`

### `scv_master/day/scv_report/02_scope_report.sh`

Purpose:
Build the final scope report from the distributions output and the raw matches report.

Main inputs:

- `/var/opt/nio/feeds/scv/home_analytics_distributions.YYYY-MM-DD.log`
- `/var/opt/nio/feeds/scv/scv.raw_matches_report.YYYY-MM-DD.csv`

Main output:

- `/var/opt/nio/feeds/scv/home_analytics_scope_report.YYYY-MM-DD.log`

## Practical Interpretation

- If `home_analytics` drops but the `3/3` gate succeeded, inspect whether all shard partials arrived before assuming the master script itself failed.
- If `matches_scv_master` copies are missing for a shard/date, the master can still run with reduced shard coverage.
- If report files are missing but core home analytics exists, the issue may be isolated to the reporting path rather than the core SCV merge.