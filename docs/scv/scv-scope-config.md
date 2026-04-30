# SCV Scope Configuration

This page explains how `scope_a` and `scope_b` are used in the SCV master flow.

## Where Scope Values Come From

The scope names are read from:

- `/etc/opt/nio/analytics.json`

Specifically:

- `.scv.scope_a`
- `.scv.scope_b`

The master script `scv_master/day/scv/01_scv_merger.sh` reads those values and passes them into `scv_merger`.

## What They Mean

`scope_a` and `scope_b` are not raw input columns from the shard TLS CSV files.

They are names of fields that SCV master tries to resolve from cellmap-derived location metadata.

Examples:

- `scope_a = city`
- `scope_b = region`

This means the master flow expects the staged cellmap data to contain `city` and `region` values for the relevant location entries.

## Does the Input TLS Data Need `city` and `region` Columns?

No.

The TLS matching path needs location identifiers, not literal `city` or `region` columns in the raw shard files.

The important chain is:

1. Shard raw and day files carry location identifiers.
2. Master stages mobile and fixed `cellmap.json` files.
3. `scv_merger` uses the location values in the mapping file to look up scope fields in the cellmap content.
4. The resolved scope values are then written into the final SCV outputs.

## Required Data Dependency

If `scope_a=city` and `scope_b=region`, then the relevant staged cellmap entries must provide values for:

- `city`
- `region`

The dependency is on the cellmap content, not on the raw TLS CSV schema.

## What Happens If the Scope Fields Are Missing

SCV can still complete.

But the scope values in the final outputs become empty or unresolved because the master cannot translate the location into the requested scope fields.

This means:

- core matching can still succeed
- `home_analytics` can still be produced
- scope-oriented reporting quality may be degraded or blank

## Files Involved in Scope Resolution

Main runtime files:

- `/var/opt/nio/feeds/scv/tmp/mobile_cellmap.json`
- `/var/opt/nio/feeds/scv/tmp/fixed_cellmap.json`
- `/var/opt/nio/feeds/scv/tmp/user_mobile_to_fixed_map.csv`
- `/var/opt/nio/feeds/scv/home_analytics.YYYY-MM-DD.log`
- `/var/opt/nio/feeds/scv/home_analytics_distributions.YYYY-MM-DD.log`
- `/var/opt/nio/feeds/scv/home_analytics_scope_report.YYYY-MM-DD.log`

## Practical Checks

When scope-based grouping looks wrong:

1. Confirm `.scv.scope_a` and `.scv.scope_b` in `/etc/opt/nio/analytics.json`.
2. Confirm the master staged both cellmaps successfully.
3. Confirm the cellmap entries actually include the requested fields.
4. Confirm the mapping file contains the expected location identifiers.
5. Only after that, inspect the final report outputs for blank or skewed scope values.

## Practical Interpretation

- If the customer wants grouping by `city` and `region`, the cellmap data must expose `city` and `region` for the relevant locations.
- If the TLS path only provides location identifiers and the cellmap is correct, that is enough.
- If the cellmap lacks those fields, changing only `analytics.json` will not make the grouping meaningful.