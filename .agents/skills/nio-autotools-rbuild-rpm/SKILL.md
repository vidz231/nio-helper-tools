---
name: nio-autotools-rbuild-rpm
description: Understand and operate the nio-analytics build system deeply. Use this skill whenever the user mentions configure.ac, Makefile.am, py3 subproject builds, autoreconf, configure, make install, rbuild, remote build hosts, compiler flags, Python runtime wiring, shell script installation, nio-analytics.spec, BuildRequires, Requires, RPM packaging, or why a nio-analytics build, install, or deployment failed. Prefer this skill even when the user only asks for part of the chain, because nio-analytics build issues often span autotools, rbuild, Python packaging, and RPM install behavior together.
---

# NIO Autotools rbuild RPM

Use this skill for nio-analytics build-system work.

This skill is for understanding and operating the full nio-analytics build chain:
- root autotools project
- py3 autotools subproject
- Python and bash runtime layout
- remote rbuild workflow
- RPM packaging and post-install behavior

## When To Use

Use this skill when the user asks to:
- explain how configure.ac or Makefile.am works in nio-analytics
- debug autoreconf, configure, make, or make install failures
- understand how the py3 folder is built and installed
- verify Python, bash, pkg-config, compiler, or runtime environment assumptions
- understand how nio-analytics becomes an RPM
- understand what the spec file installs or migrates
- run or debug rbuild commands for nio-analytics

## Do Not Use

Do not use this skill for:
- general ETL runtime exploration on deployed pockets
- API endpoint implementation in nio-api3
- unrelated repo build systems unless the user explicitly expands scope

## Output Contract

Default to this response structure:
1. short diagnosis or explanation
2. exact commands to run
3. expected artifacts or files
4. likely failure points
5. next verification step

When explaining, always connect the stages together instead of describing them in isolation.

## Reading Order

Read references in this order:
1. references/autotools_flow.md
2. references/rbuild_workflow.md
3. references/python_bash_runtime.md
4. references/rpm_pipeline.md
5. references/troubleshooting.md

## Behavior Rules

- Treat nio-analytics root and py3 as one build chain with recursive autotools.
- Explain whether a problem belongs to autoreconf, configure, make, install, RPM post-install, or runtime validation.
- Prefer exact workspace commands such as ./rbuild.sh nio-analytics -saAb over generic autotools advice.
- When discussing installed artifacts, use the RPM layout: /opt/nio, /var/opt/nio, /etc/opt/nio.
- When discussing remote builds, use rbuild terminology: staging dir, build dir, install dir, build env.
- When discussing Python, distinguish between build-time Python and installed runtime entrypoints.
- When discussing shell scripts, state whether they come from automake script installation or RPM install rules.
- Always mention expected outputs such as generated Makefiles, installed scripts, site-packages, libexec files, ETL resources, or RPM subpackages.
