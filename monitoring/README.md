# Forge Proxmox monitoring patches

Adds CPU/GPU/NVMe/disk temperatures to the Proxmox VE 9 node Summary view and,
on hosts with an NVIDIA GPU, adds GPU usage / VRAM / GPU temperature charts
under the existing CPU/Memory charts.

## What it does

| Component | Where | Notes |
|---|---|---|
| `/usr/local/bin/forge-pve-sensors` | every host | Python helper: reads `sensors -j`, `smartctl`, `nvidia-smi` and emits a flat JSON blob |
| `Nodes.pm` sensor injection | every host | adds `forge_sensors` to the `/api2/json/nodes/{node}/status` response |
| `pvemanagerlib.js` StatusView rows | every host | renders CPU/GPU/NVMe/SATA/motherboard temps + (if present) GPU usage/VRAM |
| `/usr/local/sbin/forge-gpu-collector` | GPU hosts only | Perl daemon writing nvidia-smi readings to `/var/lib/rrdcached/db/forge-gpu-9.0/<host>` every 10s |
| `forge-gpu-collector.service` | GPU hosts only | systemd unit with `Restart=always` |
| `Nodes.pm` `gpu_rrddata` method | GPU hosts only | new API endpoint reading the custom RRD via `PVE::RRD::create_rrd_data` |
| `pvemanagerlib.js` GPU charts | GPU hosts only | three `proxmoxRRDChart` panels in the node Summary view |
| `/etc/apt/apt.conf.d/99-forge-pve-patches` | every host | `DPkg::Post-Invoke` hook that re-runs the patcher after package upgrades |

## Layout

```
proxmox-monitoring/
├── README.md
├── deploy.sh                        # rsync + remote install
├── apply-patches.sh                 # thin wrapper around apply-patches.py
├── apply-patches.py                 # idempotent patcher (Python)
├── revert-patches.sh                # restore .forge-orig backups
├── 99-forge-pve-patches             # apt post-invoke snippet
├── forge-pve-sensors                # local sensor probe helper (Python)
├── forge-gpu-collector              # GPU stats collector daemon (Perl)
├── forge-gpu-collector.service      # systemd unit for the collector
└── patches/
    ├── nodes-pm-sensors.snippet.pl
    ├── nodes-pm-gpu-rrddata.snippet.pl
    ├── statusview.snippet.js
    └── summary-gpu-charts.snippet.js
```

## Deployment

```bash
# Hosts with no GPU
./deploy.sh root@pve-no-gpu.local
./deploy.sh root@pve-no-gpu-2.local
./deploy.sh root@pve-dell.local   # Dell OptiPlex 7010: no NVMe, no discrete GPU

# Host with NVIDIA GPU
./deploy.sh root@pve-gpu.local --with-gpu
```

After deployment, hard-reload the Proxmox web UI (Ctrl+Shift+R) to pick up the
new JS. The new rows appear in the node Summary panel, and on GPU hosts three
extra charts appear in the Summary chart column.

## Idempotency & upgrade survival

`apply-patches.py` is the single source of truth. It always:

1. Backs up the original Nodes.pm / pvemanagerlib.js once (`*.forge-orig`).
2. Strips any existing `// BEGIN FORGE PATCH: …` blocks from both files.
3. Re-inserts the current versions of the snippets at well-defined anchors.
4. Runs `perl -c` against the patched Nodes.pm before activating.
5. Atomically replaces the files via `os.replace`.
6. `systemctl reload pveproxy && pvedaemon`.

The apt post-invoke hook re-runs this automatically after `pve-manager` or
`proxmox-widget-toolkit` upgrades, so the patches survive Proxmox updates.

## Reverting

```bash
ssh root@<host> /opt/forge-proxmox-monitoring/revert-patches.sh
# and remove the GPU collector if you set it up:
ssh root@<host> 'systemctl disable --now forge-gpu-collector; rm -f /etc/systemd/system/forge-gpu-collector.service /usr/local/sbin/forge-gpu-collector; systemctl daemon-reload'
```

## Why a custom RRD for GPU stats?

Proxmox's own RRDs (`pve-node-9.0/<host>`) are populated by `pvestatd`, whose
data-source schema is hard-coded in `update_node_status()`. Extending it would
mean modifying `pvestatd.pm`, which gets overwritten by every `pve-manager`
upgrade. The collector writes a parallel RRD at
`/var/lib/rrdcached/db/forge-gpu-9.0/<host>` using the same on-disk format,
which `PVE::RRD::create_rrd_data` reads transparently when invoked via the new
`gpu_rrddata` API method. This keeps our changes orthogonal to pvestatd.

## Anchors used (so future debugging is easy)

The Python patcher uses these textual anchors:

| File | Anchor | Purpose |
|---|---|---|
| Nodes.pm | first bare `        return $res;` line | insert sensor merge block before status return |
| Nodes.pm | `name => 'rrddata'` register_method block | append `gpu_rrddata` method after rrddata closes |
| pvemanagerlib.js | `Ext.define('PVE.node.StatusView', …) height: 350,` | bump panel height |
| pvemanagerlib.js | `itemId: 'version'` row | insert sensor rows immediately above |
| pvemanagerlib.js | `pve-rrd-node` Ext.define closing `});` | append `pve-rrd-gpu` model |
| pvemanagerlib.js | `var rrdstore = Ext.create('Proxmox.data.RRDStore'` | append `forgeGpuRrdStore` |
| pvemanagerlib.js | CPU Usage chart panel block | append GPU chart panels |
