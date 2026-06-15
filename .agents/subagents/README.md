# NIO Project Subagents

Project-specific subagent prompts for the Mobileum NIO workspace.

These are plain prompt files intended to be used as scoped helper agents for
work inside:

- `nio-api3`
- `nio-analytics`
- `nio-analytics-c-tools`
- `nio-base`
- `nio-python3-libs`
- `nio-storage`
- `rbuild`

## Suggested subagents

- `api-explorer.md`
  - Map Flask API endpoints, controller patterns, route registration, and tests.
- `analytics-explorer.md`
  - Map ETL pipelines, `libexec` entrypoints, scheduler scripts, and C-tool touchpoints.
- `shared-libs-explorer.md`
  - Map `niolib`, generated config, and cross-repo dependencies.
- `build-workflow-explorer.md`
  - Focus on `rbuild`, autotools, validation commands, and safe build workflow.
- `change-impact-reviewer.md`
  - Review a proposed change across repo boundaries and list likely knock-on effects.

## Usage pattern

Pass the file contents as the agent's system/task prompt, then append the
specific task. Keep each agent scoped to its defined repositories.

Example:

1. Load `analytics-explorer.md`
2. Append: "Investigate how `scp_day.sh` feeds downstream aggregators and list
   the tests or commands needed to validate a change."

## Notes

- These prompts are intentionally read-only by default.
- They assume the workspace root is:
  `/Volumes/vidzdatastore/work/mobileum_source`
- They reflect the repo map documented in
  `.agents/skills/nio-workspace/SKILL.md`
