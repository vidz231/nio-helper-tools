---
name: nio-analytics-explorer
description: Explore and operate installed nio-analytics ETL pipelines on pocket hosts using deployed RPM paths. Use this skill whenever the user asks to check latest input or output files by granularity (unit, hour, day), verify server roles across mobile or fixed pockets, validate scv_shard or scv_master artifacts, or trigger ETL on remote pocket machines with etl_runner. Prefer read-only SSH checks first, and require explicit confirmation before any trigger or write action.
---

# NIO Analytics Explorer

Use this skill for runtime operations on deployed machines only.

This skill is designed for installed RPM environments and must use:
- /opt/nio
- /var/opt/nio
- /etc/opt/nio

Do not use rbuild paths, local development trees, or source-repo runtime assumptions when executing remote checks.

## When To Use

Use this skill when the user asks to:
- check if a pocket host has ETL input files for a specific role and granularity
- list the latest files for unit, hour, or day processing
- validate scv_shard to scv_master handoff artifacts
- inspect ETL logs for a role, source, or interval
- trigger a pipeline with etl_runner on a pocket machine

## Do Not Use

Do not use this skill for:
- source code implementation in nio repositories
- rbuild build or test workflows
- API endpoint development

## Operating Contract

Always follow this order:
1. Confirm target host, role, source, and interval.
2. Run read-only preflight checks first.
3. Return file evidence in the standard output format.
4. Ask for explicit confirmation before any non-read command.
5. After a trigger, verify logs and output artifacts.

## Standard Output Format

When returning file checks, always provide:
- host
- role
- source
- interval
- top 10 latest files with timestamp, size, full path
- quick interpretation: found, empty, missing directory, or permission issue

## References

Read these files in this order:
1. references/server_map.md
2. references/io_paths.md
3. references/commands.md

## Behavior Rules

- Default to read-only SSH commands.
- Never assume command success.
- If SSH or sudo fails, report the exact failure class and next best check.
- Unit means 30 minutes unless the runtime config explicitly overrides it.
- Prefer absolute paths on remote hosts.
- Use etl_runner as the primary trigger method.
- Use task broker commands only when validating or documenting pipeline handoff steps.
