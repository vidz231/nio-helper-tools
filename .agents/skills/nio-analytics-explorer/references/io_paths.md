# Runtime IO Paths By Granularity

Use deployed RPM runtime locations only:
- /opt/nio
- /var/opt/nio
- /etc/opt/nio

## Granularity

- unit: 30-minute interval
- hour: 60-minute interval
- day: daily interval

## Server Roles By Processing Step

### Mobile side

1. pocket-ath-np1 (ncore, nlive)
- produces upstream artifacts for unit, hour, and day windows
- pushes handoff data toward mrs workflows

2. pocket-ath-mu1 (mrs, scv_shard, scv_master)
- receives and aggregates upstream data in mrs stage
- runs shard matching in scv_shard stage
- performs master merge in scv_master stage

3. pocket-ath-mu3 (scv_broker, scv_shard)
- provides scv brokered handoff paths
- can run shard stage depending on deployment routing

### Fixed side

1. pocket-ath-np2 (ncore, nlive)
- produces upstream fixed-network artifacts

2. pocket-ath-mu2 (mrs)
- receives fixed-side handoff and runs mrs stage

## Core Runtime Locations

- ETL runner:
  - /opt/nio/libexec/etl_runner.sh

- ETL definitions:
  - /opt/nio/share/etl/<role>/cubes/

- Runtime config:
  - /etc/opt/nio/analytics.json

- Runtime logs:
  - /var/opt/nio/log/

- Runtime data roots:
  - /var/opt/nio/aggregations/
  - /var/opt/nio/feeds/
  - /var/opt/nio/historical/
  - /var/opt/nio/alerts/
  - /var/opt/nio/tmp/

## Role Oriented Inputs And Outputs

### ncore

Typical input:
- probe collection inputs and role-specific ETL source files under configured runtime roots

Typical outputs:
- /var/opt/nio/log/scv/
- /var/opt/nio/aggregations/
- scheduled handoff via task broker to mrs

Common checks:
- unit artifacts produced for downstream mrs consumption
- day artifacts for daily handoff

### nlive

Typical input:
- live network streams and role-specific intermediate files

Typical outputs:
- /var/opt/nio/historical/user_1m/
- /var/opt/nio/alerts/
- /var/opt/nio/aggregations/

Common checks:
- 1m or unit feed generation
- day rollups and handoff to mrs or downstream consumers

### mrs

Typical input:
- copied artifacts from ncore and nlive via task brokers

Typical outputs:
- /var/opt/nio/aggregations/scv.*
- /var/opt/nio/feeds/nio/
- mrs ETL logs under /var/opt/nio/log/

Common checks:
- source files exist for requested unit or day window
- prepared outputs available for scv_shard and scv_master stages

### scv_shard

Typical input:
- mrs-produced scv tls artifacts for matching windows

Typical outputs:
- unit:
  - /var/opt/nio/aggregations/scv_matches/
  - scv.unit_merged_matches_raw and related files
- day:
  - /var/opt/nio/feeds/scv/scv.day_merged_matches.*
  - partial outputs for scv_master handoff

Common checks:
- unit input file presence by timestamp window
- day partial files generated and queued for master

Typical source names:
- unit: tls_scv_shard
- day: tls_scv_shard

### scv_master

Typical input:
- partial day files from scv_shard hosts
- complementary userkey or subintel feeds if configured

Typical outputs:
- merged day-level scv outputs in /var/opt/nio/feeds/scv/
- final artifacts for analytics load chain

Common checks:
- all expected shard files present for day window
- merged output created after expected handoff completion

Typical source names:
- day: scv or deployment-specific master source alias

## Time And Naming Notes

- Unit file names commonly encode YYYY-MM-DD-HH-MM.
- Day files commonly encode YYYY-MM-DD or YYYYMMDD.
- Use both filename timestamp and mtime when determining latest files.
