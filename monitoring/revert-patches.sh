#!/usr/bin/env bash
# Restore the original Nodes.pm + pvemanagerlib.js from the .forge-orig backups.
set -euo pipefail

for f in /usr/share/perl5/PVE/API2/Nodes.pm /usr/share/pve-manager/js/pvemanagerlib.js; do
    if [[ -f "${f}.forge-orig" ]]; then
        cp -a "${f}.forge-orig" "$f"
        echo "restored $f from .forge-orig"
    else
        echo "no backup found for $f; skipping"
    fi
done

systemctl reload pveproxy 2>/dev/null || systemctl restart pveproxy
systemctl reload pvedaemon 2>/dev/null || systemctl restart pvedaemon
echo "done"
