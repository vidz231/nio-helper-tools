# SCV Domain Report Validation Report

## Verdict

PASS for the `nio-analytics` `feature/scv-domain-reports` staged-source validation.

This report covers a controlled preserved-snapshot replay, not a scheduler-observed production run. The replay proves the changed Python logic, deployed wrapper entry points, artifact continuity, and mathematical consistency of the generated SCV domain report using real mobile and fixed SCV inputs copied from the ATH topology.

## Scope

- Repository: `nio-analytics`
- Branch under test: `feature/scv-domain-reports`
- Primary replay day: `2026-04-10`
- Replay host: `pocket-ath-mu1`
- Mobile-side source: `pocket-ath-mu1`
- Fixed-side source: `pocket-ath-np2`
- Replay root: `/tmp/scv_domain_replay_20260410_8755243c`
- Validation harness: `offline/scv-validation-visualizer`

## Topology Used

Mobile side:

- `pocket-ath-np1`: ncore, nlive
- `pocket-ath-mu1`: mrs, scv_shard, scv_master
- `pocket-ath-mu3`: scv_broker, scv_shard

Fixed side:

- `pocket-ath-np2`: ncore, nlive
- `pocket-ath-mu2`: mrs

The key correction was that fixed-side replay inputs were on `pocket-ath-np2`, not `pocket-ath-mu2`.

## Approach

1. Stage the current `nio-analytics` worktree to `pocket-ath-mu1`:

   ```bash
   ./rbuild.sh nio-analytics -s
   ```

2. Run the affected staged-source Python tests on `pocket-ath-mu1`:

   ```bash
   PYTHONPATH=/home/phu.tran/rbuild/nio-analytics/py3/src/lib/python3 \
   /opt/nio/lib/analytics/virtualenv/bin/python3.12 -m unittest \
     py3.tests.analytics.test_scv_day_matcher \
     py3.tests.analytics.test_scv_domain_report
   ```

3. Create an isolated replay root on `pocket-ath-mu1` under `/tmp/scv_domain_replay_<YMD>_<runid>`.

4. Copy preserved mobile TLS inputs from `pocket-ath-mu1`.

5. Copy preserved fixed TLS inputs and fixed userkey logs from `pocket-ath-np2`.

6. Decompress and merge the sharded TLS files into the layout expected by `scv_day_matcher`:

   ```text
   <replay_root>/var/opt/nio/aggregations/scv_matches/<YMD>/scv.tls.<type>.<unit>.<probe>.<network>.csv
   ```

7. Run the deployed wrapper `/opt/nio/bin/scv_day_matcher` while forcing it to import staged branch code:

   ```bash
   export PYTHONPATH=/home/phu.tran/rbuild/nio-analytics/py3/src/lib/python3
   /opt/nio/bin/scv_day_matcher \
     --date <YMD> \
     --config <replay_root>/etc/opt/nio/analytics.json \
     --working-dir <replay_root>/var/opt/nio/aggregations \
     --feeds-dir <replay_root>/var/opt/nio/feeds/scv
   ```

8. Copy the generated shard partial into the master layout:

   ```text
   <replay_root>/var/opt/nio/aggregations/scv/<YMD>/scv.domain_report.partial.pocket-ath-mu1.<YMD>.csv
   ```

9. Run the deployed wrapper `/opt/nio/bin/scv_domain_report` with staged branch imports:

   ```bash
   export PYTHONPATH=/home/phu.tran/rbuild/nio-analytics/py3/src/lib/python3
   /opt/nio/bin/scv_domain_report \
     --date <YMD> \
     --aggr-dir <replay_root>/var/opt/nio/aggregations \
     --feeds-dir <replay_root>/var/opt/nio/feeds/scv
   ```

10. Verify the generated final report mathematically against the partial report.

## Primary Evidence: 2026-04-10

Run id: `8755243c5644`

Status: PASS

Unit tests:

- `py3.tests.analytics.test_scv_day_matcher`: passed
- `py3.tests.analytics.test_scv_domain_report`: passed
- Total: `73` tests, `OK`

Input replay counts:

| Metric | Count |
| --- | ---: |
| Copied mobile TLS inputs | 384 |
| Copied fixed TLS inputs | 1920 |
| Copied fixed userkey logs | 1 |
| Merged mobile TLS files | 192 |
| Merged fixed TLS files | 192 |

Matcher output:

| Metric | Count |
| --- | ---: |
| Raw matches | 718136 |
| Matches after invalid key filtering | 715356 |
| Deduplicated merged match rows | 37194 |
| Domain-report partial lines | 7690 |

Domain report output:

| Artifact | Path | Lines |
| --- | --- | ---: |
| Merged matches | `/tmp/scv_domain_replay_20260410_8755243c/var/opt/nio/feeds/scv/scv.day_merged_matches.2026-04-10.csv` | 37194 |
| Shard partial | `/tmp/scv_domain_replay_20260410_8755243c/var/opt/nio/feeds/scv/scv.domain_report.partial.2026-04-10.csv` | 7690 |
| Master-layout partial | `/tmp/scv_domain_replay_20260410_8755243c/var/opt/nio/aggregations/scv/2026-04-10/scv.domain_report.partial.pocket-ath-mu1.2026-04-10.csv` | 7690 |
| Final report | `/tmp/scv_domain_replay_20260410_8755243c/var/opt/nio/feeds/scv/scv.domain_report.2026-04-10.csv` | 7690 |

Module provenance:

```text
/home/phu.tran/rbuild/nio-analytics/py3/src/lib/python3/nioanalytics/scv/scv_day_matcher.py
/home/phu.tran/rbuild/nio-analytics/py3/src/lib/python3/nioanalytics/scv/scv_domain_report.py
```

This proves the deployed `/opt/nio/bin/...` wrappers executed staged branch code.

## Mathematical Verification

### Column Definitions

| Column | Definition |
| --- | --- |
| `domain` | TLS `server_name` / domain key used to group report metrics. |
| `unique_valid_tls` | Count of distinct TLS keys observed for that domain during the raw domain-key scan. |
| `valid_tls_matches` | Count of filtered TLS match records whose `server_name` equals that domain. |
| `duplicated_tls_keys` | Count of observed TLS keys for that domain that were classified invalid because they were shared across mobile users. |

### Formulas

For each shard partial:

```text
partial.unique_valid_tls(domain)
  = count_distinct(tls_key where tls_key was observed for domain in raw TLS inputs)
```

```text
partial.valid_tls_matches(domain)
  = count(match in filtered_matches where match.server_name = domain)
```

```text
partial.duplicated_tls_keys(domain)
  = count(tls_key in raw_domain_keys[domain] where tls_key in invalid_keys)
```

For the master combined report:

```text
final.metric(domain)
  = sum(partial_i.metric(domain) for each shard partial_i)
```

In this controlled replay there was one master-layout shard partial:

```text
final.metric(domain) = partial.metric(domain)
```

for every domain and for every metric column.

### Computed Totals

| Metric | Final report total | Partial total | Result |
| --- | ---: | ---: | --- |
| `unique_valid_tls` | 349280 | 349280 | PASS |
| `valid_tls_matches` | 715356 | 715356 | PASS |
| `duplicated_tls_keys` | 124 | 124 | PASS |

Structural checks:

| Check | Result |
| --- | --- |
| Final header matches expected schema | PASS |
| Partial header matches expected schema | PASS |
| Numeric columns are integers | PASS |
| Numeric columns are non-negative | PASS |
| Final report domains are unique | PASS |
| Final report domains are sorted | PASS |
| Final report rows equal partial rows for one-shard replay | PASS |
| Final report has nonzero rows | PASS |

## Corroborating PASS Runs

| Run id | Replay day | Status | Copied mobile | Copied fixed | Merged mobile | Merged fixed | Merged match rows | Final report rows |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `966a0505b3a4` | `2026-04-10` | PASS | 384 | 1920 | 192 | 192 | 37194 | 7690 |
| `8755243c5644` | `2026-04-10` | PASS | 384 | 1920 | 192 | 192 | 37194 | 7690 |
| `5996d9352096` | `2026-04-09` | PASS | 384 | 1920 | 192 | 192 | 21934 | 7059 |
| `fc4d4a23af96` | `2026-04-08` | PASS | 184 | 880 | 92 | 88 | 15792 | 5172 |

An attempted `2026-04-07` replay correctly failed acceptance because no mobile or fixed replay inputs were copied. That is useful negative evidence: the harness does not mark an empty replay as PASS.

## Does This Prove Production Works?

It proves the most important runtime logic path for this change:

- The packaged wrapper names exist and can be invoked.
- The wrappers can execute the staged branch modules.
- Real mobile and fixed SCV inputs can be replayed into the expected matcher layout.
- `scv_day_matcher` produces merged matches and a domain-report partial.
- `scv_domain_report` consumes the master-layout partial and writes the final domain report.
- The final report is mathematically consistent with the shard partial.

It does not fully prove every production operational concern:

- It is not a scheduler-observed production run.
- It does not prove RPM/package deployment parity after installing a built package.
- It does not prove cron/task timing, task import, permissions, or cleanup in the live scheduler path.
- It uses a controlled replay root under `/tmp`, not live `/var/opt/nio` output paths.
- The primary replay has one master-layout partial, so it proves combine semantics for the available replay partial, not multi-shard summation across multiple independent shard partials.

Production confidence from this validation:

- Python SCV report logic: high
- Wrapper-to-module execution path: high
- Artifact path continuity for shard partial to master final report: high
- Mathematical correctness of final report aggregation for the replay: high
- Scheduler/RPM production deployment parity: not proven by this report

## Manual RPM And Scheduler Observation Gate

RPM creation is intentionally manual and must be performed by the user in Jenkins.

Jenkins job:

```text
https://jbuilder.niometrics.com/job/testing-rocky8/job/nio-analytics/
```

Manual build input:

```text
changeset = feature/scv-domain-reports
```

After the Jenkins RPM is built and installed, use the visualizer `Manual Jenkins RPM / Scheduler Observation` panel to record:

- Jenkins build URL
- Jenkins build number
- RPM version/release
- changeset or branch
- install target hosts
- install timestamp

Expected install targets:

- `pocket-ath-mu1`
- `pocket-ath-mu3`

The scheduler-observation action does not trigger Jenkins, install RPMs, or write live scheduler output paths. It reads and reports:

- `rpm -q nio-analytics`
- `/opt/nio/bin/scv_day_matcher`
- `/opt/nio/bin/scv_domain_report`
- recent scheduler log markers from `task.log`, `etl.log`, `scv_shard_day.log`, and `scv_master_day.log`
- live SCV domain-report artifact inventory

Scheduler-observed verdicts:

- `PASS`: RPM evidence, wrapper evidence, scheduler/log marker, and live domain-report artifact are present.
- `PASS_WITH_NOTES`: RPM evidence, wrapper evidence, and scheduler/log marker are present, but no live report artifact is available yet.
- `BLOCKED`: RPM evidence is missing, wrappers are missing, scheduler markers are absent, or artifact continuity breaks.

## Recommendation

Use this report as a full PASS for staged-source SCV domain-report logic and artifact continuity.

For production release confidence, add one of the following follow-up gates:

1. Build/install the package and rerun the same replay without `PYTHONPATH` override.
2. Capture one scheduler-observed day run and verify the same artifacts in live output locations.
3. For multi-shard proof, replay or capture at least two shard partials and verify:

   ```text
   final.metric(domain) = partial_shard_1.metric(domain) + partial_shard_2.metric(domain) + ...
   ```
