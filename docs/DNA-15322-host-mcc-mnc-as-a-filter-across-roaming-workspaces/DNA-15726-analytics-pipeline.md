---
epic: DNA-15322
story: DNA-15726
title: "ANA: Support all combinations with host MCC MNC in ANA pipeline for roaming WS"
repository_state: DRAFT_PR_OPEN
jira_state: UNVERIFIED
last_repository_verification: 2026-08-08
primary_repository: nio-analytics
---

# DNA-15726: Analytics pipeline

## State

Repository state: **DRAFT_PR_OPEN** on `feature/dna-15322-host-network` from `origin/master`.

Draft PRs: [nio-analytics #2081](https://github.com/mobeande/nio-analytics/pull/2081) and [nio-api3 #1182](https://github.com/mobeande/nio-api3/pull/1182).

Jira workflow state: **UNVERIFIED** because the authenticated Jira session was not available to Codex.

Runtime deployment state: **UNVERIFIED**.

Merged Analytics work provides ten base Host MCC-MNC aggregation combinations.

The draft implementation adds database persistence, higher database granularities, retention registration, API combinations, and focused tests.

RPM proof and pocket-host proof remain runtime validation gates.

## User story

As an Analytics consumer, I want every outbound Host MCC-MNC aggregation persisted and rolled up so KPI queries can isolate one physical host network across supported time granularities.

## Landed foundation

- `rdna_cp`: two combinations at 5m.
- `rdna_segment_cp`: two combinations at 5m.
- `rdna_up`: two combinations at 30m.
- `rdna_segment_up`: two combinations at 30m.
- `rdna_services`: one combination at 30m.
- `rdna_segment_services`: one combination at 30m.
- Packaged NLive RDNA input field: `oimm`.
- NLive preaggregation, MRS report CSV, and PostgreSQL field: `oimm`.
- Historical pre-rename field: `outbound_imsi_mccmnc`.
- Canonical public value example: `311-480`.

The runtime producer implementation is outside the checked repositories, so its emission of the packaged `oimm` contract remains unproven until pocket-host E2E validation.

## Approved implementation: Option 2A

1. Create ten partitioned sidecar PostgreSQL tables matching the ten base aggregation schemas.
2. Include `oimm` in every relevant dimension set and primary key.
3. Expose compatibility through public views while keeping sidecar storage independently partitioned.
4. Add four 5m `postgres_insert3` loaders for CP and Segment CP.
5. Add six 30m `postgres_insert3` loaders for UP, Segment UP, Services, and Segment Services.
6. Add CP database rollups from 5m to hour, day, and month.
7. Add UP and Services database rollups from unit to hour, day, and month.
8. Add retention entries to `nio-analytics/etc/db_expire.conf.json`.
9. Validate replay safety, partition routing, public-view compatibility, metric reconciliation, and outbound-only data.
10. Run targeted tests and `rbuild` before draft review.
11. Run RPM validation and pocket-host E2E validation before final acceptance.

This is Option 2A: partitioned sidecar persistence with public compatibility views.

## Acceptance criteria

### Base persistence

Given all ten Host MCC-MNC base files are produced, when their scheduled database loaders run, then every file is inserted into its matching partitioned table without losing `oimm`.

### Host-network separation

Given two MCC-MNC values belong to the same operator, when their rows are inserted and queried, then each MCC-MNC remains a separate group.

### Public views

Given sidecar partitions contain Host Network rows, when an existing consumer queries the public compatibility view, then it receives the supported columns without depending on sidecar table names.

### Higher granularities

Given valid base rows, when hour, day, and month database rollups execute, then metrics reconcile with their source intervals.

### Replay

Given a completed interval is replayed, when the loader and rollup jobs run again, then duplicate logical rows are not created.

### Retention

Given partitions exceed configured retention, when database expiry runs, then expired partitions are removed without affecting retained intervals.

## Required tests

### Unit tests

- `shouldIncludeOimmInPrimaryKeyWhenCreatingHostTable`
- `shouldSelectFiveMinuteSourceWhenBuildingCpHourlyRollup`
- `shouldSelectUnitSourceWhenBuildingUpHourlyRollup`
- `shouldPreserveHostDimensionWhenBuildingInsertColumns`

### Integration tests

- `givenTwoHostNetworksWhenLoadingBaseCsvThenRowsRemainSeparated`
- `givenBaseRowsWhenRollingUpHourDayMonthThenMetricsReconcile`
- `givenCompletedIntervalWhenReplayingLoaderThenLogicalRowsAreNotDuplicated`
- `givenExpiredPartitionsWhenRunningDbExpireThenOnlyExpiredDataIsRemoved`

## Scope boundary

This story owns Analytics cube consumption, PostgreSQL persistence, database rollups, retention, and Analytics validation.

Public API schema, enumeration, alert templates, and frontend behavior require their owning stories and repositories.

Enumeration production and discovery are tracked by [DNA-15727](DNA-15727-enumerations.md).

## Diagrams

- [Approved implementation architecture](diagrams/dna-15322-approved-implementation.svg)
- [Architecture and remaining-work map](diagrams/dna-15322-architecture-and-remaining-work.svg)
- [Repository-grouped sequence](diagrams/dna-15726-15729-sequence.svg)
- [Enumeration sequence with repository boundaries](diagrams/dna-15727-enumeration-sequence.svg)
