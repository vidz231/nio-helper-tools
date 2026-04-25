# rbuild Workflow

This reference explains how nio-analytics is built remotely with rbuild.

## Key Files

- rbuild.sh
- rbuild.conf
- rbuild/README.md

## Wrapper Entry Point

Use the workspace wrapper:
./rbuild.sh nio-analytics <flags>

This enters the repo and invokes rbuild with the shared config file.

## What rbuild Does

rbuild supports edit locally, build remotely.

Typical ordered stages:
1. stage source to remote build host
2. autoreconf on remote staging tree
3. configure in a separate remote build directory
4. make install in the build directory
5. optional make check
6. optional deploy to another host

These stages are executed in a fixed order no matter how flags are ordered.

## Important rbuild.conf Values

- BUILD_HOST: remote Linux machine used for builds
- INSTALL_DIR: remote install prefix root, usually under $HOME/.local/${BUILD_ENV}
- PKG_CONFIG_PATH: dependency lookup for configure
- CC and CXX: compiler toolchain paths
- CFLAGS and CXXFLAGS: debug or optimized flags
- BUILD_JOBS: make parallelism
- SSH: non-interactive SSH behavior

## Build Environments

Common build envs:
- debug
- optimized

Behavior from rbuild.conf:
- debug uses sanitizers, -O0, and strict warnings
- optimized uses RPM-like optimization flags and disables noisy logging in some cases

## Recommended Commands

Fast incremental build:
./rbuild.sh nio-analytics -sb

Full clean autotools rebuild:
./rbuild.sh nio-analytics -r -sAab

Optimized build:
./rbuild.sh nio-analytics -sbo

Run tests after build:
./rbuild.sh nio-analytics -sbt

Configure-only troubleshooting:
./rbuild.sh nio-analytics -sAa

## How Remote Paths Work

There are usually three remote concepts:
- staging dir: synced source tree
- build dir: out-of-tree configure and make directory
- install dir: prefix where make install writes outputs

When explaining rbuild, name all three explicitly.

## Common Failure Modes

- SSH/auth failure: cannot reach build host
- stale build dir: old configure results or incompatible generated files
- pkg-config failure: dependency not visible through PKG_CONFIG_PATH
- compiler toolchain path failure: gcc-toolset missing or wrong version
- configure failure in py3: Python 3.12 missing on build host or wrong interpreter path
- make install failure: setup.py install path or DESTDIR issue

## Practical Guidance

Prefer these habits:
- after configure.ac or Makefile.am changes, use -A and -a, not just -b
- after dependency or compiler changes, rebuild from a clean build dir with -r
- when debugging, use debug env first unless the issue is optimization-specific
- explain that rbuild performs make install, not just make
