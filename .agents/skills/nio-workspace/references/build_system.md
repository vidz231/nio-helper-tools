# NIO Build System (rbuild + autotools)

## Overview

NIO uses `rbuild` — a bash tool for **edit-locally, build-remotely** workflows. You edit C/Python source on macOS and build on a remote Linux server via SSH + rsync.

## rbuild Command Reference

| Command | What It Does |
|---|---|
| `rbuild` or `rbuild -sb` | Stage source + build (default, most common) |
| `rbuild -s` | Stage source only (rsync to build server) |
| `rbuild -b` | Build only (`make install` on remote) |
| `rbuild -A` | Run `autoreconf --install` on remote |
| `rbuild -a` | Run `configure --prefix=$INSTALL_DIR` on remote |
| `rbuild -sAab` | Full setup: stage + autoreconf + configure + build |
| `rbuild -c` | Clean build directory (`make clean`) |
| `rbuild -t` | Run tests (`make check`) |
| `rbuild -r` | Remove build directory entirely |
| `rbuild -o` | Shortcut for `-e optimized` |
| `rbuild -d` | Deploy built binaries to a third machine |
| `rbuild -B <target>` | Build a specific Makefile target |
| `rbuild -j <N>` | Set make parallelism |

**Execution order** (regardless of flag position): Stage → Clean → Autoreconf → Configure → Make → Deploy

## Configuration (`rbuild.conf`)

Located at workspace root: `/Volumes/vidzdatastore/work/mobileum_source/rbuild.conf`

Key variables:
```bash
DEVTOOLSET="gcc-toolset-12"
BUILD_HOST=user@remote-server.niometrics.com

INSTALL_DIR="/home/user/.local/${BUILD_ENV}"
PKG_CONFIG_PATH="$pkg_libnio:$pkg_ncore:$pkg_nlive:$pkg_optnio"

CC=/opt/rh/${DEVTOOLSET}/root/usr/bin/gcc
CXX=/opt/rh/${DEVTOOLSET}/root/usr/bin/g++
BUILD_JOBS=40
```

### Build Environments

Selected via `-e <env>` flag (default: `debug`):

| Environment | Flags | Use Case |
|---|---|---|
| `debug` | `-ggdb3 -g -O0` + sanitizers (ASAN/UBSAN) | Development, debugging |
| `optimized` | `-ggdb3 -g -O3 -DNIO_LOG_LEVEL=0` | Performance testing, production |

## First-Time Setup for a Repo

```bash
# 1. Stage source to build server
./rbuild.sh <repo-name> -s

# 2. Run autoreconf + configure + build
./rbuild.sh <repo-name> -Aab

# After first setup, just use:
./rbuild.sh <repo-name> -sb    # or just: ./rbuild.sh <repo-name>
```

The wrapper script `rbuild.sh` at workspace root handles the `-i rbuild.conf` setup.

## autotools Structure

Each C repo uses GNU autotools:

```
<repo>/
├── configure.ac    # autoconf input (defines project, dependencies, flags)
├── Makefile.am     # automake input (defines targets, sources, install rules)
├── m4/             # Custom m4 macros (if any)
└── build-aux/      # Generated autoconf auxiliary files
```

### Key Dependencies (from `configure.ac`)

- `glib-2.0 >= 2.42.2` — Core C utility library
- `check` — Unit testing framework for C
- Standard C99 compiler

### Build Artifacts

After `rbuild -sb`, built binaries install to `$INSTALL_DIR/<repo>/`:
- `bin/` — Executables
- `lib/` — Libraries (`.so`, `.a`)
- `lib/pkgconfig/` — pkg-config files (used by dependent repos)

## rsync Exclude Lists

`rbuild -s` uses rsync exclude lists to avoid overwriting autoreconf-generated files:
1. `<repo>/.rbuild_exclude` (per-project)
2. `~/.rbuild.exclude` (global)
3. Built-in default list (`rbuild -x` to inspect)

Each repo also has `.rbuild.exclude` at its root listing generated files to skip.

## Python Repos (nio-api3, nio-python3-libs, etc.)

Python repos still use autotools for packaging but `setup.py.in` for Python-specific build:
- `configure.ac` configures the Python environment
- `setup.py.in` is processed by autoconf to generate `setup.py`
- `Makefile.am` handles install/test targets

### Running Python Tests

```bash
# After rbuild -sb to the remote server:
cd rbuild/<repo>.<env>/
./run_tests.sh                              # All tests
./run_tests.sh -- -p "*<pattern>_"          # Specific tests
./run_tests.sh -d                           # Without database
./run_tests.sh -d -c                        # Without database & component check
TEST_LOGLEVEL=DEBUG ./run_tests.sh          # Debug logging
```
