# Command Playbook

All commands are for deployed pocket hosts only.

## Safety Modes

- Mode A: read-only checks (default)
- Mode B: trigger actions (requires explicit user confirmation)

## SSH Preflight

1. Connectivity
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "hostname && date"

2. Runtime path presence
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "ls -ld /opt/nio /var/opt/nio /etc/opt/nio"

3. ETL runner presence
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "ls -l /opt/nio/libexec/etl_runner.sh"

## Read-Only File Exploration

Use this to list latest files for a target path:
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "find <target_dir> -maxdepth 2 -type f -printf '%T@|%TY-%Tm-%Td %TH:%TM:%TS|%s|%p\n' 2>/dev/null | sort -t'|' -nr -k1,1 | head -10"

Interpret columns:
- epoch mtime
- printable timestamp
- bytes
- full path

## Example: scv_shard unit input check on pocket-ath-mu1

ssh -i ~/.ssh/id_rsa phu.tran@pocket-ath-mu1.niometrics.com "find /var/opt/nio/aggregations -maxdepth 3 -type f \( -name '*scv*' -o -name '*tls*' \) -printf '%T@|%TY-%Tm-%Td %TH:%TM:%TS|%s|%p\n' 2>/dev/null | sort -t'|' -nr -k1,1 | head -10"

Expected response format:
- host: pocket-ath-mu1
- role: scv_shard
- source: tls_scv_shard or user-specified source
- interval: unit
- files: top 10 with timestamp, size, path
- status: found or empty or missing path or permission denied

## Read-Only ETL Log Checks

Latest ETL logs:
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "find /var/opt/nio/log -maxdepth 1 -type f -name '*etl*' -printf '%T@|%TY-%Tm-%Td %TH:%TM:%TS|%s|%p\n' | sort -t'|' -nr -k1,1 | head -10"

Role-specific logs by interval and source pattern:
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "find /var/opt/nio/log -maxdepth 1 -type f -name '*<role>*<interval>*<source>*' -printf '%T@|%TY-%Tm-%Td %TH:%TM:%TS|%s|%p\n' | sort -t'|' -nr -k1,1 | head -10"

## Trigger Actions With etl_runner

Never run these without explicit user confirmation.

Template:
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "sudo -n -u nio /opt/nio/libexec/etl_runner.sh --role <role> --interval <interval> --source <source> --timestamp <unix_ts>"

### Role And Source Shortcuts

- scv_shard unit:
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "sudo -n -u nio /opt/nio/libexec/etl_runner.sh --role scv_shard --interval unit --source tls_scv_shard --timestamp <unix_ts>"

- scv_shard day:
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "sudo -n -u nio /opt/nio/libexec/etl_runner.sh --role scv_shard --interval day --source tls_scv_shard --timestamp <unix_ts>"

- scv_master day:
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "sudo -n -u nio /opt/nio/libexec/etl_runner.sh --role scv_master --interval day --source scv --timestamp <unix_ts>"

- mrs day template:
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "sudo -n -u nio /opt/nio/libexec/etl_runner.sh --role mrs --interval day --source <mrs_source> --timestamp <unix_ts>"

Unit timestamp helper on remote host:
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "TS=$(($(date +%s) - ($(date +%s) % 1800))); echo $TS"

Day timestamp helper on remote host:
ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com "date -d '2026-04-22 00:00:00' +%s"

## Trigger Verification Checklist

After trigger, run read-only verification:
1. check latest etl logs in /var/opt/nio/log/
2. check expected output directory for top 10 latest files
3. check downstream handoff artifacts when applicable

## Optional Task Broker Handoff Validation

Use only for validation and diagnostics of downstream copy behavior:
- /opt/nio/bin/task -import-broker
- /opt/nio/bin/task -import-scv-master
- /opt/nio/bin/task -import-scv-broker

Do not run broker import actions unless the user explicitly requests it.

## Troubleshooting

- missing directory: report role to path mismatch and propose nearest valid runtime root
- permission denied: suggest sudo or access escalation path
- empty result: confirm timestamp window and source naming pattern
- host not reachable: report SSH failure and request alternate host from server map
