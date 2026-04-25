# Troubleshooting

Use this reference to map symptoms to build stages and respond with precise next steps.

## Stage Mapping

- autoreconf stage:
  - missing or broken m4 macros
  - build-aux generation issues
  - configure script not regenerating

- configure stage:
  - pkg-config dependency missing
  - compiler not found
  - Python version mismatch in py3
  - wrong PKG_CONFIG_PATH or ACLOCAL_PATH

- make stage:
  - C compile errors
  - recursive subdir failures
  - generated template or render step failure
  - py3 setup.py build failure

- install stage:
  - setup.py install path issues
  - missing DESTDIR or prefix assumptions
  - shell scripts or ETL resources not installed where expected

- RPM buildroot stage:
  - file ownership or missing directory problems
  - ETL/config copy path mismatch
  - Python compileall or site-packages path mismatch

- post-install/runtime stage:
  - service not enabled or restarted
  - db_migrator side effects
  - role-specific logic from analytics.json

## Fast Diagnosis Questions

Ask or infer:
1. Did the failure happen during autoreconf, configure, make, make install, or rpm install?
2. Was the build local, rbuild remote, Jenkins RPM, or installed host verification?
3. Is the issue root project, py3 subproject, or deployed runtime path?
4. Did configure.ac, Makefile.am, setup.py.in, or spec recently change?

## Safe Default Commands

Autotools refresh:
./rbuild.sh nio-analytics -r -sAab

Incremental build:
./rbuild.sh nio-analytics -sb

Build and test:
./rbuild.sh nio-analytics -sbt

Configure-only debug:
./rbuild.sh nio-analytics -sAa

## Expected Artifacts To Mention

- generated configure and Makefile files
- installed libexec scripts
- installed /opt/nio/bin entrypoints
- installed Python site-packages
- copied /opt/nio/share/etl resources
- runtime directories under /var/opt/nio
- service or migration changes after RPM install

## Typical Explanation Pattern

Use this pattern in answers:
- what stage is failing
- why that stage owns the problem
- exact command to reproduce or validate
- exact artifact or file to inspect next
- what successful output should look like
