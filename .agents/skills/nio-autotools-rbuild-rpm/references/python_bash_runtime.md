# Python and Bash Runtime

This reference explains how bash scripts and Python code are wired into the nio-analytics build and install result.

## Bash Scripts

Root Makefile.am installs many operational scripts via dist_libexec_SCRIPTS.
Examples include:
- etl_runner.sh
- etl_utils.sh
- scp_day.sh
- clickhouse_loader.sh
- alerts_checker.sh

py3/Makefile.am also installs bash helpers via dist_libexec_SCRIPTS.

Interpretation:
- Many production behaviors come from installed shell scripts, not compiled code.
- If a user asks why an installed script exists on a host, check Makefile.am and the RPM spec.

## Python Build Behavior

py3 is not installed by pip in the usual developer way.
Instead:
- py3/Makefile.am creates a python-build symlink tree
- setup.py build runs with the configured Python 3.12 interpreter
- setup.py install writes package files and entrypoints into the configured prefix

## Python Entry Points

setup.py.in defines many console scripts.
Important examples include:
- scv_domain_report
- scv_raw_matches_report
- scv_ncore_area_matches
- scheduler3
- postgres_insert3
- render_scopes
- scp_predictor

If a user asks where a command comes from, check setup.py.in first.

## RBUILD-Specific Python Behavior

py3/Makefile.am contains RBUILD conditionals.
In rbuild mode:
- PYTHON312 points into the nio-virtualenv-python environment
- .pth files may be created so the virtualenv can see nio-analytics site-packages

This matters because:
- build-time Python interpreter path differs between rbuild and installed RPM systems
- import problems can be caused by missing .pth linkage or wrong prefix assumptions

## Runtime Questions To Answer

When troubleshooting Python or bash behavior, check:
1. which file installs the artifact: root Makefile.am, py3/Makefile.am, or RPM spec
2. whether the artifact is a shell script, Python console entrypoint, or compiled library
3. whether the path is a build-tree path, rbuild install prefix path, or final RPM path
4. whether the interpreter/runtime environment matches the branch expectations

## Expected Installed Areas

Common installed areas after build/RPM:
- /opt/nio/bin
- /opt/nio/libexec
- /opt/nio/share/etl
- /opt/nio/lib/python3.12/site-packages
- /opt/nio/lib64/python3.12/site-packages
- /var/opt/nio for runtime data and logs
- /etc/opt/nio for config
