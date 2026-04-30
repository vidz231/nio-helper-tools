# SCV Logs and Troubleshooting

This page explains what each log is for and how to troubleshoot incidents like a sudden drop in red devices.

## Main Log Families

### `task.log`

Location:

- `/var/opt/nio/log/task.log`
- rotated history: `/var/opt/nio/log/old/task.log.N`

Use this when you need to answer:

- Did the shard copy task run?
- Which shard files reached scv_master?
- Did the `matches_scv_master`, `userkey_scv_master`, and `subintel_scv_master` tasks all complete?
- Did the `scv` day task audit reach `3/3`?

What it represents:

- cross-machine copy events
- queue and scheduling actions
- bump and audit records

Typical evidence to look for:

- `CopyTask End` entries for `matches_scv_master`
- `CopyTask End` entries for `scv_report`
- `Successfully ran task` entries for the day cube runs
- audit output from `/opt/nio/bin/task -list-audit`

### `scv_shard_unit.log`

Location:

- `/var/opt/nio/log/scv_shard_unit.log`
- rotated history: `/var/opt/nio/log/old/scv_shard_unit.log.N`

Use this when you need to answer:

- Did unit TLS matching run and produce raw unit files?
- Did blacklists, time exclusions, or probe-pair filtering remove expected data?
- Did the matching logic skip inputs because files were empty or missing?

### `scv_shard_day.log`

Location:

- `/var/opt/nio/log/scv_shard_day.log`
- rotated history: `/var/opt/nio/log/old/scv_shard_day.log.N`

Use this when you need to answer:

- Did the `23:30` day scheduling step run?
- Was `scv.day_merged_matches.YYYY-MM-DD.csv` created?
- Did invalid-TLS-key handling or domain-report generation fail?
- Did the shard rename and copy its partials to scv_master?

### `scv_master_day.log`

Location:

- `/var/opt/nio/log/scv_master_day.log`
- rotated history: `/var/opt/nio/log/old/scv_master_day.log.N`

Use this when you need to answer:

- Did the master aggregate shard partials?
- Did cellmap staging succeed?
- Did the mapping file and final `home_analytics` outputs get built?
- Did the reporting steps fail after core SCV completed?

### `etl.log`

Location:

- `/var/opt/nio/log/etl.log`

Use this as supplementary context when you need the generic ETL runner surface. It is not the primary log for SCV incident diagnosis.

## Troubleshooting Order

### 1. Validate the business symptom

Start from the final output the business is looking at.

Typical example:

- count red devices from `/var/opt/nio/feeds/scv/home_analytics.YYYY-MM-DD.log`
- compare the problem date with the previous and next day

Why:
This confirms whether the incident is real, isolated to one date, and limited to one output type.

### 2. Confirm the master `scv` day task status

Check whether the `scv` day task for the target date reached `3/3` and ran.

Interpretation:

- If the gate did not reach `3/3`, the core day flow may never have started.
- If it reached `3/3`, the master flow ran, but shard coverage may still have been incomplete.

Important rule:
A successful `3/3` status does not prove that all shard partials were present. It only proves the three master-side source families satisfied the gate.

### 3. Check shard-to-master copy coverage in `task.log`

For a date-specific drop, inspect `CopyTask End` lines for:

- `scv.day_rolling_merged_matches.partial.<shard>.YYYY-MM-DD.csv`

What this answers:

- Which shard hosts delivered core match partials
- Which shard hosts did not deliver partials for the problem date

This was the decisive technique in the April 24 incident: the master `scv` task succeeded, but `task.log` still showed only partial shard coverage for the affected date.

### 4. Distinguish missing handoff from script failure

If a shard file is missing on the master, there are two broad cases:

- The shard never created or copied it
- The shard created it, but the master-side issue was later in aggregation or reporting

Use:

- `scv_shard_day.log` to see whether the shard built the day outputs and attempted the handoff
- `task.log` to see whether the copy ended successfully
- `scv_master_day.log` to see whether master aggregation or reporting later failed

### 5. Switch to rotated logs when the incident is historical

Do not assume the live log files still cover the incident window.

For historical incidents, collect:

- `/var/opt/nio/log/old/task.log.N`
- `/var/opt/nio/log/old/scv_shard_unit.log.N`
- `/var/opt/nio/log/old/scv_shard_day.log.N`
- `/var/opt/nio/log/old/scv_master_day.log.N`

Why:
The April 24 investigation had to move to rotated logs because the active logs no longer covered the relevant runtime window.

### 6. Check retention before planning a rerun

Before promising a rebuild for a historical date, confirm whether the shard still retains:

- `/var/opt/nio/aggregations/scv_matches/YYYY-MM-DD/scv.unit_merged_matches_raw.YYYY-MM-DD-??-??.csv`

If those files are gone, the usual shard `23:30` rerun path for that date is no longer available.

### 7. Use the right rerun entry point

If the retained shard raw unit files for that date still exist, the practical rerun path is:

- rerun the shard `unit 23:30` task for the target date on the missing shard host(s)

Why:

- it rebuilds the shard day inputs from the retained raw unit files
- it also schedules the shard day flow automatically
- after shard day completes, the master should receive the regenerated partials

### 8. Avoid wildcard mistakes during recovery

Be careful with `touch` or similar commands using globs.

If a shell glob does not match, the shell may pass the literal pattern through, and `touch` can create bogus files like:

- `scv.day_rolling_merged_matches.partial.*.2026-04-27.csv`

That happened during the incident discussion and is exactly the kind of recovery noise this runbook should prevent.

## April 24 Incident Pattern

### Symptom

- Red-device count dropped on `2026-04-24`
- Counts recovered on the next day

### What the investigation established

1. The master `scv` day task still reached `3/3` and ran successfully.
2. `task.log` showed only a subset of shard partials arrived for the problem date.
3. The report-path logic on shard could fail due to malformed non-UTF-8 TLS bytes.
4. That failure could stop the shell flow before later steps unless the hotfix behavior was present.
5. Retention had already deleted some older shard raw unit files, limiting rerun options.

### Practical lessons extracted from that incident

- Always start from the final business output, not from an internal assumption.
- A successful day task audit is necessary but not sufficient.
- Missing `CopyTask End` entries by shard/date are often more informative than the top-level task status.
- Reporting failures and core matching failures are related but not identical.
- Historical reruns are bounded by retention, not just by willingness to rerun.

## Fast Question-to-Log Map

| Question | Best first place to look |
| --- | --- |
| Did the shard copy arrive on master? | `/var/opt/nio/log/task.log` |
| Did the master day gate fire? | `/var/opt/nio/log/task.log` or task audit |
| Did the shard 23:30 unit run normalize the day files? | `/var/opt/nio/log/scv_shard_day.log` |
| Did the master build `home_analytics`? | `/var/opt/nio/log/scv_master_day.log` |
| Did reporting fail while core SCV still completed? | `/var/opt/nio/log/scv_master_day.log` plus presence of report outputs in `/var/opt/nio/feeds/scv/` |
| Can I still rerun that date from the shard? | Check retained raw unit files under `/var/opt/nio/aggregations/scv_matches/YYYY-MM-DD/` |