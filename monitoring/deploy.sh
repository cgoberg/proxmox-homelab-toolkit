#!/usr/bin/env bash
# Deploy forge-proxmox-monitoring to one Proxmox host.
#
# Usage:  deploy.sh <host> [--with-gpu]
# Example: deploy.sh root@pve-gpu.local --with-gpu

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <host> [--with-gpu]" >&2
    exit 2
fi

HOST="$1"
shift
WITH_GPU=""
if [[ $# -gt 0 && "$1" == "--with-gpu" ]]; then
    WITH_GPU="--with-gpu"
    shift
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
REMOTE_DIR="/opt/forge-proxmox-monitoring"

echo "[deploy] target: $HOST  gpu=${WITH_GPU:-no}"

# Make sure target dir exists, then rsync source files there.
ssh "$HOST" "mkdir -p $REMOTE_DIR/patches"
rsync -a --delete \
    "$HERE/forge-pve-sensors" \
    "$HERE/forge-gpu-collector" \
    "$HERE/forge-gpu-collector.service" \
    "$HERE/apply-patches.sh" \
    "$HERE/apply-patches.py" \
    "$HERE/revert-patches.sh" \
    "$HERE/99-forge-pve-patches" \
    "$HOST:$REMOTE_DIR/"
rsync -a --delete "$HERE/patches/" "$HOST:$REMOTE_DIR/patches/"

# Install helper script + collector + apt hook on the remote, then patch.
ssh "$HOST" bash -s -- "$WITH_GPU" <<'REMOTE'
set -euo pipefail
WITH_GPU="${1:-}"

# Ensure dependencies. lm-sensors + smartmontools are usually already present.
need_pkgs=()
command -v sensors  >/dev/null 2>&1 || need_pkgs+=(lm-sensors)
command -v smartctl >/dev/null 2>&1 || need_pkgs+=(smartmontools)
if [[ ${#need_pkgs[@]} -gt 0 ]]; then
    apt-get update -y
    apt-get install -y "${need_pkgs[@]}"
fi

install -m 0755 /opt/forge-proxmox-monitoring/forge-pve-sensors /usr/local/bin/forge-pve-sensors
install -m 0755 /opt/forge-proxmox-monitoring/apply-patches.sh   /usr/local/sbin/forge-apply-pve-patches
install -m 0644 /opt/forge-proxmox-monitoring/99-forge-pve-patches /etc/apt/apt.conf.d/99-forge-pve-patches
chmod 0755 /opt/forge-proxmox-monitoring/apply-patches.py
chmod 0755 /opt/forge-proxmox-monitoring/revert-patches.sh

if [[ "$WITH_GPU" == "--with-gpu" ]]; then
    install -m 0755 /opt/forge-proxmox-monitoring/forge-gpu-collector /usr/local/sbin/forge-gpu-collector
    install -m 0644 /opt/forge-proxmox-monitoring/forge-gpu-collector.service /etc/systemd/system/forge-gpu-collector.service
    systemctl daemon-reload
    systemctl enable --now forge-gpu-collector.service
    echo "[deploy] forge-gpu-collector enabled"
fi

# Apply patches via the python script (the bash wrapper just execs python).
/usr/bin/python3 /opt/forge-proxmox-monitoring/apply-patches.py $WITH_GPU
REMOTE

echo "[deploy] $HOST: done"
