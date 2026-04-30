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
- For the SCV validation visualizer, run
  `python3 server.py` from
  `/Volumes/vidzdatastore/work/mobileum_source/nio-analytics/offline/scv-validation-visualizer`
  and open `http://127.0.0.1:8765`. Treat `Install RPM + Observe` and
  `Run ETL + Observe` as mutating operations on pocket hosts.

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
