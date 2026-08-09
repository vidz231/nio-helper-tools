---
epic: DNA-15322
story: DNA-15727
title: "Enumerations support for Host MCC MNC field"
repository_state: DRAFT_PR_OPEN
jira_state: UNVERIFIED
last_repository_verification: 2026-08-08
primary_repository: nio-analytics
supporting_repositories:
  - nio-api3
---

# DNA-15727: Enumerations support

## State

Repository state: **DRAFT_PR_OPEN** on `feature/dna-15322-host-network` from `origin/master`.

Draft PRs: [nio-analytics #2081](https://github.com/mobeande/nio-analytics/pull/2081) and [nio-api3 #1182](https://github.com/mobeande/nio-api3/pull/1182).

Jira workflow state: **UNVERIFIED** because the authenticated Jira session was not available to Codex.

Runtime deployment state: **UNVERIFIED**.

The repositories already provide reusable enumeration storage, scheduling, MCC-MNC dictionary loading, and a dynamic enumeration API.

The draft implementation adds the missing `host_mcc_mnc` enumeration producer, resolver registration, dynamic API allowlist entry, and focused tests.

The existing `roaming_plmn` endpoint is not equivalent because it returns the whole operator dictionary, can group multiple PLMNs under one operator, and does not enumerate Host Network values observed in Analytics traffic.

## User story

As a Roaming user, I want Host Network filter values discovered from observed outbound traffic and displayed as `Network Name (MCC-MNC)` so I can select the exact physical network represented in Analytics data.

## Naming contract

| Layer | Name or value |
|---|---|
| Packaged NLive RDNA input field | `oimm` |
| NLive preaggregation, MRS report CSV, and PostgreSQL field | `oimm` |
| Historical pre-rename field | `outbound_imsi_mccmnc` |
| Public enumeration name | `host_mcc_mnc` |
| Canonical raw value | `311-480` |
| Resolved display value | `Verizon (311-480)` |
| Parent enumeration | `roaming_direction=OUTBOUND` |

`roaming_plmn` must not be reused as the public Host Network enumeration.

The runtime producer implementation is outside the checked repositories, so its emission of the packaged `oimm` contract remains unproven until pocket-host E2E validation.

## Repository ownership

### `nio-analytics`

- Read distinct `oimm` values from the Host MCC-MNC aggregation tables delivered by DNA-15726.
- Restrict Host Network discovery to outbound roaming data.
- Register `host_mcc_mnc` as an enumeration with `roaming_direction` as its parent.
- Resolve each canonical MCC-MNC through the existing MCC-MNC dictionary.
- Persist the canonical value, resolved value, and parent fields in the existing `enumerations` model.
- Define safe behavior for unknown, malformed, and unmapped MCC-MNC values.
- Register any required enumeration calendar or historical recalculation behavior.

### `nio-api3`

- Add `host_mcc_mnc` to the dynamic enumeration allowlist.
- Treat it as a string enumeration with `roaming_direction` as its parent.
- Return both the stable raw value and the resolved display value.
- Preserve parent filtering, search, pagination, and availability behavior.

### UI consumers

- Request `host_mcc_mnc` only when Roaming Direction is Outbound.
- Store and submit `311-480` as the stable filter key.
- Display `Verizon (311-480)` to the user.

## Approved implementation: Option 3A

1. Discover only Host Network values observed in the Analytics Host tables delivered by DNA-15726.
2. Cover the supported Host Network tables while deduplicating the public values.
3. Add Host Network to the parent-aware and resolved enumeration registries.
4. Add or extend a resolver that maps canonical `MCC-MNC` values to `Network Name (MCC-MNC)`.
5. Add `host_mcc_mnc` to the `nio-api3` dynamic enumeration allowlist.
6. Enforce `roaming_direction=OUTBOUND` across enumeration production and API consumption.
7. Preserve an unmapped raw value with the display label `Unknown (<raw>)`.
8. Reuse the existing enumeration history, calendar, and retention behavior.
9. Run focused unit tests and `rbuild` before draft review.
10. Run RPM validation and pocket-host E2E proof before final acceptance.

## Acceptance criteria

### Distinct Host Networks

Given observed outbound rows contain `311-480` and `310-260`, when the Analytics enumerator runs, then both MCC-MNC values are stored as separate `host_mcc_mnc` enumeration values.

### Network-name resolution

Given `311-480` exists in the MCC-MNC dictionary, when the enumeration value is resolved, then its raw value remains `311-480` and its display value is `Verizon (311-480)`.

### Outbound dependency

Given a Host MCC-MNC value exists only in inbound data, when the Analytics enumerator runs, then that value is not advertised as a Host Network option.

### Unknown value handling

Given `999-999` is absent from the MCC-MNC dictionary, when the resolver processes it, then the raw value remains `999-999`, the display value is `Unknown (999-999)`, and the enumeration run succeeds.

### Dynamic API

Given an API request selects `host_mcc_mnc` with parent `roaming_direction=OUTBOUND`, when the dynamic enumeration endpoint is queried, then it returns only matching active Host Network values with raw and resolved forms.

### Search

Given `311-480` resolves to Verizon, when the dynamic enumeration is searched for `Verizon`, then the matching Host Network is returned.

### Historical availability

Given supported historical Host rows exist, when the agreed enumeration recalculation or calendar process runs, then the supported historical intervals become discoverable without creating duplicate logical values.

## Required tests

### Unit tests

- `shouldResolveNetworkNameWhenHostMccMncExistsInDictionary`
- `shouldUseUnknownFallbackWhenHostMccMncIsUnmapped`
- `shouldExcludeInboundValuesWhenEnumeratingHostMccMnc`
- `shouldAllowHostMccMncWhenValidatingDynamicEnumerationName`

### Integration tests

- `givenObservedHostNetworksWhenEnumeratorRunsThenDistinctValuesAreStored`
- `givenOutboundParentWhenQueryingHostEnumerationThenOnlyOutboundValuesAreReturned`
- `givenVerizonSearchWhenQueryingDynamicEnumerationThenResolvedHostNetworkMatches`
- `givenHistoricalHostRowsWhenRecalculatingCalendarThenConfiguredIntervalsAreAvailable`

## Approved decisions

1. Use observed Analytics values only.
2. Use `roaming_direction` as the parent and `OUTBOUND` as the only valid parent value.
3. Resolve known values as `Network Name (MCC-MNC)`.
4. Resolve unknown values as `Unknown (MCC-MNC)` without changing the stable raw value.
5. Keep the internal cube, file, and table field `oimm` and expose the public enumeration name `host_mcc_mnc`.

This is Option 3A: enumerate only Host Networks observed in outbound Analytics data.

It is aligned with the MRD because the UI advertises only Host Networks backed by queryable roaming data and still uses the existing MCC-MNC dictionary for the display name.

## Dependencies

- [DNA-15726 Analytics pipeline](DNA-15726-analytics-pipeline.md) must provide the Host MCC-MNC database tables used as enumeration sources.
- [DNA-15729 Alerts support](DNA-15729-alerts.md) consumes the same public value and display-label contract.

## Diagrams

- [Approved implementation architecture](diagrams/dna-15322-approved-implementation.svg)
- [Architecture and remaining-work map](diagrams/dna-15322-architecture-and-remaining-work.svg)
- [Enumeration sequence with repository boundaries](diagrams/dna-15727-enumeration-sequence.svg)
