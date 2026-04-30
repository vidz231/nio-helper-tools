# SCV Troubleshooting Notes

This folder is a private operator runbook for SCV troubleshooting in deployed environments.

It focuses on the SCV shard and SCV master TLS-key flow, especially the reporting path and the common production questions:

- which files should exist at each major step
- which log to inspect for copy, gate, and ETL failures
- what `scope_a` and `scope_b` actually depend on
- how to reason about incidents like a sudden drop in red devices

## Pages

- `scv-tls-flow.md`: execution order and handoff meaning
- `scv-step-io-reference.md`: important input and output files by step
- `scv-logs-and-troubleshooting.md`: which logs answer which questions, plus an incident playbook
- `scv-scope-config.md`: how scope fields are derived in SCV master

## Start Here When SCV Numbers Drop

1. Validate the business symptom in `/var/opt/nio/feeds/scv/home_analytics.YYYY-MM-DD.log`.
2. Check whether the master `scv` day task reached `3/3` and ran successfully.
3. Check `task.log` for missing shard copy events into `/var/opt/nio/aggregations/scv/YYYY-MM-DD/`.
4. Check `scv_shard_day.log` and `scv_master_day.log` for script-level failures on the same date.
5. If the issue is historical, switch to rotated logs before drawing conclusions.
6. Before planning a rerun, confirm the required retained input files still exist.

## Runtime Surfaces Used Most Often

- `/var/opt/nio/log/task.log`: copy tasks, bump tasks, scheduling audit
- `/var/opt/nio/log/scv_shard_unit.log`: unit TLS matching behavior on shards
- `/var/opt/nio/log/scv_shard_day.log`: end-of-day shard rollup and master handoff
- `/var/opt/nio/log/scv_master_day.log`: master aggregation, merger, and reporting steps
- `/var/opt/nio/feeds/scv/`: final SCV outputs and staged master temp files
- `/var/opt/nio/aggregations/scv/`: shard partials delivered to scv_master

## Scope of This Runbook

This runbook is intentionally centered on:

- `scv_shard/unit/tls_scv_shard`
- `scv_shard/day/tls_scv_shard`
- `scv_master/day/matches_scv_master`
- `scv_master/day/scv`
- `scv_master/day/scv_report`

It references upstream NCORE, NLIVE, and MRS behavior only when those stages directly affect shard/master troubleshooting.