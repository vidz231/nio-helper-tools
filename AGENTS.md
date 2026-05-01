# NIO Helper Tools Agent Notes

This repository stores private guidance for NIO/Mobileum work: Codex skills,
Cursor/GitHub agent prompts, SCV troubleshooting runbooks, and the SCV validation
visualizer source. Keep guidance edits small, factual, and tied to files in this
repo.

## Local Guidance Surfaces

- For broad NIO workspace work, read `.agents/skills/nio-workspace/SKILL.md`
  before planning changes across `nio-analytics`, `nio-api3`, `nio-base`,
  `nio-python3-libs`, `nio-analytics-c-tools`, or related repos.
- For `nio-analytics` autotools, `configure.ac`, `Makefile.am`, py3 install,
  rbuild, or RPM packaging issues, use
  `.agents/skills/nio-autotools-rbuild-rpm/SKILL.md`.
- For deployed pocket-host ETL checks, role/source/interval file inspection,
  SCV shard/master artifact validation, logs, or `etl_runner` operations, use
  `.agents/skills/nio-analytics-explorer/SKILL.md`; start with read-only SSH
  evidence and require explicit confirmation before remote triggers or writes.
- `.github/agents/nio-etl-pipeline.agent.md` captures ETL pipeline guidance for
  task scheduling, pipeline step order, MRS signaling, and build/test commands.
- `.cursor/agents/nio-coordinator.md` captures the cross-repo coordinator flow
  for routing NIO work, dependency-aware build order, and operational
  checklists.
- Use `.agents/skills/skill-creator/SKILL.md` and its scripts when changing or
  evaluating skills in this repo.

## Common Commands

- From `/Volumes/vidzdatastore/work/mobileum_source`, use
  `./rbuild.sh <repo> -sb` for the normal stage-and-build loop,
  `./rbuild.sh <repo> -sAab` after configure/autotools changes, and
  `./rbuild.sh <repo> -t` for tests.
- For installed NIO runtimes, primary logs live under `/var/opt/nio/log/`.
  Start SCV incident checks with `task.log`, `scv_shard_unit.log`,
  `scv_shard_day.log`, `scv_master_day.log`, and `etl.log` as described in
  `docs/scv/scv-logs-and-troubleshooting.md`.
- Use `/opt/nio/libexec/etl_runner.sh` as the main deployed ETL trigger surface
  when a rerun is explicitly intended. Verify retained inputs first; do not
  promise historical reruns before checking retention.

## SCV Workflows

- For SCV drops or missing reports, start at `docs/scv/README.md`, then use
  `docs/scv/scv-step-io-reference.md` to map the expected shard/master inputs,
  outputs, and handoffs for the target date.
- Treat a successful master `scv` day audit as necessary but not sufficient:
  still verify shard copy coverage and report-path artifacts before concluding
  the pipeline was complete.
- The SCV validation visualizer is documented in
  `scv-validation-visualizer/README.md`. Its runtime assumptions expect it to
  run from the `nio-analytics/offline/scv-validation-visualizer` location in the
  Mobileum source workspace:
  `python3 server.py`, then open `http://127.0.0.1:8765`.
- Visualizer actions named `Install RPM + Observe` and `Run ETL + Observe`
  mutate pocket hosts. Treat them as remote operational actions, not read-only
  diagnostics.
