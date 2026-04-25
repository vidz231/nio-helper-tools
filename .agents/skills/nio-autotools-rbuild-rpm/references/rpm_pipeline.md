# RPM Pipeline

This reference explains how nio-analytics is packaged into RPMs and what happens on install.

## Main Spec File

- nio-analytics/release/nio-analytics.spec

## High-Level RPM Stages

- %prep: unpack source
- %build: autoreconf, configure, make, optional tests
- %install: populate buildroot with binaries, Python packages, ETL resources, scripts, configs, and runtime directories
- %post: systemd reload and service actions
- %posttrans: database extension setup, migrations, render steps, and legacy file moves
- %preun: stop or disable services on uninstall

## Important Install Paths

- prefix: /opt/nio
- local state: /var/opt/nio
- config: /etc/opt/nio
- ETL resources: /opt/nio/share/etl
- migrations: /opt/nio/share/etc/migrations
- Python site-packages: /opt/nio/lib/python3.12/site-packages and lib64 variant

## What RPM Installs

The spec installs:
- compiled outputs from make install
- ETL tree from resources/etl into /opt/nio/share/etl
- customizable config into /var/opt/nio/customizable-conf
- shell wrappers into /opt/nio/bin
- many runtime directories under /var/opt/nio
- migrations and shared config files

## Python Packaging Inside RPM

The spec compiles Python bytecode with Python 3.12.
It keeps Python source present for scanning and support.
This means Python packaging is a combined result of py3 autotools install plus RPM buildroot processing.

## Subpackages

- nio-analytics-cubes: ETL resource configs and customizable files
- nio-analytics-schema: migration files

When users ask why a file is in a specific package, map it to these subpackages or the base package.

## Build Dependencies vs Runtime Dependencies

BuildRequires covers what is needed to build the RPM.
Requires covers what must be present on the installed host.
Important recurring dependency groups:
- PostgreSQL and extensions
- ClickHouse
- jq, glib, core shell tools
- nio-base, nio-python3-libs, nio-virtualenv-python, nio-ncore tools, nio-nlive libs, analytics C tools

## Post-Install Behavior

The spec does more than copy files.
It may also:
- reload systemd units
- enable or restart nio-triggers.service for certain machine roles
- create database extensions
- run db_migrator over multiple migration folders
- render scope configurations depending on analytics.json settings
- move some legacy customizable files to persistent runtime locations

## How To Explain RPM Questions

When a user asks about deployment behavior, separate these layers:
1. built artifact from autotools
2. installed artifact in buildroot during RPM creation
3. final file path on deployed machine
4. post-install actions that mutate the runtime system after package installation
