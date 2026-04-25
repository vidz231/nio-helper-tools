# Server Role Map

This map is configurable and should be updated when topology changes.

## SSH Pattern

Example:
ssh -i ~/.ssh/id_rsa phu.tran@pocket-ath-mu1.niometrics.com

Host FQDN format:
<host>.niometrics.com

## Mobile Side

- pocket-ath-np1:
  - ncore
  - nlive

- pocket-ath-mu1:
  - mrs
  - scv_shard
  - scv_master

- pocket-ath-mu3:
  - scv_broker
  - scv_shard

## Fixed Side

- pocket-ath-np2:
  - ncore
  - nlive

- pocket-ath-mu2:
  - mrs

## Role Routing Notes

- ncore and nlive produce upstream unit or day artifacts.
- mrs aggregates and prepares cross-probe outputs.
- scv_shard performs shard-level matching and partial outputs.
- scv_master consumes shard outputs and performs final day-level merge logic.
- scv_broker is used for brokered handoff paths in scv flows.

## Selection Rules

When the user asks for a check, resolve host like this:
1. If host is explicit, use that host.
2. If only role is provided, pick from this map and ask the user if multiple hosts match.
3. If mobile or fixed is specified, constrain to that side.
