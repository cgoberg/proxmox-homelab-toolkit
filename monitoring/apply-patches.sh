#!/usr/bin/env bash
# Forge Proxmox monitoring patches — idempotent installer.
#
# Patches /usr/share/perl5/PVE/API2/Nodes.pm and
# /usr/share/pve-manager/js/pvemanagerlib.js to expose temperature + (on hosts
# with NVIDIA GPUs) GPU usage/VRAM data in the node Summary view.
#
# Safe to re-run. Strips existing FORGE PATCH markers before re-inserting, so
# it self-heals after package upgrades that overwrote our changes.
#
# Usage:  apply-patches.sh [--with-gpu]
#
# The actual implementation lives next to deploy.sh at
# /opt/forge-proxmox-monitoring/apply-patches.py — this thin wrapper is
# installed as /usr/local/sbin/forge-apply-pve-patches by deploy.sh and is
# what the apt DPkg::Post-Invoke hook calls.

set -euo pipefail
# Resolve relative to this script's directory when run from the source tree,
# otherwise fall back to the canonical install location.
HERE="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$HERE/apply-patches.py" ]]; then
    exec /usr/bin/python3 "$HERE/apply-patches.py" "$@"
elif [[ -f /opt/forge-proxmox-monitoring/apply-patches.py ]]; then
    exec /usr/bin/python3 /opt/forge-proxmox-monitoring/apply-patches.py "$@"
else
    echo "ERROR: apply-patches.py not found in $HERE or /opt/forge-proxmox-monitoring/" >&2
    exit 1
fi
