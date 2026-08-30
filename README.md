# Proxmox Homelab Toolkit

Two practical fixes for the Proxmox machine you can hear and the telemetry you
cannot see.

This repository combines:

- **fan-control tooling** for hardware that Linux `fancontrol` cannot address
  correctly, plus measured example curves for four older Intel/AMD systems;
- **monitoring patches** that add CPU, motherboard, NVMe, SATA, and GPU
  telemetry to the Proxmox VE 9 node summary, including optional NVIDIA RRD
  charts.

Both started as fixes for a mixed-generation homelab. They are published
because the awkward parts are broadly reusable: write-only Dell SMM PWM,
old-style Fintek sysfs paths, Ryzen idle boost spikes, fan stall/restart
measurement, Proxmox UI patch anchoring, and upgrade-surviving reapplication.

## Choose the part you need

### [Fan control](fan-control/README.md)

Use this when `pwmconfig` produces a loud idle curve, ignores the actual fan
controller, or refuses a write-only PWM interface. The included controller
fails hot: an unreadable temperature is treated as 95 °C, shutdown drives all
managed channels to `SAFE_PWM`, and systemd restarts the daemon.

The example configurations are hardware measurements, not universal presets.
Measure your own fan stall points and load temperatures before installing one.

### [Proxmox monitoring](monitoring/README.md)

Use this when you want sensor rows and optional NVIDIA charts in the PVE 9 node
summary. The patcher backs up upstream files once, inserts marked blocks at
known anchors, syntax-checks the Perl API module, and can reapply itself after
package upgrades.

## Read this before installing

Fan control and host UI patches both have real failure modes.

- A bad fan floor can overheat hardware. Test in steps, watch temperatures
  independently, and keep firmware/physical access available.
- The Proxmox monitoring layer modifies distribution-owned Perl and JavaScript
  files. An upstream update can move an anchor or make a patch incompatible.
- `deploy.sh` uses root SSH, installs packages when needed, reloads Proxmox
  services, and uses `rsync --delete` inside its dedicated remote directory.
  Read it before running it.
- The toolkit was measured on specific hardware and Proxmox VE 9. It is not a
  blanket compatibility promise for every board, sensor chip, or PVE release.

Start with the component README, make a recoverable host backup, and test one
machine before rolling anything across a cluster.

## Verification

```bash
python3 -m py_compile monitoring/apply-patches.py monitoring/forge-pve-sensors
bash -n monitoring/*.sh fan-control/forge-fanctl
```

MIT licensed. Issues with a new board/sensor profile are most useful when they
include `sensors -j`, the relevant `/sys/class/hwmon` names, a measured PWM/RPM
sweep, and load temperatures with identifying host details removed.
