
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

# Mobileum Workspace Agent Routing

This workspace keeps reusable NIO guidance under `.agents/skills`,
`.agents/subagents`, `.github/agents`, and `.cursor/agents`.

## Local Guidance Surfaces

- For broad NIO/Mobileum work, read `.agents/skills/nio-workspace/SKILL.md`
  before planning repo changes.
- For `nio-analytics` build, autotools, rbuild, or RPM packaging issues, read
  `.agents/skills/nio-autotools-rbuild-rpm/SKILL.md`.
- For installed pocket-host ETL checks, role/source/interval file inspection, or
  `etl_runner` operations, read `.agents/skills/nio-analytics-explorer/SKILL.md`;
  default to read-only SSH evidence first and require explicit confirmation
  before any trigger or write action.
- `.agents/subagents/*.md` are plain read-only helper prompts. Pass the relevant
  prompt contents to a helper agent, then append the concrete task; keep each
  helper scoped to the repositories listed in that prompt.
- `.github/agents/nio-etl-pipeline.agent.md` captures GitHub Copilot-style
  guidance for `nio-analytics` ETL pipeline work, including task scheduling,
  pipeline step ordering, MRS signaling, and build/test commands.


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

## Default-Branch Sync

- For clean-start or "latest repo" checks in these linked worktrees, verify the
  live canonical default branch over HTTPS before trusting cached tracking refs:
  `git ls-remote --symref https://github.com/phutran2495-cpu/nio-helper-tools.git HEAD refs/heads/main`.
- If the SSH `upstream` remote stalls during fetch, fetch only the canonical
  branch over HTTPS:
  `git fetch https://github.com/phutran2495-cpu/nio-helper-tools.git main:refs/remotes/upstream/main`.
- If another linked worktree already owns `main`, keep this checkout detached at
  the verified default-branch commit with `git checkout --detach <commit>` and
  preserve unrelated local state such as the OMX `.gitignore` entry.

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
=======
- For clean-start or "latest repo" checks in these linked worktrees, verify the
  live default branch before trusting cached refs:
  `git ls-remote --symref origin HEAD refs/heads/main`, then
  `git fetch origin --prune --tags`. If another linked worktree owns `main`,
  keep this checkout detached at `origin/main` instead of disturbing that
  worktree.
- For the SCV validation visualizer, run
  `python3 server.py` from
  `/Volumes/vidzdatastore/work/mobileum_source/nio-analytics/offline/scv-validation-visualizer`
  and open `http://127.0.0.1:8765`. Treat `Install RPM + Observe` and
  `Run ETL + Observe` as mutating operations on pocket hosts.
- To generate fixed-broadband OTTCall IPDR test files from this repo, run
  `python3 generate_fake_fixed_ottcall.py --output-dir ./fake_fixed_ipdr`.
  It writes schema `15109` files named `ipdr_cib_fixed.log.<interval>`; confirm
  the target host before copying them into `/var/opt/nio/log/raw/`.
- For `nio-conf-templates` validation, follow
  `nio-conf-templates-validation-guide.md`. Treat
  `sudo yum update nio-conf-templates -y`,
  `sudo /opt/nio/bin/conf sync`, and `sudo systemctl restart ncore` as mutating
  operations; prefer `sudo /opt/nio/bin/conf regenerate --diff` for previewing
  rendered config changes.

## Access And Pocket Probes

- For private Mobileum repos under `mobeande/*`, check
  `gh auth status -h github.com` before concluding the repo is missing. If
  `vidz231` cannot see the repo, switch to `Tran-Phu_Mobileum` for the check
  and restore the previous active account afterward.
- When SSH fetches fail with `Permission denied (publickey)` or hang through
  the 1Password SSH-agent path, use a one-off HTTPS fallback:
  `git -c credential.helper='!gh auth git-credential' -c url."https://github.com/".insteadOf=git@github.com: fetch --prune --tags origin`.
- For pocket-host access checks, separate DNS, port, and auth before debugging
  deeper runtime behavior:
  `dscacheutil -q host -a name <host>.niometrics.com`,
  `nc -vz -G 5 <host>.niometrics.com 22`, then
  `ssh -i ~/.ssh/id_rsa phu.tran@<host>.niometrics.com 'hostname && date && id -un'`.
- Before live `conf-edit` work, inspect `/etc/opt/nio/analytics.json` and
  `sudo conf show`; derive the edit path from the deployed JSON instead of
  guessing. Treat `conf-edit`, `conf apply`, and `conf regenerate` as mutating
  unless the user explicitly approved that action.

## OTTCall And DNA-15382 Notes

- For mixed FBB/MBB OTTCall impact analysis, keep slide-backed requirements,
  current runtime facts, and proposed implementation design separate. If the
  user narrows scope to `nio-analytics` and `nio-conf-templates`, exclude
  `nio-api3` until they explicitly re-add it.
- First scoped anchors: `resources/etl/ncore/cubes/unit/ottcall`,
  `resources/etl/mrs/cubes/unit/ottcall`,
  `py3/src/lib/python3/nioanalytics/analytics/correlate_ottcall_v3.py`, plus
  `conf-templates.d/ipdr.conf`, `conf-templates.d/nstored.conf.shared`,
  `conf-templates.d/nstore.conf.tmpl`, `conf-templates.d/nstore_ipdr.conf.tmpl`,
  and `conf-templates.d/eventlog.njoin.json.tmpl`.
- TODO: Document the mixed FBB/MBB MRS replay helper
  `generate_ncore_ottcall_mrs.py` only after the script and its artifact
  contract are committed on the target branch. Current evidence came from local
  feature artifacts, not live `main`.

For Mobileum and NIO tasks in `/Volumes/vidzdatastore/work/mobileum_source`, prefer `mobileum_coordinator` as the default entrypoint unless the user explicitly asks for a narrower agent by name.

## Direct Mention Routing

- Treat a direct mention such as `[@mobileum_coordinator](subagent://mobileum_coordinator)` as an explicit instruction to invoke that exact custom agent name.
- When a named custom agent exists in `.codex/agents`, do not substitute a built-in `default`, `worker`, or `explorer` agent for that handoff.
- Use the canonical custom agent name for invocation and reporting. Do not rewrite it to a friendly alias for this workspace.

## Runtime Compatibility

- In environments where the available `spawn_agent` tool cannot select workspace custom agent names directly and only exposes built-in roles, emulate the requested custom agent by spawning a single built-in `default` agent and pasting the matching custom agent instructions from `.codex/agents/<name>.toml` into that agent's task prompt.
- In that compatibility mode, still treat the requested custom agent name as the source of truth for routing, sequencing, and reporting.
- Do not report that the custom agent is unavailable merely because the spawn tool only accepts built-in roles. Fall back to the compatibility pattern above instead.

## Execution Order

- Coordinated Mobileum flows must run sequentially, with at most one active spawned agent at a time.
- Finish navigator discovery before handing work to the specialist or QE agent that depends on it.
- Finish the specialist or QE step before invoking `solution_auditor`.
- Do not run `solution_auditor` in parallel with any other agent.

## Routing Rules

- Solution design, architecture, impact analysis, or requests such as "create solution design":
  route to `mobileum_coordinator`, then sequentially use the relevant repo navigator agents, `solution_designer`, and `solution_auditor`.
- Build-validation requests, or requests such as "Rbuild test":
  route to `mobileum_coordinator`, then sequentially use `rbuild_navigator`, any affected repo navigators, `rbuild_qe`, and `solution_auditor`.
- Package-validation requests, or requests such as "RPM test":
  route to `mobileum_coordinator`, then sequentially use the affected repo navigators, `rbuild_navigator` when build workflow matters, `nio_build_deps_navigator` when packaging dependencies matter, `rpm_qe`, and `solution_auditor`.
- General implementation, bug-fix, and code-change requests:
  route to `mobileum_coordinator`, then sequentially use the relevant repo navigator agents, `mobileum_engineer`, and `solution_auditor`.

## Completion Gate

- `solution_auditor` is mandatory before coordinated work is considered complete.
- Allowed auditor verdicts are `PASS`, `PASS_WITH_NOTES`, and `BLOCKED`.
- `mobileum_coordinator` may only close a task on `PASS` or `PASS_WITH_NOTES`.
- `BLOCKED` stops completion. The coordinator must return the blocking issues and the next required action.

## Repo Navigator Use

- Navigator agents are read-only and repo-scoped.
- Each navigator should stay within its assigned repo unless another repo is needed to explain a direct dependency.
- Use the smallest set of navigators needed for the task.
- When more than one navigator is required, invoke them one at a time in dependency order instead of running them in parallel.

## Available Custom Agents

- Core: `mobileum_coordinator`, `solution_designer`, `solution_auditor`, `mobileum_engineer`, `rbuild_qe`, `rpm_qe`
- Navigators: `nio_analytics_navigator`, `nio_analytics_c_tools_navigator`, `nio_api3_navigator`, `nio_base_navigator`, `nio_build_deps_navigator`, `nio_python_libs_navigator`, `nio_python3_libs_navigator`, `nio_storage_navigator`, `nio_virtualenv_python_navigator`, `rbuild_navigator`

