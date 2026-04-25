# SCV Validation Visualizer

Local-only developer harness for the `feature/scv-domain-reports` validation flow.

It serves an HTML UI that can run whitelisted actions:

- `full-pass-replay`
- `scheduler-observe`
- `install-and-observe`
- `etl-run-and-observe`

The action stages `nio-analytics`, runs the two SCV Python test modules, builds an isolated replay root on `pocket-ath-mu1`, copies mobile inputs from `pocket-ath-mu1` and fixed inputs from `pocket-ath-np2`, then runs the deployed SCV wrappers with `PYTHONPATH` pointed at staged source.

## Run

```bash
cd /Volumes/vidzdatastore/work/mobileum_source/nio-analytics/offline/scv-validation-visualizer
python3 server.py
```

Open:

```text
http://127.0.0.1:8765
```

## Safety

- Binds to `127.0.0.1` only.
- Uses Python standard library only.
- Browser input is limited to a validated replay date.
- Browser cannot submit shell commands, hosts, or filesystem paths.
- Remote replay output is written under `/tmp/scv_domain_replay_<YMD>_<runid>` on `pocket-ath-mu1`.
- Live `/var/opt/nio` scheduler output directories are not written by the replay.
- Jenkins RPM creation remains manual; the visualizer only records user-provided RPM evidence.
- Scheduler observation reads RPM state, wrapper state, logs, and artifacts from `pocket-ath-mu1` and `pocket-ath-mu3`.

## Expected PASS Evidence

The UI shows `PASS` only after:

- `./rbuild.sh nio-analytics -s` succeeds.
- `test_scv_day_matcher` and `test_scv_domain_report` pass from staged source.
- `scv_day_matcher` and `scv_domain_report` resolve to staged modules under `/home/phu.tran/rbuild/nio-analytics/py3/src/lib/python3`.
- Preserved replay inputs produce merged mobile and fixed TLS files.
- `scv_day_matcher` writes `scv.day_merged_matches.<YMD>.csv` and `scv.domain_report.partial.<YMD>.csv`.
- `scv_domain_report` consumes the master-layout partial and writes `scv.domain_report.<YMD>.csv`.

This is a controlled preserved-snapshot replay, not a scheduler-observed production run.

## Scheduler Observation

After manually building a Jenkins RPM, expand the `Manual Jenkins RPM / Scheduler Observation` section.

To install and observe from the visualizer, enter the RPM version/release, for example `1.24-0.42`, and click `Install RPM + Observe`.

To observe after installing manually, fill in the build/install evidence and click `Observe Only`.

To force the installed SCV day ETL path and then observe, fill in the build/install evidence and click `Run ETL + Observe`.

At least one RPM evidence field is required before observation starts:

- Jenkins URL
- Jenkins build number
- RPM version/release
- install confirmation

The observation action records:

- Jenkins URL / build number / RPM version / changeset / install hosts / install time.
- `rpm -q nio-analytics` from `pocket-ath-mu1` and `pocket-ath-mu3`.
- `/opt/nio/bin/scv_day_matcher` and `/opt/nio/bin/scv_domain_report` presence.
- Recent SCV scheduler log markers from `task.log`, `etl.log`, `scv_shard_day.log`, and `scv_master_day.log` when present.
- Live SCV domain report artifact inventory.

It does not build RPMs, trigger Jenkins, or write live scheduler output directories.

`Install RPM + Observe` installs only these whitelisted packages on `pocket-ath-mu1` and `pocket-ath-mu3`:

- `nio-analytics-<version>`
- `nio-analytics-cubes-<version>`
- `nio-analytics-schema-<version>`

It uses `sudo dnf install -y` on the target hosts and then runs the same scheduler observation.

`Run ETL + Observe` runs only these whitelisted commands on `pocket-ath-mu1`, then runs the same scheduler observation:

```bash
sudo -n -u nio /opt/nio/libexec/etl_runner.sh --role scv_shard --interval day --source tls_scv_shard --timestamp <day-start-epoch>
sudo -n -u nio /opt/nio/libexec/etl_runner.sh --role scv_master --interval day --source scv --timestamp <day-start-epoch>
```

This action mutates live SCV pipeline outputs and should only be used when a forced ETL run is intended.

Before running ETL, it repairs ownership to `nio:nio` for existing selected-day SCV outputs under:

- `/var/opt/nio/feeds/scv/*<YMD>*`
- `/var/opt/nio/feeds/scv/scv.day_merged_matches.*.csv*`
- `/var/opt/nio/feeds/scv/tmp_shard/*<YMD>*`
- `/var/opt/nio/aggregations/scv/<YMD>/*`
- SCV day log files touched by the forced ETL path

Run artifacts are stored under `runs/` and ignored by git.
