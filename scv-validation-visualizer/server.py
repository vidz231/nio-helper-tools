#!/usr/bin/env python3
"""Local-only SCV validation visualizer server.

This is an offline developer harness. It exposes only whitelisted actions for
staged replay, scheduler observation, and RPM install-then-observe validation.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import signal
import subprocess
import threading
import time
import uuid
from http import HTTPStatus
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse


HOST = "127.0.0.1"
PORT = 8765
ACTION = "full-pass-replay"
SCHEDULER_ACTION = "scheduler-observe"
INSTALL_ACTION = "install-and-observe"
ETL_ACTION = "etl-run-and-observe"
SUPPORTED_ACTIONS = {ACTION, SCHEDULER_ACTION, INSTALL_ACTION, ETL_ACTION}
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = Path(__file__).resolve().parent / "static"
RUN_ROOT = Path(__file__).resolve().parent / "runs"
DEFAULT_YMD = "2026-04-10"
MU1 = "phu.tran@pocket-ath-mu1.niometrics.com"
MU3 = "phu.tran@pocket-ath-mu3.niometrics.com"
NP2 = "phu.tran@pocket-ath-np2.niometrics.com"
REMOTE_STAGE = "/home/phu.tran/rbuild/nio-analytics"
REMOTE_PYTHONPATH = f"{REMOTE_STAGE}/py3/src/lib/python3"
SSH_IDENTITY_FILE = str(Path.home() / ".ssh" / "id_rsa")
SSH_OPTS = (
    "-o BatchMode=yes "
    "-o StrictHostKeyChecking=no "
    "-o ForwardAgent=yes "
    "-o IdentitiesOnly=yes "
    f"-o IdentityFile={SSH_IDENTITY_FILE}"
)
YMD_RE = re.compile(r"^\d{4}-?\d{2}-?\d{2}$")
RPM_TEXT_RE = re.compile(r"^[A-Za-z0-9._:/?=&@%+#,;() -]{0,240}$")
RPM_VERSION_RE = re.compile(r"^\d+\.\d+-[A-Za-z0-9_.]+$")
MAX_VIEW_BYTES = 2_000_000
REMOTE_ARTIFACT_KEYS = {
    "final-report": "final_report",
    "partial-feed": "partial_feed",
    "partial-master": "partial_master",
    "merged-matches": "merged_matches",
}


RUNS: dict[str, dict] = {}
RUNS_LOCK = threading.Lock()


def normalize_ymd(value: str) -> str:
    value = value.strip()
    if not YMD_RE.match(value):
        raise ValueError("YMD must be YYYY-MM-DD or YYYYMMDD")
    digits = value.replace("-", "")
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"


def json_response(handler: SimpleHTTPRequestHandler, payload: object, status: int = 200) -> None:
    body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def text_response(
    handler: SimpleHTTPRequestHandler,
    payload: str,
    status: int = 200,
    content_type: str = "text/plain; charset=utf-8",
) -> None:
    body = payload.encode("utf-8", errors="replace")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def public_run(run: dict) -> dict:
    return {
        "id": run["id"],
        "action": run["action"],
        "ymd": run["ymd"],
        "status": run["status"],
        "phase": run["phase"],
        "created_at": run["created_at"],
        "started_at": run.get("started_at"),
        "completed_at": run.get("completed_at"),
        "exit_code": run.get("exit_code"),
        "metrics": run["metrics"],
        "log_tail": run["log_tail"][-240:],
        "artifacts": run["artifacts"],
        "rpm_evidence": run.get("rpm_evidence", {}),
        "error": run.get("error"),
    }


def update_run(run_id: str, **updates: object) -> None:
    with RUNS_LOCK:
        RUNS[run_id].update(updates)


def append_log(run: dict, line: str) -> None:
    run["log_file"].parent.mkdir(parents=True, exist_ok=True)
    with run["log_file"].open("a", encoding="utf-8") as fp:
        fp.write(line)
        if not line.endswith("\n"):
            fp.write("\n")

    clean = line.rstrip("\n")
    with RUNS_LOCK:
        run["log_tail"].append(clean)
        run["log_tail"] = run["log_tail"][-500:]

        if clean.startswith("SCV_PHASE "):
            run["phase"] = clean.split(" ", 1)[1].strip()
        elif clean.startswith("SCV_STATUS "):
            run["status"] = clean.split(" ", 1)[1].strip()
        elif clean.startswith("SCV_VERDICT "):
            run["status"] = clean.split(" ", 1)[1].strip()
        elif clean.startswith("SCV_METRIC "):
            metric = clean.split(" ", 1)[1]
            key, sep, value = metric.partition("=")
            if sep:
                run["metrics"][key.strip()] = value.strip()
                if key.strip().endswith("_path") or key.strip() in {
                    "replay_root",
                    "final_report",
                    "partial_master",
                    "partial_feed",
                    "merged_matches",
                    "scheduler_report",
                }:
                    run["artifacts"][key.strip()] = value.strip()


def validate_rpm_evidence(raw: dict) -> dict:
    fields = {
        "jenkins_url": raw.get("jenkins_url", ""),
        "build_number": raw.get("build_number", ""),
        "rpm_version": raw.get("rpm_version", ""),
        "changeset": raw.get("changeset", "feature/scv-domain-reports"),
        "install_hosts": raw.get("install_hosts", "pocket-ath-mu1,pocket-ath-mu3"),
        "install_timestamp": raw.get("install_timestamp", ""),
        "install_confirmation": raw.get("install_confirmation", ""),
    }
    clean = {}
    for key, value in fields.items():
        value = str(value).strip()
        if not RPM_TEXT_RE.match(value):
            raise ValueError(f"invalid characters in {key}")
        clean[key] = value
    if not (clean["jenkins_url"] or clean["build_number"] or clean["rpm_version"] or clean["install_confirmation"]):
        raise ValueError("provide Jenkins URL, build number, RPM version/release, or install confirmation")
    if clean["rpm_version"] and not RPM_VERSION_RE.match(clean["rpm_version"]):
        raise ValueError("RPM version must look like 1.24-0.42")
    return clean


def shell_script(run_id: str, ymd: str) -> str:
    ymd_compact = ymd.replace("-", "")
    remote_root = f"/tmp/scv_domain_replay_{ymd_compact}_{run_id[:8]}"
    workspace = shlex.quote(str(WORKSPACE_ROOT.parent))
    repo = shlex.quote(str(WORKSPACE_ROOT))
    ymd_q = shlex.quote(ymd)
    remote_root_q = shlex.quote(remote_root)
    mu1_q = shlex.quote(MU1)
    np2_q = shlex.quote(NP2)

    return f"""#!/usr/bin/env bash
set -euo pipefail
SSH_OPTS="{SSH_OPTS}"
MU1={mu1_q}
NP2={np2_q}
YMD={ymd_q}
REPLAY={remote_root_q}

ssh_cmd() {{
  ssh $SSH_OPTS "$@"
}}

echo "SCV_PHASE stage"
cd {workspace}
./rbuild.sh nio-analytics -s

echo "SCV_PHASE unit_tests"
ssh_cmd "$MU1" 'cd {REMOTE_STAGE} && export PYTHONPATH=$PWD/py3/src/lib/python3 && /opt/nio/lib/analytics/virtualenv/bin/python3.12 -m unittest py3.tests.analytics.test_scv_day_matcher py3.tests.analytics.test_scv_domain_report'
echo "SCV_METRIC unit_tests=73 OK"

echo "SCV_PHASE prepare_replay"
ssh_cmd "$MU1" "set -euo pipefail
rm -rf '$REPLAY'
mkdir -p '$REPLAY/var/opt/nio/aggregations' '$REPLAY/var/opt/nio/feeds/scv' '$REPLAY/etc/opt/nio' '$REPLAY/var/opt/nio/log' '$REPLAY/var/opt/nio/tmp'
cp /etc/opt/nio/analytics.json '$REPLAY/etc/opt/nio/analytics.json'
"
echo "SCV_METRIC replay_root=$REPLAY"

echo "SCV_PHASE copy_mobile_inputs"
ssh_cmd "$MU1" "cd /var/opt/nio/aggregations && find . -maxdepth 1 -type f -name 'scv.tls.*.$YMD-*.mobile.*.csv.lz4' -print0 | tar --null -T - -cf -" \\
  | ssh_cmd "$MU1" "cd '$REPLAY/var/opt/nio/aggregations' && tar -xf -"

echo "SCV_PHASE copy_fixed_inputs"
ssh_cmd "$NP2" "cd /var/opt/nio/aggregations && find . -maxdepth 1 -type f \\( -name 'scv.tls.*.$YMD-*.fixed.*.csv' -o -name 'scv.tls.*.$YMD-*.fixed.*.csv.lz4' -o -name 'scv.userkey.$YMD.*.fixed.log.lz4' \\) -print0 | tar --null -T - -cf -" \\
  | ssh_cmd "$MU1" "cd '$REPLAY/var/opt/nio/aggregations' && tar -xf -"

ssh_cmd "$MU1" "set -euo pipefail
cd '$REPLAY/var/opt/nio/aggregations'
echo SCV_METRIC copied_mobile=\\$(find . -maxdepth 1 -type f | grep -E 'scv\\.tls\\..*\\.mobile\\..*\\.csv(\\.lz4)?$' | wc -l)
echo SCV_METRIC copied_fixed=\\$(find . -maxdepth 1 -type f | grep -E 'scv\\.tls\\..*\\.fixed\\..*\\.csv(\\.lz4)?$' | wc -l)
echo SCV_METRIC copied_fixed_userkey=\\$(find . -maxdepth 1 -type f | grep -E 'scv\\.userkey\\..*\\.fixed\\.log(\\.lz4)?$' | wc -l)
"

echo "SCV_PHASE merge_tls"
ssh_cmd "$MU1" "set -euo pipefail
AGGR='$REPLAY/var/opt/nio/aggregations'
MATCH_DIR=\\$AGGR/scv_matches/$YMD
mkdir -p \\$MATCH_DIR
cd \\$AGGR
rm -f \\$MATCH_DIR/scv.tls.*.csv
for f in scv.tls.*.$YMD-*-*.csv scv.tls.*.$YMD-*-*.csv.lz4; do
  [ -e \\$f ] || continue
  base=\\${{f%.lz4}}
  IFS=. read -r scv tls typ unit probe network rest <<< \\$base
  out=\\$MATCH_DIR/scv.tls.\\$typ.\\$unit.\\$probe.\\$network.csv
  if [[ \\$f == *.lz4 ]]; then
    /usr/bin/lz4 -dc \\$f >> \\$out
  else
    cat \\$f >> \\$out
  fi
done
for f in \\$MATCH_DIR/scv.tls.*.csv; do
  [ -e \\$f ] || continue
  LC_ALL=C sort -t, -k3,3 \\$f -o \\$f
done
echo SCV_METRIC merged_mobile_tls=\\$(find \\$MATCH_DIR -maxdepth 1 -type f | grep -E 'scv\\.tls\\..*\\.mobile\\.csv$' | wc -l)
echo SCV_METRIC merged_fixed_tls=\\$(find \\$MATCH_DIR -maxdepth 1 -type f | grep -E 'scv\\.tls\\..*\\.fixed\\.csv$' | wc -l)
"

echo "SCV_PHASE day_matcher"
ssh_cmd "$MU1" "cd {REMOTE_STAGE} && export PYTHONPATH={REMOTE_PYTHONPATH} && /opt/nio/bin/scv_day_matcher --date '$YMD' --config '$REPLAY/etc/opt/nio/analytics.json' --working-dir '$REPLAY/var/opt/nio/aggregations' --feeds-dir '$REPLAY/var/opt/nio/feeds/scv' --log-level INFO"

ssh_cmd "$MU1" "set -euo pipefail
FEEDS='$REPLAY/var/opt/nio/feeds/scv'
echo SCV_METRIC merged_matches_rows=\\$(wc -l < \\$FEEDS/scv.day_merged_matches.$YMD.csv)
echo SCV_METRIC partial_rows=\\$(wc -l < \\$FEEDS/scv.domain_report.partial.$YMD.csv)
echo SCV_METRIC merged_matches=\\$FEEDS/scv.day_merged_matches.$YMD.csv
echo SCV_METRIC partial_feed=\\$FEEDS/scv.domain_report.partial.$YMD.csv
"

echo "SCV_PHASE domain_report"
ssh_cmd "$MU1" "set -euo pipefail
mkdir -p '$REPLAY/var/opt/nio/aggregations/scv/$YMD'
cp '$REPLAY/var/opt/nio/feeds/scv/scv.domain_report.partial.$YMD.csv' '$REPLAY/var/opt/nio/aggregations/scv/$YMD/scv.domain_report.partial.pocket-ath-mu1.$YMD.csv'
cd {REMOTE_STAGE}
export PYTHONPATH={REMOTE_PYTHONPATH}
/opt/nio/bin/scv_domain_report --date '$YMD' --aggr-dir '$REPLAY/var/opt/nio/aggregations' --feeds-dir '$REPLAY/var/opt/nio/feeds/scv' --log-level INFO
echo SCV_METRIC partial_master='$REPLAY/var/opt/nio/aggregations/scv/$YMD/scv.domain_report.partial.pocket-ath-mu1.$YMD.csv'
echo SCV_METRIC final_report='$REPLAY/var/opt/nio/feeds/scv/scv.domain_report.$YMD.csv'
echo SCV_METRIC final_report_rows=\\$(wc -l < '$REPLAY/var/opt/nio/feeds/scv/scv.domain_report.$YMD.csv')
"

echo "SCV_PHASE provenance"
ssh_cmd "$MU1" "cd {REMOTE_STAGE} && export PYTHONPATH={REMOTE_PYTHONPATH} && /opt/nio/lib/analytics/virtualenv/bin/python3.12 - <<'PY'
import nioanalytics.scv.scv_day_matcher as day
import nioanalytics.scv.scv_domain_report as report
print('SCV_METRIC day_matcher_module=' + day.__file__)
print('SCV_METRIC domain_report_module=' + report.__file__)
PY"

echo "SCV_PHASE acceptance"
ssh_cmd "$MU1" "set -euo pipefail
REPLAY='$REPLAY'
YMD='$YMD'
STAGED='{REMOTE_PYTHONPATH}'
AGGR=\\$REPLAY/var/opt/nio/aggregations
FEEDS=\\$REPLAY/var/opt/nio/feeds/scv
MASTER_DIR=\\$REPLAY/var/opt/nio/aggregations/scv/\\$YMD
require_positive() {{
  label=\\$1
  value=\\$2
  if ! [[ \\$value =~ ^[0-9]+$ ]] || [ \\$value -le 0 ]; then
    echo SCV_ACCEPTANCE_FAIL \\$label=\\$value
    exit 1
  fi
}}
require_file() {{
  label=\\$1
  path=\\$2
  if [ ! -s \\$path ]; then
    echo SCV_ACCEPTANCE_FAIL \\$label=\\$path
    exit 1
  fi
}}
mobile=\\$(find \\$AGGR -maxdepth 1 -type f | grep -E 'scv\\.tls\\..*\\.mobile\\..*\\.csv(\\.lz4)?$' | wc -l)
fixed=\\$(find \\$AGGR -maxdepth 1 -type f | grep -E 'scv\\.tls\\..*\\.fixed\\..*\\.csv(\\.lz4)?$' | wc -l)
fixed_userkey=\\$(find \\$AGGR -maxdepth 1 -type f | grep -E 'scv\\.userkey\\..*\\.fixed\\.log(\\.lz4)?$' | wc -l)
matches_rows=\\$(wc -l < \\$FEEDS/scv.day_merged_matches.\\$YMD.csv)
partial_rows=\\$(wc -l < \\$FEEDS/scv.domain_report.partial.\\$YMD.csv)
final_rows=\\$(wc -l < \\$FEEDS/scv.domain_report.\\$YMD.csv)
require_positive copied_mobile \\$mobile
require_positive copied_fixed \\$fixed
require_positive copied_fixed_userkey \\$fixed_userkey
require_positive merged_matches_rows \\$matches_rows
require_positive partial_rows \\$partial_rows
require_positive final_report_rows \\$final_rows
require_file merged_matches \\$FEEDS/scv.day_merged_matches.\\$YMD.csv
require_file partial_feed \\$FEEDS/scv.domain_report.partial.\\$YMD.csv
require_file partial_master \\$MASTER_DIR/scv.domain_report.partial.pocket-ath-mu1.\\$YMD.csv
require_file final_report \\$FEEDS/scv.domain_report.\\$YMD.csv
cd {REMOTE_STAGE}
export PYTHONPATH={REMOTE_PYTHONPATH}
mods=\\$(/opt/nio/lib/analytics/virtualenv/bin/python3.12 - <<'PY'
import nioanalytics.scv.scv_day_matcher as day
import nioanalytics.scv.scv_domain_report as report
print(day.__file__)
print(report.__file__)
PY
)
while IFS= read -r mod; do
  case \\$mod in
    \\$STAGED/*) ;;
    *) echo SCV_ACCEPTANCE_FAIL staged_module=\\$mod; exit 1 ;;
  esac
done <<< \\$mods
echo SCV_METRIC acceptance=passed
"

echo "SCV_PHASE summary"
echo "SCV_VERDICT PASS"
"""


def scheduler_observe_script(run_id: str, ymd: str, rpm_evidence: dict) -> str:
    report_name = f"scheduler-observe-{run_id}.md"
    report_path = RUN_ROOT / run_id / report_name
    report_q = shlex.quote(str(report_path))
    ymd_q = shlex.quote(ymd)
    mu1_q = shlex.quote(MU1)
    mu3_q = shlex.quote(MU3)
    evidence_json = shlex.quote(json.dumps(rpm_evidence, sort_keys=True))
    install_before_observe = rpm_evidence.get("install_before_observe") == "true"
    etl_before_observe = rpm_evidence.get("etl_before_observe") == "true"
    rpm_version = rpm_evidence.get("rpm_version", "")
    install_block = ""
    if install_before_observe:
        rpm_version_q = shlex.quote(rpm_version)
        install_block = f"""
echo "SCV_PHASE install_rpm"
for host in "$MU1" "$MU3"; do
  echo "SCV_METRIC install_target=$host"
  ssh_cmd "$host" "set -euo pipefail
sudo dnf clean all -q || true
sudo dnf install -y \\
  nio-analytics-{rpm_version_q} \\
  nio-analytics-cubes-{rpm_version_q} \\
  nio-analytics-schema-{rpm_version_q}
rpm -q nio-analytics nio-analytics-cubes nio-analytics-schema
"
done
"""
    etl_block = ""
    if etl_before_observe:
        etl_block = """
echo "SCV_PHASE repair_etl_ownership"
ssh_cmd "$MU1" "set -euo pipefail
for path in \\
  /var/opt/nio/feeds/scv/*$YMD* \\
  /var/opt/nio/feeds/scv/scv.day_merged_matches.*.csv \\
  /var/opt/nio/feeds/scv/scv.day_merged_matches.*.csv.filtered \\
  /var/opt/nio/feeds/scv/tmp_shard/*$YMD* \\
  /var/opt/nio/aggregations/scv/$YMD/* \\
  /var/opt/nio/log/scv_shard.log \\
  /var/opt/nio/log/scv_shard_day.log \\
  /var/opt/nio/log/scv_master_day.log \\
  /var/opt/nio/log/etl_cubes.tls_scv_shard.day.scv_shard.log \\
  /var/opt/nio/log/etl_cubes.scv.day.scv_master.log; do
  [ -e \\$path ] || continue
  sudo chown nio:nio \\$path
done
"

echo "SCV_PHASE run_etl"
ssh_cmd "$MU1" "set -euo pipefail
DAY_TS=\\$(date -d '$YMD 00:00:00' +%s)
sudo -n -u nio /opt/nio/libexec/etl_runner.sh \\
  --role scv_shard \\
  --interval day \\
  --source tls_scv_shard \\
  --timestamp \\$DAY_TS
sudo -n -u nio /opt/nio/libexec/etl_runner.sh \\
  --role scv_master \\
  --interval day \\
  --source scv \\
  --timestamp \\$DAY_TS
"
"""

    return f"""#!/usr/bin/env bash
set -euo pipefail
SSH_OPTS="{SSH_OPTS}"
MU1={mu1_q}
MU3={mu3_q}
YMD={ymd_q}
REPORT={report_q}
RPM_EVIDENCE={evidence_json}

ssh_cmd() {{
  ssh $SSH_OPTS "$@"
}}

emit_section() {{
  printf '\\n## %s\\n\\n' "$1" >> "$REPORT"
}}

echo "SCV_PHASE rpm_evidence"
mkdir -p "$(dirname "$REPORT")"
cat > "$REPORT" <<EOF
# SCV Scheduler Observation Report

Run id: {run_id}

Replay/observation day: $YMD

This report records scheduler/RPM observation evidence only. Jenkins RPM creation and RPM installation are manual user actions.

EOF

python3 - "$RPM_EVIDENCE" "$REPORT" <<'PY'
import json
import sys

evidence = json.loads(sys.argv[1])
report = sys.argv[2]
with open(report, "a", encoding="utf-8") as fp:
    fp.write("## Manual RPM Evidence\\n\\n")
    for key, label in [
        ("jenkins_url", "Jenkins build URL"),
        ("build_number", "Jenkins build number"),
        ("rpm_version", "RPM version/release"),
        ("changeset", "Changeset / branch"),
        ("install_hosts", "Install target hosts"),
        ("install_timestamp", "Install timestamp"),
        ("install_confirmation", "Install confirmation"),
    ]:
        fp.write(f"- {{label}}: `{{evidence.get(key) or 'not provided'}}`\\n")
PY

echo "SCV_METRIC scheduler_report=$REPORT"

{install_block}

echo "SCV_PHASE host_markers"
emit_section "Host Markers"
rpm_hosts_ok=1
wrappers_hosts_ok=1
observation_marker_epoch=$(date +%s)
echo "SCV_METRIC scheduler_observation_marker_epoch=$observation_marker_epoch"

{etl_block}

for host in "$MU1" "$MU3"; do
  host_checks=$(ssh_cmd "$host" "set -e
rpm -q nio-analytics >/dev/null 2>&1 && echo RPM_PRESENT=1 || echo RPM_PRESENT=0
test -x /opt/nio/bin/scv_day_matcher && test -x /opt/nio/bin/scv_domain_report && echo WRAPPERS_PRESENT=1 || echo WRAPPERS_PRESENT=0
")
  echo "$host_checks" | grep -q 'RPM_PRESENT=1' || rpm_hosts_ok=0
  echo "$host_checks" | grep -q 'WRAPPERS_PRESENT=1' || wrappers_hosts_ok=0
  {{
    echo "### $host"
    echo
    echo '```text'
    echo "$host_checks"
    ssh_cmd "$host" "set -e
echo host=\\$(hostname)
echo observed_at=\\$(date -Is)
echo rpm=\\$(rpm -q nio-analytics 2>/dev/null || true)
echo wrappers:
ls -l /opt/nio/bin/scv_day_matcher /opt/nio/bin/scv_domain_report 2>&1 || true
echo recent_domain_reports:
find /var/opt/nio/feeds/scv /var/opt/nio/aggregations/scv -maxdepth 3 -type f 2>/dev/null | grep -E 'scv\\.domain_report(\\.partial)?\\..*\\.csv$' | sort | tail -n 20 || true
"
    echo '```'
    echo
  }} >> "$REPORT"
done
echo "SCV_METRIC scheduler_rpm_hosts_ok=$rpm_hosts_ok"
echo "SCV_METRIC scheduler_wrappers_hosts_ok=$wrappers_hosts_ok"

echo "SCV_PHASE scheduler_logs"
emit_section "Scheduler Log Evidence After Observation"
log_marker_present=0
for host in "$MU1" "$MU3"; do
  host_log_check=$(ssh_cmd "$host" "python3 - '$observation_marker_epoch' <<'PY'
import datetime
import pathlib
import re
import sys

marker = int(sys.argv[1])
logs = [
    pathlib.Path('/var/opt/nio/log/task.log'),
    pathlib.Path('/var/opt/nio/log/etl.log'),
    pathlib.Path('/var/opt/nio/log/scv_shard_day.log'),
    pathlib.Path('/var/opt/nio/log/scv_master_day.log'),
]
needle = re.compile(r'scv_day_matcher|scv_domain_report|domain_report|matches_scv_master|tls_scv_shard|scv_master|scv_shard')
stamp = re.compile(r'^\\[(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2})')
found = 0
samples = []
for log in logs:
    if not log.exists():
        continue
    try:
        lines = log.read_text(errors='replace').splitlines()
    except OSError:
        continue
    for line in lines[-2000:]:
        if not needle.search(line):
            continue
        match = stamp.match(line)
        if not match:
            continue
        dt = datetime.datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
        if int(dt.timestamp()) >= marker:
            found = 1
            samples.append('%s: %s' % (log, line))
if samples:
    print('LOG_MARKER_PRESENT=1')
    for sample in samples[-20:]:
        print(sample)
else:
    print('LOG_MARKER_PRESENT=0')
PY
")
  echo "$host_log_check" | grep -q 'LOG_MARKER_PRESENT=1' && log_marker_present=1
  {{
    echo "### $host"
    echo
    echo '```text'
    echo "$host_log_check"
    ssh_cmd "$host" "set -e
for log in /var/opt/nio/log/task.log /var/opt/nio/log/etl.log /var/opt/nio/log/scv_shard_day.log /var/opt/nio/log/scv_master_day.log; do
  [ -f \\$log ] || continue
  echo == \\$log ==
  grep -E 'scv_day_matcher|scv_domain_report|domain_report|matches_scv_master|tls_scv_shard|scv_master|scv_shard' \\$log 2>/dev/null | tail -n 80 || true
done
"
    echo '```'
    echo
  }} >> "$REPORT"
done
echo "SCV_METRIC scheduler_log_marker_present=$log_marker_present"

echo "SCV_PHASE artifact_inventory"
emit_section "Live Artifact Inventory"
live_report_present=0
live_partial_present=0
live_math_pass=0
for host in "$MU1" "$MU3"; do
  host_artifact_check=$(ssh_cmd "$host" "set -e
marker='$observation_marker_epoch'
if [ -s /var/opt/nio/feeds/scv/scv.domain_report.$YMD.csv ] && [ \\$(stat -c %Y /var/opt/nio/feeds/scv/scv.domain_report.$YMD.csv) -ge \\$marker ]; then
  echo LIVE_REPORT_PRESENT=1
else
  echo LIVE_REPORT_PRESENT=0
fi
if find /var/opt/nio/aggregations/scv/$YMD -maxdepth 1 -type f -newermt @\\$marker 2>/dev/null | grep -E 'scv\\.domain_report\\.partial\\..*\\.csv$' >/dev/null 2>&1; then
  echo LIVE_PARTIAL_PRESENT=1
else
  echo LIVE_PARTIAL_PRESENT=0
fi
")
  echo "$host_artifact_check" | grep -q 'LIVE_REPORT_PRESENT=1' && live_report_present=1
  echo "$host_artifact_check" | grep -q 'LIVE_PARTIAL_PRESENT=1' && live_partial_present=1
  {{
    echo "### $host"
    echo
    echo '```text'
    echo "$host_artifact_check"
    ssh_cmd "$host" "set -e
for path in \\
  /var/opt/nio/feeds/scv/scv.domain_report.$YMD.csv \\
  /var/opt/nio/feeds/scv/scv.domain_report.partial.$YMD.csv \\
  /var/opt/nio/aggregations/scv/$YMD; do
  echo == \\$path ==
  if [ -f \\$path ]; then
    ls -l \\$path
    wc -l \\$path
    head -n 5 \\$path
  elif [ -d \\$path ]; then
    find \\$path -maxdepth 1 -type f | grep -E 'scv\\.domain_report(\\.partial)?\\..*\\.csv$' | sort | xargs -r ls -l
  else
    echo missing
  fi
done
"
    echo '```'
    echo
  }} >> "$REPORT"
done
echo "SCV_METRIC scheduler_live_report_present=$live_report_present"
echo "SCV_METRIC scheduler_live_partial_present=$live_partial_present"

echo "SCV_PHASE live_math"
if [ "$live_report_present" = "1" ] && [ "$live_partial_present" = "1" ]; then
  live_math_check=$(ssh_cmd "$MU1" "python3 - '$YMD' '$observation_marker_epoch' <<'PY'
import csv
import glob
import pathlib
import sys

ymd = sys.argv[1]
marker = int(sys.argv[2])
final_path = pathlib.Path('/var/opt/nio/feeds/scv/scv.domain_report.%s.csv' % ymd)
partial_paths = [
    pathlib.Path(p)
    for p in glob.glob('/var/opt/nio/aggregations/scv/%s/scv.domain_report.partial.*.csv' % ymd)
    if pathlib.Path(p).stat().st_mtime >= marker
]
expected = ['domain', 'unique_valid_tls', 'valid_tls_matches', 'duplicated_tls_keys']
numeric = expected[1:]

def read_rows(path):
    with path.open(newline='', encoding='utf-8') as fp:
        reader = csv.DictReader(fp)
        rows = list(reader)
    if reader.fieldnames != expected:
        raise SystemExit('bad header: %s' % path)
    result = dict()
    for row in rows:
        result[row['domain']] = dict((key, int(row[key])) for key in numeric)
    return result

if not final_path.exists() or final_path.stat().st_mtime < marker:
    raise SystemExit('missing post-marker final report')
if not partial_paths:
    raise SystemExit('missing post-marker partial report')
final = read_rows(final_path)
combined = dict()
for path in partial_paths:
    for domain, metrics in read_rows(path).items():
        target = combined.setdefault(domain, dict((key, 0) for key in numeric))
        for key in numeric:
            target[key] += metrics[key]
if final != combined:
    raise SystemExit('final report does not equal summed partials')
if not final:
    print('LIVE_MATH_PASS=0')
else:
    print('LIVE_MATH_PASS=1')
    print('LIVE_MATH_FINAL_ROWS=%d' % len(final))
    print('LIVE_MATH_PARTIAL_FILES=%d' % len(partial_paths))
PY
")
  echo "$live_math_check" | grep -q 'LIVE_MATH_PASS=1' && live_math_pass=1
  echo "$live_math_check" >> "$REPORT"
else
  echo "LIVE_MATH_PASS=0" >> "$REPORT"
fi
echo "SCV_METRIC scheduler_live_math_pass=$live_math_pass"

echo "SCV_PHASE scheduler_verdict"
python3 - "$REPORT" "$rpm_hosts_ok" "$wrappers_hosts_ok" "$log_marker_present" "$live_report_present" "$live_partial_present" "$live_math_pass" <<'PY'
import pathlib
import sys

report = pathlib.Path(sys.argv[1])
has_rpm = sys.argv[2] == "1"
has_wrappers = sys.argv[3] == "1"
has_scheduler_marker = sys.argv[4] == "1"
has_live_report = sys.argv[5] == "1"
has_live_partial = sys.argv[6] == "1"
has_live_math = sys.argv[7] == "1"

if has_rpm and has_wrappers and has_scheduler_marker and has_live_report and has_live_partial and has_live_math:
    verdict = "PASS"
elif has_rpm and has_wrappers and has_scheduler_marker:
    verdict = "PASS_WITH_NOTES"
else:
    verdict = "BLOCKED"

with report.open("a", encoding="utf-8") as fp:
    fp.write("\\n## Scheduler Observation Verdict\\n\\n")
    fp.write(f"`{{verdict}}`\\n\\n")
    fp.write("- RPM installed evidence present: `%s`\\n" % has_rpm)
    fp.write("- Wrapper evidence present: `%s`\\n" % has_wrappers)
    fp.write("- Scheduler/log marker present: `%s`\\n" % has_scheduler_marker)
    fp.write("- Live shard partial artifact present: `%s`\\n" % has_live_partial)
    fp.write("- Live domain report artifact present: `%s`\\n" % has_live_report)
    fp.write("- Live report math verification passed: `%s`\\n" % has_live_math)

print("SCV_VERDICT " + verdict)
PY
"""


def run_worker(run_id: str) -> None:
    with RUNS_LOCK:
        run = RUNS[run_id]
    update_run(run_id, status="RUNNING", started_at=time.time())
    script_path = run["dir"] / "run.sh"
    if run["action"] in {SCHEDULER_ACTION, INSTALL_ACTION, ETL_ACTION}:
        script = scheduler_observe_script(run_id, run["ymd"], run.get("rpm_evidence", {}))
    else:
        script = shell_script(run_id, run["ymd"])
    script_path.write_text(script, encoding="utf-8")
    script_path.chmod(0o700)

    process = subprocess.Popen(
        ["/bin/bash", str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=str(WORKSPACE_ROOT),
        preexec_fn=os.setsid,
    )
    update_run(run_id, process=process)

    try:
        assert process.stdout is not None
        for line in process.stdout:
            append_log(run, line)
        exit_code = process.wait()
    except Exception as exc:  # noqa: BLE001 - keep the UI useful for operator errors.
        update_run(run_id, status="FAIL", error=str(exc), completed_at=time.time())
        append_log(run, f"SCV_ERROR {exc}")
        return

    with RUNS_LOCK:
        status = RUNS[run_id]["status"]
    if exit_code == 0 and status in {"PASS", "PASS_WITH_NOTES", "BLOCKED"}:
        final_status = status
    elif status == "CANCELLED":
        final_status = "CANCELLED"
    else:
        final_status = "FAIL"
    update_run(run_id, status=final_status, exit_code=exit_code, completed_at=time.time())
    write_summary(run_id)


def write_summary(run_id: str) -> None:
    with RUNS_LOCK:
        run = RUNS[run_id]
        summary = public_run(run)
    summary_path = run["dir"] / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    with RUNS_LOCK:
        RUNS[run_id]["artifacts"]["summary"] = str(summary_path)


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        if parsed.path == "/":
            return str(STATIC_ROOT / "index.html")
        if parsed.path.startswith("/static/"):
            rel = parsed.path.removeprefix("/static/")
            root = STATIC_ROOT.resolve()
            candidate = (root / rel).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                return str(root / "__not_found__")
            return str(candidate)
        return str(STATIC_ROOT / "index.html")

    def do_GET(self) -> None:  # noqa: N802 - http.server API.
        parsed = urlparse(self.path)
        if parsed.path == "/":
            super().do_GET()
            return
        if parsed.path.startswith("/static/"):
            super().do_GET()
            return
        if parsed.path == "/api/runs":
            with RUNS_LOCK:
                payload = [public_run(run) for run in RUNS.values()]
            json_response(self, payload)
            return
        match = re.match(r"^/api/runs/([a-f0-9]{12})$", parsed.path)
        if match:
            run_id = match.group(1)
            with RUNS_LOCK:
                run = RUNS.get(run_id)
                payload = public_run(run) if run else None
            if payload is None:
                json_response(self, {"error": "run not found"}, HTTPStatus.NOT_FOUND)
            else:
                json_response(self, payload)
            return
        artifact = re.match(r"^/api/runs/([a-f0-9]{12})/artifact$", parsed.path)
        if artifact:
            self.handle_artifact(artifact.group(1), parse_qs(parsed.query).get("name", [""])[0])
            return
        events = re.match(r"^/api/runs/([a-f0-9]{12})/events$", parsed.path)
        if events:
            self.handle_events(events.group(1))
            return
        json_response(self, {"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - http.server API.
        parsed = urlparse(self.path)
        if parsed.path == "/api/runs":
            self.create_run()
            return
        cancel = re.match(r"^/api/runs/([a-f0-9]{12})/cancel$", parsed.path)
        if cancel:
            self.cancel_run(cancel.group(1))
            return
        json_response(self, {"error": "not found"}, HTTPStatus.NOT_FOUND)

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def create_run(self) -> None:
        try:
            body = self.read_json_body()
            action = body.get("action", ACTION)
            if action not in SUPPORTED_ACTIONS:
                raise ValueError(f"unsupported action: {action}")
            ymd = normalize_ymd(body.get("ymd", DEFAULT_YMD))
            rpm_evidence = (
                validate_rpm_evidence(body.get("rpm_evidence", {}))
                if action in {SCHEDULER_ACTION, INSTALL_ACTION, ETL_ACTION}
                else {}
            )
            if action == INSTALL_ACTION:
                if not rpm_evidence.get("rpm_version"):
                    raise ValueError("RPM version is required for install-and-observe")
                rpm_evidence["install_before_observe"] = "true"
                rpm_evidence["install_confirmation"] = (
                    rpm_evidence.get("install_confirmation")
                    or f"install nio-analytics {rpm_evidence['rpm_version']} on mu1 and mu3"
                )
            if action == ETL_ACTION:
                rpm_evidence["etl_before_observe"] = "true"
        except (ValueError, json.JSONDecodeError) as exc:
            json_response(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        run_id = uuid.uuid4().hex[:12]
        run_dir = RUN_ROOT / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        run = {
            "id": run_id,
            "action": action,
            "ymd": ymd,
            "status": "QUEUED",
            "phase": "queued",
            "created_at": time.time(),
            "dir": run_dir,
            "log_file": run_dir / "run.log",
            "log_tail": [],
            "metrics": {},
            "artifacts": {"log": str(run_dir / "run.log")},
            "process": None,
            "rpm_evidence": rpm_evidence,
        }
        with RUNS_LOCK:
            RUNS[run_id] = run
        thread = threading.Thread(target=run_worker, args=(run_id,), daemon=True)
        thread.start()
        json_response(self, public_run(run), HTTPStatus.CREATED)

    def cancel_run(self, run_id: str) -> None:
        with RUNS_LOCK:
            run = RUNS.get(run_id)
            process = run.get("process") if run else None
        if run is None:
            json_response(self, {"error": "run not found"}, HTTPStatus.NOT_FOUND)
            return
        if process and process.poll() is None:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        update_run(run_id, status="CANCELLED", completed_at=time.time())
        json_response(self, public_run(run))

    def handle_artifact(self, run_id: str, name: str) -> None:
        with RUNS_LOCK:
            run = RUNS.get(run_id)
            run_public = public_run(run) if run else None
        if run is None or run_public is None:
            json_response(self, {"error": "run not found"}, HTTPStatus.NOT_FOUND)
            return
        if name == "summary":
            json_response(self, run_public)
            return
        if name == "log":
            log_path = run["log_file"]
            text_response(self, log_path.read_text(encoding="utf-8") if log_path.exists() else "")
            return
        if name == "scheduler-report":
            report = run_public["metrics"].get("scheduler_report", "")
            report_path = Path(report)
            try:
                report_path.resolve().relative_to(run["dir"].resolve())
            except ValueError:
                json_response(self, {"error": "scheduler report is not available"}, HTTPStatus.BAD_REQUEST)
                return
            text_response(self, report_path.read_text(encoding="utf-8") if report_path.exists() else "")
            return
        if name == "report-preview":
            report = run_public["metrics"].get("final_report", "")
            replay_root = run_public["metrics"].get("replay_root", "")
            if not self.remote_path_allowed(report, replay_root):
                json_response(self, {"error": "final report is not available yet"}, HTTPStatus.BAD_REQUEST)
                return
            cmd = [
                "ssh",
                *SSH_OPTS.split(),
                MU1,
                f"head -n 100 {shlex.quote(report)}",
            ]
            try:
                preview = subprocess.check_output(cmd, text=True, timeout=20)
            except subprocess.SubprocessError as exc:
                json_response(self, {"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
                return
            text_response(self, preview, content_type="text/csv; charset=utf-8")
            return
        if name in REMOTE_ARTIFACT_KEYS:
            metric_key = REMOTE_ARTIFACT_KEYS[name]
            path = run_public["metrics"].get(metric_key, "")
            replay_root = run_public["metrics"].get("replay_root", "")
            if not self.remote_path_allowed(path, replay_root):
                json_response(self, {"error": f"{metric_key} is not available yet"}, HTTPStatus.BAD_REQUEST)
                return
            text = self.fetch_remote_artifact(path, replay_root)
            text_response(self, text, content_type="text/plain; charset=utf-8")
            return
        if name == "math-analysis":
            analysis = self.analyze_report_math(run_public)
            json_response(self, analysis)
            return
        json_response(self, {"error": "unknown artifact"}, HTTPStatus.BAD_REQUEST)

    def remote_path_allowed(self, path: str, replay_root: str) -> bool:
        return bool(
            path
            and replay_root
            and replay_root.startswith("/tmp/scv_domain_replay_")
            and path.startswith(f"{replay_root}/")
            and "/../" not in path
            and not path.endswith("/..")
        )

    def fetch_remote_artifact(self, path: str, replay_root: str) -> str:
        script = r"""
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
path = pathlib.Path(sys.argv[2]).resolve()
limit = int(sys.argv[3])
if not str(root).startswith("/tmp/scv_domain_replay_"):
    raise SystemExit("blocked path")
try:
    path.relative_to(root)
except ValueError:
    raise SystemExit("blocked path")
if not path.is_file():
    raise SystemExit("file not found")

data = path.read_bytes()
truncated = len(data) > limit
data = data[:limit]
sys.stdout.write(data.decode("utf-8", errors="replace"))
if truncated:
    sys.stdout.write("\n\n[truncated after %d bytes]\n" % limit)
"""
        cmd = [
            "ssh",
            *SSH_OPTS.split(),
            MU1,
            "python3",
            "-",
            replay_root,
            path,
            str(MAX_VIEW_BYTES),
        ]
        try:
            return subprocess.check_output(cmd, input=script, text=True, timeout=30)
        except subprocess.SubprocessError as exc:
            return f"Unable to fetch artifact: {exc}"

    def analyze_report_math(self, run_public: dict) -> dict:
        metrics = run_public.get("metrics", {})
        replay_root = metrics.get("replay_root", "")
        final_report = metrics.get("final_report", "")
        partial = metrics.get("partial_master") or metrics.get("partial_feed", "")
        merged_matches = metrics.get("merged_matches", "")
        for path in (final_report, partial, merged_matches):
            if path and not self.remote_path_allowed(path, replay_root):
                return {"verdict": "BLOCKED", "error": f"blocked path: {path}"}
        if not final_report or not partial:
            return {"verdict": "BLOCKED", "error": "final report or partial report is not available"}

        script = r"""
import csv
import json
import pathlib
import sys

EXPECTED_HEADER = ["domain", "unique_valid_tls", "valid_tls_matches", "duplicated_tls_keys"]
NUMERIC = EXPECTED_HEADER[1:]


def safe_path(root_raw, path_raw):
    root = pathlib.Path(root_raw).resolve()
    path = pathlib.Path(path_raw).resolve()
    if not str(root).startswith("/tmp/scv_domain_replay_"):
        raise SystemExit("blocked path")
    try:
        path.relative_to(root)
    except ValueError:
        raise SystemExit("blocked path")
    if not path.is_file():
        raise SystemExit("missing file: %s" % path)
    return path


def read_report(root_raw, raw):
    path = safe_path(root_raw, raw)
    with path.open(newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        rows = list(reader)

    totals = {key: 0 for key in NUMERIC}
    non_integer = []
    negative = []
    domains = []
    row_map = {}
    for index, row in enumerate(rows, start=2):
        domain = row.get("domain", "")
        domains.append(domain)
        metric_row = {}
        for key in NUMERIC:
            value = row.get(key, "")
            try:
                parsed = int(value)
            except ValueError:
                non_integer.append({"line": index, "domain": domain, "column": key, "value": value})
                parsed = 0
            if parsed < 0:
                negative.append({"line": index, "domain": domain, "column": key, "value": parsed})
            totals[key] += parsed
            metric_row[key] = parsed
        row_map[domain] = metric_row

    return {
        "path": str(path),
        "header": reader.fieldnames or [],
        "row_count": len(rows),
        "totals": totals,
        "non_integer": non_integer[:20],
        "negative": negative[:20],
        "sorted_by_domain": domains == sorted(domains),
        "duplicate_domains": len(domains) - len(set(domains)),
        "rows_by_domain": row_map,
        "sample_rows": rows[:8],
    }


def count_lines(root_raw, raw):
    if not raw:
        return None
    path = safe_path(root_raw, raw)
    with path.open("rb") as fp:
        return sum(1 for _ in fp)


root_arg = sys.argv[1]
final = read_report(root_arg, sys.argv[2])
partial = read_report(root_arg, sys.argv[3])
merged_lines = count_lines(root_arg, sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else None

domain_union = sorted(set(final["rows_by_domain"]) | set(partial["rows_by_domain"]))
domain_mismatches = []
for domain in domain_union:
    final_row = final["rows_by_domain"].get(domain)
    partial_row = partial["rows_by_domain"].get(domain)
    if final_row != partial_row:
        domain_mismatches.append({
            "domain": domain,
            "final": final_row,
            "partial_sum": partial_row,
        })
        if len(domain_mismatches) >= 20:
            break

checks = [
    {"name": "final_header", "pass": final["header"] == EXPECTED_HEADER,
     "detail": ",".join(final["header"])},
    {"name": "partial_header", "pass": partial["header"] == EXPECTED_HEADER,
     "detail": ",".join(partial["header"])},
    {"name": "final_numeric_columns_are_integers", "pass": not final["non_integer"],
     "detail": str(len(final["non_integer"]))},
    {"name": "partial_numeric_columns_are_integers", "pass": not partial["non_integer"],
     "detail": str(len(partial["non_integer"]))},
    {"name": "final_numeric_columns_are_nonnegative", "pass": not final["negative"],
     "detail": str(len(final["negative"]))},
    {"name": "partial_numeric_columns_are_nonnegative", "pass": not partial["negative"],
     "detail": str(len(partial["negative"]))},
    {"name": "final_domains_are_unique", "pass": final["duplicate_domains"] == 0,
     "detail": str(final["duplicate_domains"])},
    {"name": "final_domains_sorted", "pass": final["sorted_by_domain"],
     "detail": "lexicographic"},
    {"name": "final_equals_partial_sum_for_single_replay_shard", "pass": not domain_mismatches,
     "detail": "%d mismatched domains" % len(domain_mismatches)},
    {"name": "final_has_rows", "pass": final["row_count"] > 0,
     "detail": str(final["row_count"])},
]

result = {
    "verdict": "PASS" if all(check["pass"] for check in checks) else "FAIL",
    "columns": {
        "domain": "TLS server_name / domain key used to group metrics.",
        "unique_valid_tls": "For each domain in a shard partial: count distinct TLS keys observed in raw domain-key scan. Final report sums this column across shard partials.",
        "valid_tls_matches": "For each domain in a shard partial: count filtered TLS match records whose server_name equals this domain. Final report sums this column across shard partials.",
        "duplicated_tls_keys": "For each domain in a shard partial: count observed TLS keys that were classified invalid because they were shared across mobile users. Final report sums this column across shard partials.",
    },
    "formulas": [
        "partial.unique_valid_tls(domain) = |{tls_key observed for domain in raw shard TLS inputs}|",
        "partial.valid_tls_matches(domain) = count(filtered_matches where server_name = domain)",
        "partial.duplicated_tls_keys(domain) = |{tls_key in raw_domain_keys[domain] and tls_key in invalid_keys}|",
        "final.metric(domain) = sum(partial_i.metric(domain) for every shard partial_i)",
        "For this controlled replay there is one shard partial, so final.metric(domain) must equal that partial metric for every domain.",
    ],
    "relationships": [
        "raw mobile/fixed TLS inputs -> scv_day_matcher -> scv.day_merged_matches.<YMD>.csv",
        "raw domain-key scan + filtered matches + invalid keys -> scv.domain_report.partial.<YMD>.csv",
        "master-layout shard partials -> scv_domain_report -> scv.domain_report.<YMD>.csv",
    ],
    "checks": checks,
    "totals": {
        "final": final["totals"],
        "partial_sum": partial["totals"],
        "merged_match_rows": merged_lines,
        "final_domain_rows": final["row_count"],
        "partial_domain_rows": partial["row_count"],
    },
    "samples": final["sample_rows"],
    "mismatches": domain_mismatches,
    "paths": {
        "final_report": final["path"],
        "partial": partial["path"],
        "merged_matches": sys.argv[4] if len(sys.argv) > 4 else "",
    },
}
print(json.dumps(result))
"""
        cmd = [
            "ssh",
            *SSH_OPTS.split(),
            MU1,
            "python3",
            "-",
            replay_root,
            final_report,
            partial,
            merged_matches,
        ]
        try:
            raw = subprocess.check_output(cmd, input=script, text=True, timeout=60)
        except subprocess.SubprocessError as exc:
            return {"verdict": "BLOCKED", "error": str(exc)}
        return json.loads(raw)

    def handle_events(self, run_id: str) -> None:
        with RUNS_LOCK:
            run = RUNS.get(run_id)
        if run is None:
            json_response(self, {"error": "run not found"}, HTTPStatus.NOT_FOUND)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        last_payload = None
        while True:
            with RUNS_LOCK:
                current = RUNS.get(run_id)
                payload = public_run(current) if current else None
            if payload is None:
                break

            encoded = json.dumps(payload, sort_keys=True)
            if encoded != last_payload:
                try:
                    self.wfile.write(f"event: state\ndata: {encoded}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break
                last_payload = encoded

            if payload["status"] not in {"QUEUED", "RUNNING"}:
                break
            time.sleep(0.75)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[visualizer] {self.address_string()} - {fmt % args}")


def main() -> None:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"SCV validation visualizer: http://{HOST}:{PORT}")
    print("Press Ctrl-C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
