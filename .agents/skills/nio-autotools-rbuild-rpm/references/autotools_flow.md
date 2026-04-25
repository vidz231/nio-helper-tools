# Autotools Flow

This reference explains how nio-analytics uses autotools at the root and in the py3 subproject.

## Root Project

Main files:
- nio-analytics/configure.ac
- nio-analytics/Makefile.am

Key points:
- Root configure.ac defines the main autotools project for nio-analytics.
- It enables a recursive subproject build with AC_CONFIG_SUBDIRS([py3]).
- Root automake uses SUBDIRS = $(subdirs), so the py3 subproject is part of the full build flow.
- Root configure checks core C build dependencies such as glib and check.
- Root configure also exposes build_env via the RBUILD conditional.

Useful facts:
- configure.ac uses AC_CONFIG_AUX_DIR(build-aux) and AC_CONFIG_MACRO_DIR(m4).
- Warnings are strict by default and include -Werror unless disabled.
- Root build still references AM_PATH_PYTHON([2.7]) for root-level automation, even though py3 separately enforces Python 3.12.

## Root Makefile.am

Main behaviors:
- Installs many bash scripts via dist_libexec_SCRIPTS.
- Installs some JSON config via dist_sysconf_DATA and dist_data_DATA.
- Copies migrations from resources/migrations in install-data-local.
- Creates runtime directories in install-exec-hook.
- Renders scope templates in all-local through the py3 Python code.

What this means:
- Not everything is a compiled binary.
- A large part of the installed result is shell scripts, configs, ETL resources, and directories expected by deployed systems.

## py3 Subproject

Main files:
- nio-analytics/py3/configure.ac
- nio-analytics/py3/Makefile.am
- nio-analytics/py3/setup.py.in

Key points:
- py3 is its own autotools subproject.
- py3/configure.ac requires Python 3.12.
- py3/Makefile.am builds a C library and also runs setup.py build and setup.py install.
- py3 creates console entrypoints from setup.py.in.

## Recursive Build Chain

Normal flow:
1. autoreconf --install at repository root generates root configure and supporting build files.
2. root configure runs and also configures py3 because of AC_CONFIG_SUBDIRS([py3]).
3. make or make install at root descends into py3.
4. py3 build runs setup.py build using the configured Python 3.12 interpreter.
5. py3 install runs setup.py install into the configured prefix.

## Key Outputs By Stage

After autoreconf:
- configure
- Makefile.in
- build-aux helpers
- config.h.in

After configure:
- Makefile
- py3/Makefile
- config.h

After build/install:
- installed bash scripts under prefix libexec or bin
- installed Python package in site-packages
- installed entrypoint scripts
- installed ETL resources
- created runtime directory tree

## How To Explain Problems

Map failures to stage:
- autoreconf failure: macro, m4, or autotools tooling problem
- configure failure: dependency detection, compiler, pkg-config, or Python version problem
- make failure: C compile, generated file, or recursive build problem
- install failure: prefix, permissions, setup.py install, or path generation problem
