---
epic: DNA-15322
story: DNA-15729
title: "Alerts: Support new combinations with host MCC MNC field in Alerts"
repository_state: DRAFT_PR_OPEN
jira_state: UNVERIFIED
last_repository_verification: 2026-08-08
primary_repository: nio-conf-templates
supporting_repositories:
  - nio-analytics
  - nio-python3-libs
  - nio-api3
---

# DNA-15729: Alerts support

## State

Repository state: **DRAFT_PR_OPEN** on `feature/dna-15322-host-network` from `origin/master`.

Draft PRs: [nio-analytics #2081](https://github.com/mobeande/nio-analytics/pull/2081), [nio-api3 #1182](https://github.com/mobeande/nio-api3/pull/1182), [nio-python3-libs #191](https://github.com/mobeande/nio-python3-libs/pull/191), and [nio-conf-templates #1429](https://github.com/mobeande/nio-conf-templates/pull/1429).

Jira workflow state: **UNVERIFIED** because the authenticated Jira session was not available to Codex.

Runtime deployment state: **UNVERIFIED**.

Analytics provides Host MCC-MNC base files for all six pipeline families.

The hourly cube stage already produces three Host Network day files for UP, Services, and Segment Services.

The draft implementation adds shared alert templates, dimension registration, alert-ring persistence, API information mapping, and focused tests.

The implemented alert matrix is the exact three existing day outputs at interval `86400`.

## User story

As a network operations user, I want alert rules scoped to an outbound Host Network so degradation on one physical MCC-MNC can trigger an alert without mixing traffic from other networks.

## Naming contract

| Layer | Name or value |
|---|---|
| Packaged NLive RDNA input field | `oimm` |
| NLive preaggregation and MRS file field | `oimm` |
| Historical pre-rename field | `outbound_imsi_mccmnc` |
| Public dimension | `host_mcc_mnc` |
| Internal alert-ring column | `d_oimm` |
| Public alert-ring field | `d_host_mcc_mnc` |
| Canonical value example | `311-480` |
| Display label example | `Verizon (311-480)` |

`oimm` and `d_oimm` must remain internal.

`roaming_plmn` must not be treated as equivalent Host Network support.

The runtime producer implementation is outside the checked repositories, so its emission of the packaged `oimm` contract remains unproven until pocket-host E2E validation.

## Repository ownership

### `nio-conf-templates`

- Create new shared Host Network alert templates.
- Add exact file, dimension, metric, interval, catch-up, and tag definitions.
- Include the templates in `nio-alerts.json.tmpl` under the correct RDNA feature guards.
- Preserve valid comma behavior for every enabled and disabled template combination.

### `nio-python3-libs`

- Add the internal `oimm` alert dimension and map it to the public `host_mcc_mnc` contract.
- Generate the physical `d_oimm` ring column and expose it as `d_host_mcc_mnc` through the API boundary.
- Update alert formatter expectations and mapping tests.

### `nio-analytics`

- Add the `alerts_rings.d_oimm` migration required by the exact CSV-header contract.
- Provide any missing Host alert output combination required by the final Jira matrix.

### `nio-api3`

- Add Host Network alert information mapping when owned by this story.
- Expose Host Network through alert availability and rule contracts when the rendered configuration supports it.
- Preserve `host_mcc_mnc` as the public name.

### Frontend workspace

- Offer Host Network only when Roaming Direction is Outbound.
- Display `Network Name (MCC-MNC)`.
- Support selecting a specific Host Network when defining a threshold.

Host value enumeration and display-label resolution are tracked by [DNA-15727](DNA-15727-enumerations.md).

## Story implementation

1. Add the complete Alerts runtime path for the Host Network combinations produced by Analytics.
2. Keep `oimm` as the raw file and alert-ingestion dimension.
3. Expose Host Network as the product label and reuse the DNA-15727 resolved display contract.
4. Add the explicit deployment flag `rdna.host_mcc_mnc.enabled`.
5. Default the flag to `false` so deployments opt in after the coordinated packages are installed.
6. Include Host Network shared templates only when both RDNA and the Host Network flag are enabled.
7. Preserve valid JSON when RDNA, Host Network, partner groups, and generic alerts are enabled in any supported combination.
8. Register only the three existing Host Network day outputs for UP, Services, and Segment Services at interval `86400`.

DNA-15729 is the Alerts story that consumes the approved persistence and enumeration contracts.

It aligns with the MRD deployment-configurability requirement while avoiding partial enablement of an incomplete Alerts path.

## Acceptance criteria

### Template rendering

Given RDNA and Host Network support are enabled, when `nio-alerts.json.tmpl` renders, then every required Host Network combination appears in valid JSON.

### Outbound dependency

Given Roaming Direction is not Outbound, when a user configures an alert, then Host Network is unavailable and cannot be submitted as a dimension.

### Rule evaluation

Given a rule targets `host_mcc_mnc=311-480`, when its KPI threshold is breached, then only rows for `311-480` contribute to that alert.

### Persistence

Given a Host Network alert is generated, when the alert ring is stored and queried, then physical `d_oimm` retains `311-480` and public `d_host_mcc_mnc` returns the resolved display label.

The physical database column is `d_oimm`, and the public API field is `d_host_mcc_mnc`.

### Public presentation

Given `311-480` maps to Verizon, when the alert is returned to the UI, then the user sees `Verizon (311-480)`.

### Feature disablement

Given Host Network support is disabled during deployment, when alert configuration is rendered, then Host Network combinations are not advertised.

## Required tests

### Unit tests

- `shouldExposeHostMccMncWhenRenderingHostAlertTemplate`
- `shouldMapHostMccMncToAlertRingColumnWhenFormattingAlert`
- `shouldRejectHostNetworkWhenRoamingDirectionIsNotOutbound`
- `shouldHideHostCombinationsWhenFeatureIsDisabled`

### Integration tests

- `givenHostAlertTemplatesWhenRenderingNioAlertsThenJsonIsValid`
- `givenHostAlertRuleWhenEvaluatingThresholdThenOnlySelectedNetworkContributes`
- `givenHostAlertWhenPersistingRingThenHostMccMncSurvivesQueryAndExport`
- `givenNonOutboundDirectionWhenCreatingHostAlertThenRequestIsRejected`

## Diagrams

- [Approved implementation architecture](diagrams/dna-15322-approved-implementation.svg)
- [Architecture and remaining-work map](diagrams/dna-15322-architecture-and-remaining-work.svg)
- [Repository-grouped sequence](diagrams/dna-15726-15729-sequence.svg)
- [Enumeration sequence with repository boundaries](diagrams/dna-15727-enumeration-sequence.svg)
