# nio-conf-templates: How It Works + Validation Guide

## Overview

`nio-conf-templates` is a repository containing **Cheetah template files** (`.tmpl`) that generate the actual configuration files used on NIO servers (ncore probes, MRS, analytics machines, etc.).

When you change a `.tmpl` file and deploy it, the template engine reads the customer's `nio.json` (the master configuration), renders the template with the customer-specific values, and produces the final config file (e.g., `/etc/sysconfig/ncore`).

---

## Architecture (How Config Flows from Code to Server)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Developer's Machine                                                  │
│                                                                      │
│   nio-conf-templates repo                                            │
│   ├── conf-templates.d/           ← Cheetah .tmpl files             │
│   │   ├── defaults.tmpl           ← Default values for all keys     │
│   │   ├── ncore.tmpl              ← Generates /etc/sysconfig/ncore  │
│   │   ├── analytics.json.tmpl     ← Generates analytics.json        │
│   │   └── ...                                                        │
│   ├── conf-templates-utils.d/     ← Python utilities for templates  │
│   ├── etc/                        ← Remote schema validation        │
│   ├── scripts/                    ← Deployment helper scripts       │
│   └── tests/                      ← Template syntax checks          │
└─────────────────────────────────────────────────────────────────────┘
         │
         │  git push → Jenkins builds RPM
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Jenkins CI                                                            │
│                                                                       │
│   Builds: nio-conf-templates-X.Y.Z.rpm                               │
│   Publishes to: internal YUM/DNF repository                          │
└─────────────────────────────────────────────────────────────────────┘
         │
         │  yum update nio-conf-templates
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ MRS Server (e.g., pocket-ath-mu1)                                    │
│                                                                       │
│   RPM installs templates to:                                         │
│     /opt/nio/share/conf-templates/                                   │
│                                                                       │
│   nio.json lives at:                                                 │
│     /etc/opt/nio/conf/nio.json                                       │
│                                                                       │
│   To render templates → actual config files:                         │
│     sudo /opt/nio/bin/conf regenerate                                │
│                                                                       │
│   To push config to all probes (ncore machines):                     │
│     sudo /opt/nio/bin/conf sync                                      │
│     OR: scripts/conf_sync.sh (calls API: POST /v0/conf/sync_probes) │
└─────────────────────────────────────────────────────────────────────┘
         │
         │  conf sync pushes rendered configs to each machine
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Probe/ncore Machine (e.g., pocket-ath-nc1)                           │
│                                                                       │
│   Receives rendered config at:                                       │
│     /etc/sysconfig/ncore        ← from ncore.tmpl                   │
│     /etc/opt/nio/analytics.json ← from analytics.json.tmpl          │
│                                                                       │
│   Restart service to apply:                                          │
│     sudo systemctl restart ncore                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Concepts

### 1. Cheetah Templates (`.tmpl` files)

Templates use Python's Cheetah syntax:
- `$variable` — substitutes a value from nio.json
- `#if ... #else if ... #else ... #end if` — conditional logic
- `#set local $var = ...` — define a local variable
- `#for ... #end for` — loops
- `##` — single-line comment

### 2. `nio.json` (Master Configuration)

Located at `/etc/opt/nio/conf/nio.json` on the MRS machine. This is the single source of truth for all deployment configuration. It contains:
- `nio.machines` — list of all machines with their roles and properties
- `nio.customer_type` — "telco" or "enterprise"
- Per-machine settings like `probe_type`, `is_ncore`, `hostname`, etc.

Example machine entry in nio.json:
```json
{
  "nio": {
    "machines": [
      {
        "hostname": "pocket-ath-nc1",
        "is_ncore": true,
        "probe_type": "mobile"
      },
      {
        "hostname": "pocket-ath-nc2",
        "is_ncore": true,
        "probe_type": "fixed"
      }
    ]
  }
}
```

### 3. `defaults.tmpl` (Default Values)

Defines the default value for every key that can appear in nio.json. If a key is not set in nio.json, the template uses the default. Format:
```python
('nio.machines.*.probe_type', 'default'),
```
This means if `probe_type` is not set for a machine, it defaults to `"default"`.

### 4. How `ncore.tmpl` Uses Machine-Level Config

At the top of `ncore.tmpl`:
```python
#set $machine_is_ncore = $hostname in [$x.hostname for $x in $nio.machines if $x.is_ncore]
#set local $machines_dict = { $m["hostname"]: $m for $m in $nio.machines }
#set local $probe_type = $machines_dict.get($hostname, {}).get("probe_type", "default")
```

This means: for the CURRENT machine being configured (identified by `$hostname`), look up its `probe_type` value from the machines list. Then use it in conditionals:

```python
#if $probe_type == "fixed"
NIO_USERS_LOOKUP_TYPE="user"
#else if $probe_type == "mobile"
NIO_USERS_LOOKUP_TYPE="imsi"
#else if $nio.customer_type == "telco"
NIO_USERS_LOOKUP_TYPE="imsi"
#else
NIO_USERS_LOOKUP_TYPE="user"
#end if
```

---

## What DNA-15382 Changed (probe_type per machine)

**Problem:** Previously, the ncore template only had a global `customer_type` ("telco" or "enterprise") to decide between mobile vs fixed behavior. For customers that have BOTH mobile AND fixed probes on the same pocket (like Telkomsel), we needed per-machine control.

**Solution:** Added `probe_type` as a per-machine field with three possible values:
| Value | Meaning |
|-------|---------|
| `"default"` | Falls back to old customer_type logic (backward compatible) |
| `"mobile"` | Force mobile behavior (IMSI-based lookup, GTP-C enabled) |
| `"fixed"` | Force fixed/enterprise behavior (user-based lookup, RADIUS plain mode) |

**Files changed:**
1. `conf-templates.d/defaults.tmpl` — Added `('nio.machines.*.probe_type', 'default')`
2. `conf-templates.d/ncore.tmpl` — Changed all `#if $nio.customer_type == "enterprise"` checks to `#if $probe_type == "fixed" or ($probe_type == "default" and $nio.customer_type == "enterprise")`

**Backward compatibility:** If `probe_type` is not set (or set to `"default"`), the old `customer_type` logic applies. Existing deployments are unaffected.

---

## Validation Procedure (Step by Step)

### Prerequisites
- SSH access to the target pocket's MRS machine
- `sudo` access (or `niomaint` user)
- The new RPM is available in the YUM repo (Jenkins build completed)

### Step 1: Check Current RPM Version on the Server

```bash
# SSH into the MRS machine
ssh <user>@<mrs-hostname>

# Check installed version
rpm -q nio-conf-templates
```

### Step 2: Update the RPM

```bash
# Update to the latest version
sudo yum update nio-conf-templates -y

# Verify new version
rpm -q nio-conf-templates
```

### Step 3: Verify the Template Files Were Updated

```bash
# Check that the new probe_type logic exists in ncore.tmpl
grep -n "probe_type" /opt/nio/share/conf-templates/ncore.tmpl | head -10

# You should see lines like:
#   5:#set local $probe_type = $machines_dict.get($hostname, {}).get("probe_type", "default")
#   59:#if $probe_type == "fixed"
#   61:#else if $probe_type == "mobile"
```

### Step 4: Check Current nio.json Machine Configuration

```bash
# View machines list and their probe_type settings
jq '.nio.machines[] | {hostname, is_ncore, probe_type}' /etc/opt/nio/conf/nio.json
```

If `probe_type` is not set for a machine, it will default to `"default"` (backward compatible, no behavior change).

### Step 5: Regenerate Configuration (Dry Run)

```bash
# Preview what would be generated WITHOUT actually writing files
sudo /opt/nio/bin/conf regenerate --dry-run 2>&1 | head -50

# Or generate and diff against current:
sudo /opt/nio/bin/conf regenerate --diff
```

### Step 6: Validate the Rendered ncore Config

```bash
# After regeneration, check the actual rendered output
# For a specific ncore machine, look at what NIO_USERS_LOOKUP_TYPE will be
grep "NIO_USERS_LOOKUP_TYPE\|NIO_RADINTEL_RADIUS_PLAIN\|NIO_GTPCINTEL_ENABLE" /etc/sysconfig/ncore

# Expected for mobile probe_type:
#   NIO_USERS_LOOKUP_TYPE="imsi"
#   NIO_RADINTEL_RADIUS_PLAIN is NOT set (GTP-C enabled)

# Expected for fixed probe_type:
#   NIO_USERS_LOOKUP_TYPE="user"
#   NIO_RADINTEL_RADIUS_PLAIN=true
#   NIO_GTPCINTEL_ENABLE=false
```

### Step 7: Sync Configuration to Probes

```bash
# Push the regenerated config to all ncore machines
sudo /opt/nio/bin/conf sync
```

### Step 8: Verify on the Probe Machine

```bash
# SSH into the ncore machine
ssh <user>@<ncore-hostname>

# Check the rendered config arrived
grep "NIO_USERS_LOOKUP_TYPE" /etc/sysconfig/ncore
```

### Step 9: Restart ncore (If Needed)

**IMPORTANT:** Only restart if you actually changed a value that affects this machine. If `probe_type` is "default" and the customer_type hasn't changed, the rendered output is identical — no restart needed.

```bash
# On the ncore machine
sudo systemctl restart ncore

# Verify it started cleanly
sudo systemctl status ncore
journalctl -u ncore --since "1 min ago" | tail -20
```

---

## Troubleshooting

### Problem: Template Rendering Fails

```bash
# Check for syntax errors in template
sudo /opt/nio/bin/conf regenerate 2>&1 | grep -i "error\|traceback"

# Common issues:
# - Cheetah syntax error (missing #end if, wrong variable name)
# - Missing key in nio.json that the template expects
```

### Problem: probe_type Not Taking Effect

1. Verify nio.json has the value set:
```bash
jq '.nio.machines[] | select(.hostname == "YOUR_NCORE_HOSTNAME") | .probe_type' /etc/opt/nio/conf/nio.json
```

2. If it returns `null`, the value isn't set → it will use the "default" fallback (customer_type logic).

3. To set it, edit nio.json or use the API:
```bash
# View current config through API
curl -s http://localhost:8080/v0/conf | jq '.nio.machines'
```

### Problem: Config Not Reaching the Probe

```bash
# Check conf sync logs
sudo cat /var/opt/nio/log/conf.log | tail -20

# Manually trigger sync
sudo /opt/nio/bin/conf sync

# Check if the probe is reachable from MRS
ssh <ncore-hostname> "cat /etc/sysconfig/ncore | grep NIO_USERS"
```

### Problem: ncore Won't Start After Config Change

```bash
# Check ncore logs
sudo journalctl -u ncore -n 50

# Common issue: conflicting settings
# e.g., NIO_GTPCINTEL_ENABLE=false but GTP-C interfaces are configured
# This is expected for fixed probes — they don't have GTP-C traffic
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `rpm -q nio-conf-templates` | Check installed template version |
| `sudo yum update nio-conf-templates` | Update templates RPM |
| `sudo /opt/nio/bin/conf regenerate` | Render templates → config files |
| `sudo /opt/nio/bin/conf regenerate --diff` | Show what would change |
| `sudo /opt/nio/bin/conf sync` | Push config to all machines |
| `jq '.nio.machines' /etc/opt/nio/conf/nio.json` | View machine list |
| `grep probe_type /opt/nio/share/conf-templates/ncore.tmpl` | Verify template has the change |
| `cat /etc/sysconfig/ncore` | View rendered ncore config |

---

## File Locations Reference

| Path | Description |
|------|-------------|
| `/opt/nio/share/conf-templates/` | Installed .tmpl files (from RPM) |
| `/etc/opt/nio/conf/nio.json` | Master configuration (input to templates) |
| `/etc/sysconfig/ncore` | Rendered ncore config (output of ncore.tmpl) |
| `/etc/opt/nio/analytics.json` | Rendered analytics config |
| `/var/opt/nio/log/conf.log` | Configuration sync log |
| `/opt/nio/bin/conf` | The conf tool (regenerate/sync) |
