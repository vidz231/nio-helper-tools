# ETL Pipeline I/O Reference

Quick reference for input/output file locations on deployed servers when running ETL pipelines.

**Variables used throughout:**
- `${NIO_TIMESTAMP}` — Unix epoch seconds for the interval start
- `${YMD_HM}` — `YYYY-MM-DD-HH-MM` formatted timestamp
- `${YMD}` — `YYYY-MM-DD` formatted date
- `${probe}` — hostname of the machine
- `${NETWORK_TYPE}` — `mobile` or `fixed`

**Common base directories:**

| Directory | Purpose |
|---|---|
| `/var/opt/nio/log/raw/` | Raw input logs from DPI probes |
| `/var/opt/nio/log/layer8/` | Layer8 classification logs |
| `/var/opt/nio/log/scv/` | SCV (TLS) input logs |
| `/var/opt/nio/log/live/` | Live (nlive) input logs |
| `/var/opt/nio/aggregations/` | Cube aggregation outputs (ncore/mrs) |
| `/var/opt/nio/feeds/nio/report-YYYYmm/` | MRS report feeds (per source subdirs) |
| `/var/opt/nio/feeds/` | Various feed directories (scv, dci, events) |
| `/var/opt/nio/usage/` | Usage pipeline data (hour/day subdirs) |
| `/var/opt/nio/alerts/` | Alert output data (by interval subdirs) |
| `/var/opt/nio/rdna/` | RDNA counters and aggregations |
| `/var/opt/nio/historical/` | Nlive historical data (1m/30m/1d) |
| `/var/opt/nio/state/sharding/` | Sharding state for distributed cubes |
| `/var/opt/nio/dns_active/` | DNS active subscriber counts |
| `/var/opt/nio/tmp/` | Temporary files for sort operations |
| `/var/opt/nio/dmp_processor/` | DMP rolling data |

**Log files for pipelines:**

| Log file | What it covers |
|---|---|
| `/var/opt/nio/log/etl_cubes.<source>.<interval>.<role>` | Main ETL log per source/interval/role |
| `/var/opt/nio/log/scv_ncore.log` | TLS/SCV on ncore |
| `/var/opt/nio/log/scv_mrs.log` | TLS/SCV on MRS |
| `/var/opt/nio/log/scv_nlive.log` | SCV on nlive |
| `/var/opt/nio/log/scv_master_<interval>.log` | SCV master processing |
| `/var/opt/nio/log/scv_shard_<interval>.log` | SCV shard processing |
| `/var/opt/nio/log/dns_active_subs_preprocess.log` | DNS active subscriber preprocessing |

---

## NCORE — Unit (30-minute)

### tls
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/scv/tls.{cid\|sid\|ctk\|stk}.csv.{shard_func}.{shard_no}.{num_shards}.${NIO_TIMESTAMP}` |
| **Intermediate** | `/var/opt/nio/aggregations/scv.tls.{type}.${YMD_HM}.${probe}.${NETWORK_TYPE}.{shard_suffix}.csv` |
| **Output** | `/var/opt/nio/aggregations/scv.tls.{type}.${YMD_HM}.${probe}.${NETWORK_TYPE}.{shard_func}.*.csv.lz4` |
| **Log** | `/var/opt/nio/log/scv_ncore.log` |
| **Failure marker** | `/var/opt/nio/aggregations/scv.tls.${probe}.${NETWORK_TYPE}.${YMD_HM}.failed` |

### ottcall
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/raw/ottcall.log.${NIO_TIMESTAMP}` |
| **Intermediate** | `/var/opt/nio/aggregations/ottcall.${NIO_TIMESTAMP}.tmp` |
| **Intermediate** | `/var/opt/nio/aggregations/ottcall.log.${NIO_TIMESTAMP}.csv.tmp` |
| **Output** | `/var/opt/nio/aggregations/ottcall.${probe}.${YMD_HM}.0.csv` |
| **Failure marker** | `/var/opt/nio/aggregations/ottcall.${probe}.${YMD_HM}.0.csv.failed` |

### chatacct
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/raw/chatacct.log.${NIO_TIMESTAMP}` |
| **Intermediate** | `/var/opt/nio/aggregations/chatacct.${NIO_TIMESTAMP}.tmp` |
| **Output** | `/var/opt/nio/aggregations/chatacct.${probe}.${YMD_HM}.0.csv` |
| **Failure marker** | `/var/opt/nio/aggregations/chatacct.${probe}.${YMD_HM}.0.csv.failed` |

### competitors
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/layer8/hspf.layer8.competitors.log.${NIO_TIMESTAMP}` |
| **Intermediate** | `/var/opt/nio/aggregations/competitors.${NIO_TIMESTAMP}.tmp` |
| **Output** | `/var/opt/nio/aggregations/competitors.${probe}.${YMD_HM}.0.csv` |
| **Failure marker** | `/var/opt/nio/aggregations/competitors.${probe}.${YMD_HM}.0.csv.failed` |

### cookie
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/raw/cookieintel.log.${NIO_TIMESTAMP}` |
| **Output** | `/var/opt/nio/aggregations/cookie.${probe}.${YMD_HM}.0.csv` |
| **Failure marker** | `/var/opt/nio/aggregations/cookie.${probe}.${YMD_HM}.0.csv.failed` |

### dci
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/netflix/netflix.chunks-${YMD_H}-[0-5]*.log` (split at :00/:30) |
| **Intermediate** | `/var/opt/nio/feeds/dci/netflix.chunks.${NIO_TIMESTAMP}.tmp` |
| **Output** | `/var/opt/nio/feeds/dci/netflix.chunks.${probe}.${YMD_HM}.0.csv` |
| **Failure marker** | `/var/opt/nio/feeds/dci/netflix.chunks.${probe}.${YMD_HM}.0.csv.failed` |
| **Note** | Targets big_data role, not MRS |

### mobilestores
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/layer8/hspf.layer8.applestore.log.${NIO_TIMESTAMP}` |
| **Intermediate** | `/var/opt/nio/aggregations/mobilestores.${NIO_TIMESTAMP}.tmp` |
| **Output** | `/var/opt/nio/aggregations/mobilestores.${probe}.${YMD_HM}.0.csv` |
| **Failure marker** | `/var/opt/nio/aggregations/mobilestores.${probe}.${YMD_HM}.0.csv.failed` |

### search
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/layer8/hspf.layer8.searchintel.log.${NIO_TIMESTAMP}` |
| **Intermediate** | `/var/opt/nio/aggregations/search.${NIO_TIMESTAMP}.tmp` |
| **Output** | `/var/opt/nio/aggregations/search.${probe}.${YMD_HM}.0.csv` |
| **Failure marker** | `/var/opt/nio/aggregations/search.${probe}.${YMD_HM}.0.csv.failed` |

### sshproxyfraud
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/raw/sshproxyfraud.log.${NIO_TIMESTAMP}` |
| **Intermediate** | `/var/opt/nio/aggregations/sshproxyfraud.${NIO_TIMESTAMP}.tmp` |
| **Output** | `/var/opt/nio/aggregations/proxyfraud.${probe}.${YMD_HM}.0.csv` |
| **Failure marker** | `/var/opt/nio/aggregations/proxyfraud.${probe}.${YMD_HM}.0.csv.failed` |
| **Note** | Output uses `proxyfraud` prefix (not `sshproxyfraud`) |

### torrent
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/layer8/hspf.layer8.torrent.log.${NIO_TIMESTAMP}` |
| **Intermediate** | `/var/opt/nio/aggregations/torrent.${NIO_TIMESTAMP}.tmp` |
| **Output** | `/var/opt/nio/aggregations/torrent.${probe}.${YMD_HM}.0.csv` |
| **Failure marker** | `/var/opt/nio/aggregations/torrent.${probe}.${YMD_HM}.0.csv.failed` |

### useridentity
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/layer8/hspf.layer8.useridentity.log.${NIO_TIMESTAMP}` |
| **Intermediate** | `/var/opt/nio/aggregations/useridentity.${NIO_TIMESTAMP}.tmp` |
| **Output** | `/var/opt/nio/aggregations/useridentity.${probe}.${YMD_HM}.0.csv` |
| **Failure marker** | `/var/opt/nio/aggregations/useridentity.${probe}.${YMD_HM}.0.csv.failed` |

### userinfo
| | Path |
|---|---|
| **Input** | `/var/opt/nio/aggregations/userinfo.${NIO_TIMESTAMP}.tmp` |
| **Output** | `/var/opt/nio/aggregations/userinfo.${probe}.${YMD_HM}.0.csv` |
| **Failure marker** | `/var/opt/nio/aggregations/userinfo.${probe}.${YMD_HM}.0.csv.failed` |

### vsa
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/raw/vsa.log.${NIO_TIMESTAMP}` (standard preaggregator pattern) |
| **Output** | `/var/opt/nio/aggregations/vsa.${probe}.${YMD_HM}.0.csv` |

### youtube
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/raw/youtube.log.${NIO_TIMESTAMP}` (standard preaggregator pattern) |
| **Output** | `/var/opt/nio/aggregations/youtube.${probe}.${YMD_HM}.0.csv` |

---

## NCORE — Day

### subintel
| | Path |
|---|---|
| **Input** | Aggregated from unit-level data |
| **Output** | `/var/opt/nio/aggregations/mstate.subintel-imsi-state-dump.${YMD}.ncores_merged.{mobile\|fixed}.log` |

---

## NLIVE — Unit (30-minute)

### preaggregate
| | Path |
|---|---|
| **Input** | `/var/opt/nio/historical/1m/*.log.${NIO_TIMESTAMP}` (1m jsonlog files) |
| **Intermediate** | `/var/opt/nio/aggregations/${datasource}.log.${NIO_TIMESTAMP}.csv.tmp` |
| **Output (30m logs)** | `/var/opt/nio/historical/30m/*.log.${day_start}` |
| **Output (compressed)** | `/var/opt/nio/aggregations/${datasource}.${probe}.${YMD_HM}.0.lz4` |
| **Output (parquet)** | `/var/opt/nio/historical/1m/parquet/${schema_name}/` |
| **Note** | Handles 1m→30m aggregation via `aggregate_historical` binary |

### snifraud
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/live/snifraud.log.${NIO_TIMESTAMP}` |
| **Intermediate** | `/var/opt/nio/aggregations/snifraud.log.${NIO_TIMESTAMP}.csv.tmp` |
| **Output** | `/var/opt/nio/aggregations/snifraud.${probe}.${YMD_HM}.0.lz4` |
| **Failure marker** | `/var/opt/nio/aggregations/snifraud.${probe}.${YMD_HM}.0.lz4.failed` |

### rdna_services / rdna_up / rdna_segment_services / rdna_segment_up
| | Path |
|---|---|
| **Input** | `/var/opt/nio/rdna/1m/${COUNTERS_SCHEMA}.log.${NIO_TIMESTAMP}` |
| **Intermediate** | `/var/opt/nio/rdna/aggr_30m/${COUNTERS_SCHEMA}.log.${NIO_TIMESTAMP}.csv.tmp` |
| **Output** | `/var/opt/nio/rdna/aggr_30m/${COUNTERS_SCHEMA}.${probe}.${YMD_HM}.lz4` |
| **Note** | Delays 31 minutes before processing; creates empty input if missing |

---

## NLIVE — Day

### preaggregate
| | Path |
|---|---|
| **Input** | `/var/opt/nio/historical/30m/*.log.${day_start}` |
| **Intermediate** | `/var/opt/nio/historical/tmp/${YMD}/` |
| **Output** | `/var/opt/nio/historical/1d/*.log.${month_start}` |
| **Output (parquet)** | `/var/opt/nio/historical/1d/parquet/` |
| **Note** | Triggered at 23:30 only; performs 30m→1d aggregation |

### userkey
| | Path |
|---|---|
| **Input** | `/var/opt/nio/log/live/user.flow_device_id.log.${NIO_TIMESTAMP}` |
| **Output** | `/var/opt/nio/aggregations/scv.userkey.${YMD}.${probe}.${NETWORK_TYPE}.log.lz4` |
| **Log** | `/var/opt/nio/log/scv_nlive.log` |
| **Note** | SCV feature; notifies MRS via `task -import-broker` |

---

## MRS — 1m

### user / user1m / user_inc
| | Path |
|---|---|
| **Input** | `/var/opt/nio/feeds/nio/diameter/1m/${YYYYMDHH}/diameter_unique_users_*.1m.*.csv` |
| **DB tables** | `subscribers_total`, `subscribers_by_rdir_rcountry_rop_signalling` |

### events
| | Path |
|---|---|
| **Input** | `/var/opt/nio/feeds/events/1m/${YYYYMMDD}/events_event_id_nssai_*.csv` |
| **DB tables** | `counters_by_event_nssai`, `subscribers_by_event_nssai` |

### active_dns
| | Path |
|---|---|
| **Input** | DNS active probe data (1m granularity) |

### rdna_cp / rdna_timeline
| | Path |
|---|---|
| **Input** | `/var/opt/nio/feeds/nio/report-YYYYmm/rdna_cp/${YYYYMMDD}/day/rdna_user_rdir_rcountry_roperator_*.tmp` |
| **Output** | `/var/opt/nio/feeds/nio/report-YYYYmm/rdna_cp/${YYYYMMDD}/day/rdna_user_rdir_rcountry_roperator_*.csv` (sorted) |
| **Temp** | `/var/opt/nio/tmp/` |

---

## MRS — 5m

### user
| | Path |
|---|---|
| **Input** | `/var/opt/nio/feeds/nio/active_subs/5m/${YYYYMMDD}/active_subs_overall-*.csv` |
| **Input** | `/var/opt/nio/feeds/nio/diameter/5m/${YYYYMDHH}/diameter_unique_users_*.5m.*.csv` |

### alerts
| | Path |
|---|---|
| **Output** | `/var/opt/nio/alerts/5m/${YYYYMMDDHH}/{apn\|rat\|segment\|...}-*.csv` |

### rdna_cp / rdna_dns / rdna_segment_cp / rdna_ssi_sqi / rdna_timeline
| | Path |
|---|---|
| **Input** | RDNA feed data at 5m granularity |

---

## MRS — Unit (30-minute)

### tls
| | Path |
|---|---|
| **Input** | Ncore TLS outputs (lz4 compressed, copied to MRS) |
| **Output** | `/var/opt/nio/aggregations/scv.machines.${YMD_HM}.mrs.{mobile\|fixed}.json` |
| **Output** | `/var/opt/nio/aggregations/scv.tls.{type}.${YMD_HM}.*.{network}.*.csv.lz4` (sharded) |
| **Log** | `/var/opt/nio/log/scv_mrs.log` |

### ottcall
| | Path |
|---|---|
| **Input** | Ncore ottcall outputs (copied to MRS) |
| **Output** | `/var/opt/nio/feeds/nio/report-YYYYmm/ottcall/${YYYYMMDD}/ottcall_{internal\|external}_*.csv` |
| **DB tables** | `counters_by_ott_app_voip`, `subscribers_by_ott_app_voip` |

### user
| | Path |
|---|---|
| **Input** | `/var/opt/nio/feeds/nio/diameter/30m/${YYYYMMDD}/diameter_*.csv` |
| **Input** | `/var/opt/nio/feeds/nio/active_subs/30m/${YYYYMMDD}/active_subs_overall-*.csv` |
| **Input** | `/var/opt/nio/alerts/30m/dns_active.user-*.csv` |
| **Config** | `/etc/opt/nio/maps/config/scopemap.json`, `/opt/nio/share/etc/mcc-mnc.json` |
| **Output** | `/opt/nio/share/etl/conf/operator-groups.json` |

### http
| | Path |
|---|---|
| **Input** | `/var/opt/nio/feeds/nio/report-YYYYmm/http_summary_rat_*.csv` |
| **DB tables** | `counters_by_http_summary_rat` |

### nlive
| | Path |
|---|---|
| **Input** | `/var/opt/nio/feeds/nio/report-YYYYmm/nlive_rat_*.csv` |
| **DB tables** | `counters_by_rat` |

### events
| | Path |
|---|---|
| **Config** | `/opt/nio/share/etl/conf/pois.json` → `pois_30m.json` |
| **Config** | `/opt/nio/share/etl/conf/events.json` → `events_30m.json` |
| **Config** | `/opt/nio/share/etl/conf/active_events.txt`, `active_event_id_pois.txt` |

### alerts
| | Path |
|---|---|
| **Output** | `/var/opt/nio/alerts/30m/{*}/{apn\|rat\|segment\|...}-*.csv` |

### flows_rdna
| | Path |
|---|---|
| **Input** | `/var/opt/nio/feeds/nio/report-YYYYmm/flows_rdna/${YYYYMMDD}/30m/rdna_roaming_direction_*.csv` |
| **DB tables** | `subscribers_by_rdna_rdir`, `subscribers_by_rdna_rdir_rcountry`, `subscribers_by_rdna_rdir_rcountry_roperator` |

### rdna_cp
| | Path |
|---|---|
| **Input** | `/var/opt/nio/feeds/nio/report-YYYYmm/rdna_cp/${YYYYMMDD}/30m/rdna_protocol_iface_rdir_*.csv` |
| **DB tables** | `subscribers_by_rdna_prt_iface_rdir`, `subscribers_by_rdna_prt_iface_rr`, `subscribers_by_rdna_prt_iface_rrr` |

### Standard preaggregator sources (chatacct, competitors, cookie, mobilestores, search, sshproxyfraud, torrent, useridentity, userinfo, vsa, youtube)
| | Path |
|---|---|
| **Input** | Ncore outputs from `/var/opt/nio/aggregations/<source>.*.csv` (copied to MRS) |
| **Output** | MRS cube aggregation merges all probe files |

---

## MRS — Hour

### user
| | Path |
|---|---|
| **Input** | `/var/opt/nio/dns_active/${YYYY-MM-DD}/dns_active.{overall\|scope_*}-*.csv` |
| **Input** | `/var/opt/nio/feeds/nio/diameter/1h/${YYYYMMDD}/diameter_unique_users_*.1h.*.csv` |

### alerts
| | Path |
|---|---|
| **Output** | `/var/opt/nio/alerts/1h/{apn\|rat\|...}-*.csv` |

### usage
| | Path |
|---|---|
| **Input** | `/var/opt/nio/usage/hour/${YYYYMMDD}/usage-*.tmp` |
| **Output** | `/var/opt/nio/usage/hour/${YYYYMMDD}/usage-*.csv` (sorted) |

### flows / flows_rdna / http
| | Path |
|---|---|
| **Note** | Hour-level aggregation from unit data via `db_aggregation_tool3` |

---

## MRS — Day

### user
| | Path |
|---|---|
| **Input** | `/var/opt/nio/feeds/nio/diameter/1d/${YYYYMMDD}/diameter_unique_users_*.1day.*.csv` |

### alerts
| | Path |
|---|---|
| **Output** | `/var/opt/nio/alerts/1d/{apn\|rat\|...}-*.csv` |

### usage
| | Path |
|---|---|
| **Input** | `/var/opt/nio/usage/day/usage-${YYYYMMDD}.tmp` |
| **Output** | `/var/opt/nio/usage/day/usage-${YYYYMMDD}.csv` (sorted) |

### dmp
| | Path |
|---|---|
| **Input** | `/var/opt/nio/dmp_processor/maid.rolling.${YYYYMMDD}.csv.tmp` |
| **Output** | `/var/opt/nio/dmp_processor/maid.rolling.${YYYYMMDD}.csv` (deduplicated) |

### subintel
| | Path |
|---|---|
| **Input** | `/var/opt/nio/aggregations/mstate.subintel-imsi-state-dump.${YMD}.ncores_merged.{mobile\|fixed}.log` |
| **Output** | `/var/opt/nio/aggregations/scv.subintel-imsi-state-dump.${YMD}.ncores_merged.{mobile\|fixed}.log.lz4` |
| **Note** | Notifies SCV broker via `task -import-scv-broker` |

### postday
| | Path |
|---|---|
| **Note** | Aggregation cubes for roamers IMSI volume and RABM signalling volume |

---

## MRS — Week

### scp / usage / user / useridentity / database
| | Path |
|---|---|
| **Note** | Weekly rollups and SCV/SCP processing; database maintenance tasks |

---

## MRS — Month

### scp
| | Path |
|---|---|
| **Config** | `/etc/opt/nio/maps/config/scopes.json`, `/etc/opt/nio/maps/config/scopemap.json` |
| **Input** | `/var/opt/nio/feeds/nio/report-YYYYmm/usage_subs_YYYYmm.csv` |
| **Input** | `/var/opt/nio/feeds/scp/churn/YYYYmm/locations_YYYYmm.csv` |
| **Output** | `/var/opt/nio/feeds/scp/churn/YYYYmm/subs_overall_YYYYmm.csv` |
| **Output** | `/var/opt/nio/feeds/scp/churn/YYYYmm/churn_overall_YYYYmm.csv` |

### dci
| | Path |
|---|---|
| **Input** | `/var/opt/nio/feeds/dci/month/${datasource}.${YYYY-MM}.raw.merged` |
| **Output** | `/var/opt/nio/feeds/dci/month/${datasource}.${YYYY-MM}.raw.unique` (deduplicated) |

### database
| | Path |
|---|---|
| **Note** | DB maintenance tasks (partition management, aggregation) |

---

## MRS_SHARD — Unit/Hour/Day

### flows
| | Path |
|---|---|
| **Input** | `/var/opt/nio/state/sharding/flows/flows-{interval}-${YMD_HM}/${hash}/${hostname}/` |
| **Config** | `/etc/opt/nio/maps/config/priority_apps.txt` |
| **Note** | Signals MRS via `task -import-mrs-dw` with `Complete` flag |

### http
| | Path |
|---|---|
| **Input** | `/var/opt/nio/state/sharding/http/http-{interval}-${YMD_HM}/${hash}/${hostname}/` |
| **Output** | `/var/opt/nio/aggregations/http/${YYYY-MM-DD}/` (new format) |
| **Output (legacy)** | `/var/opt/nio/aggregations/http.${probe}.*.lz4` (old format) |

### usage (hour/day)
| | Path |
|---|---|
| **Input** | `/var/opt/nio/usage/hour/${YMD}/usage-*.tmp` |
| **Output** | `/var/opt/nio/usage/hour/${YMD}/usage-*.csv.partial` (sorted) |
| **Output (sharded)** | `/var/opt/nio/state/sharding/usage/usage-hour-${YMD_HM}/${hash}/usage-*.csv.partial.${hostname}.lz4` |

---

## SCV_SHARD — Unit / Day

### tls_scv_shard
| | Path |
|---|---|
| **Config** | `/etc/opt/nio/analytics.json` (scv section: scopes, rolling_window, filters, workers) |
| **Input** | `/var/opt/nio/feeds/scv/scv.day_merged_matches.${DATE}.csv.filtered` (rolling window) |
| **Output (unit)** | `/var/opt/nio/aggregations/scv_matches/${YMD}/scv.unit_merged_matches.${YMD}-${HH}-${MM}.csv` |
| **Output (unit agg)** | `/var/opt/nio/feeds/scv/tmp_shard/scv.day_rolling_merged_matches.partial.${hostname}.${YMD}.csv` |
| **Output (day)** | `/var/opt/nio/feeds/scv/scv.day_merged_matches.${YMD}.csv` |
| **Log** | `/var/opt/nio/log/scv_shard_${interval}.log` |

---

## SCV_MASTER — Day

### scv
| | Path |
|---|---|
| **Input** | `/var/opt/nio/aggregations/scv.userkey.${YMD}.*.fixed.log.lz4` (userkey from fixed probes) |
| **Input** | `/var/opt/nio/aggregations/mobile_user_info_filtered_unique.csv` |
| **Input** | `/var/opt/nio/feeds/scv/tmp/scv.matches_scv_master.final.csv` |
| **Config** | `/etc/opt/nio/scv.blacklist.device.txt` |
| **Output** | `/var/opt/nio/feeds/scv/tmp/user_mobile_to_fixed_map.csv` |
| **Output** | `/var/opt/nio/feeds/scv/home_analytics.transitions.${direction}.${YMD}.log` |
| **Output** | `/var/opt/nio/aggregations/scv/${YMD}/` |
| **Log** | `/var/opt/nio/log/scv_master_${interval}.log` |
| **Temp** | `/var/opt/nio/tmp/` (sorting, 30% memory) |

---

## BIG_DATA — Day

### dci_ds
| | Path |
|---|---|
| **Input** | `/var/opt/nio/aggregations/netflix.chunks.*.${YMD}-*.0.csv` (from ncore) |
| **Config** | `/etc/opt/nio/analytics.json` (dci section: enabled, workers, thresholds) |
| **Intermediate** | `/var/opt/nio/tmp/dci.${YMD}.${worker_id}.csv` (split by user modulo) |
| **Intermediate** | `/var/opt/nio/tmp/dci.${YMD}/` (matching output dir) |
| **Output** | `/var/opt/nio/feeds/dci/day/dci.${YMD}.matched` (raw matches) |
| **Output** | `/var/opt/nio/feeds/dci/day/dci.${YMD}.matched_filtered` (score-filtered) |
| **Output** | `/var/opt/nio/feeds/dci/day/dci.${YMD}.0.csv` (final for MRS) |

---

## Common Patterns

**Standard ncore preaggregator sources** (chatacct, competitors, cookie, mobilestores, search, sshproxyfraud, torrent, useridentity, userinfo, vsa, youtube) all follow:
- Input: `/var/opt/nio/log/{raw,layer8}/<input_file>.${NIO_TIMESTAMP}`
- Temp: `/var/opt/nio/aggregations/<source>.${NIO_TIMESTAMP}.tmp`
- Output: `/var/opt/nio/aggregations/<source>.${probe}.${YMD_HM}.0.csv`
- Failure: `/var/opt/nio/aggregations/<source>.${probe}.${YMD_HM}.0.csv.failed`

**LZ4 compression flags:** `-3 -fq --content-size` (fast, force, quiet)

**Failure recovery:** `.failed` symlinks mark failed operations; backlog scripts retry with ~4h lookback

**Sorting:** `LC_COLLATE=C LC_ALL=C sort` with 40% memory, temp dir `/var/opt/nio/tmp/`
