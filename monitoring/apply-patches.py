#!/usr/bin/env python3
"""Forge Proxmox monitoring patches — idempotent installer.

Patches:
  /usr/share/perl5/PVE/API2/Nodes.pm
  /usr/share/pve-manager/js/pvemanagerlib.js

Safe to re-run. Strips existing FORGE PATCH blocks before re-inserting, so it
self-heals after package upgrades. Validates Perl syntax before activating
changes. Atomically replaces target files via mv.

Usage:  apply-patches.py [--with-gpu]
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATCHES = HERE / "patches"

NODES_PM = Path("/usr/share/perl5/PVE/API2/Nodes.pm")
PVEUI_JS = Path("/usr/share/pve-manager/js/pvemanagerlib.js")

def _load_snippet(name: str) -> str:
    """Read a snippet file and normalise: no leading blank lines, exactly one
    trailing newline. This is what the strip regex expects."""
    text = (PATCHES / name).read_text()
    text = text.lstrip("\n").rstrip("\n") + "\n"
    return text


SENSORS_PERL_SNIPPET = _load_snippet("nodes-pm-sensors.snippet.pl")
GPURRD_PERL_SNIPPET = _load_snippet("nodes-pm-gpu-rrddata.snippet.pl")
STATUSVIEW_JS_SNIPPET = _load_snippet("statusview.snippet.js")
GPUCHARTS_JS_SNIPPET = _load_snippet("summary-gpu-charts.snippet.js")

# pve-rrd-gpu Ext data model — inlined here so the data shape stays in lockstep
# with the GPU collector RRD DS names (gpu_usage / gpu_mem_used / gpu_mem_total
# / gpu_temp). No leading/trailing blank lines — the strip regex consumes the
# block exactly.
GPU_MODEL_SNIPPET = (
    "// BEGIN FORGE PATCH: pve-rrd-gpu model\n"
    "Ext.define('pve-rrd-gpu', {\n"
    "    extend: 'Ext.data.Model',\n"
    "    fields: [\n"
    "        'gpu_usage',\n"
    "        'gpu_mem_used',\n"
    "        'gpu_mem_total',\n"
    "        'gpu_temp',\n"
    "        { type: 'date', dateFormat: 'timestamp', name: 'time' },\n"
    "    ],\n"
    "});\n"
    "// END FORGE PATCH: pve-rrd-gpu model\n"
)

GPU_STORE_SNIPPET = (
    "        // BEGIN FORGE PATCH: GPU store\n"
    "        var forgeGpuRrdStore = Ext.create('Proxmox.data.RRDStore', {\n"
    "            rrdurl: '/api2/json/nodes/' + nodename + '/gpu_rrddata',\n"
    "            model: 'pve-rrd-gpu',\n"
    "        });\n"
    "        // END FORGE PATCH: GPU store\n"
)


def log(msg: str) -> None:
    print(f"[forge-patch] {msg}", flush=True)


def die(msg: str, code: int = 1) -> None:
    print(f"[forge-patch] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def backup_once(path: Path) -> None:
    backup = path.with_suffix(path.suffix + ".forge-orig")
    if not backup.exists():
        shutil.copy2(path, backup)
        log(f"backed up {path} -> {backup}")


def strip_blocks(text: str, marker_pairs: list[tuple[str, str]]) -> str:
    """Remove existing FORGE PATCH blocks (for re-application)."""
    for begin, end in marker_pairs:
        pattern = re.compile(
            r"[ \t]*" + re.escape(begin) + r".*?" + re.escape(end) + r"\n",
            re.DOTALL,
        )
        text = pattern.sub("", text)
    return text


def patch_nodes_pm(src: str, with_gpu: bool) -> str:
    src = strip_blocks(
        src,
        [
            ("# BEGIN FORGE PATCH: sensors", "# END FORGE PATCH: sensors"),
            ("# BEGIN FORGE PATCH: gpu_rrddata", "# END FORGE PATCH: gpu_rrddata"),
        ],
    )

    # ----- sensors snippet: insert before the `return $res;` line at the end
    # of the `status` register_method's code block. The status method has
    # exactly one bare `        return $res;` line; we anchor on that.
    status_return_re = re.compile(r"^        return \$res;\n", re.MULTILINE)
    if not status_return_re.search(src):
        raise RuntimeError("Nodes.pm: 'return $res;' anchor not found")
    src = status_return_re.sub(
        SENSORS_PERL_SNIPPET + "        return $res;\n", src, count=1,
    )

    # ----- gpu_rrddata method: insert after the closing }); of the rrddata
    # register_method.
    if with_gpu:
        rrddata_pattern = re.compile(
            r"(    name => 'rrddata',.*?\n\}\);\n)",
            re.DOTALL,
        )
        m = rrddata_pattern.search(src)
        if not m:
            raise RuntimeError("Nodes.pm: rrddata register_method anchor not found")
        insert_at = m.end()
        src = src[:insert_at] + GPURRD_PERL_SNIPPET + src[insert_at:]

    return src


def patch_pveui_js(src: str, with_gpu: bool) -> str:
    src = strip_blocks(
        src,
        [
            ("// BEGIN FORGE PATCH: sensor rows", "// END FORGE PATCH: sensor rows"),
            ("// BEGIN FORGE PATCH: GPU charts", "// END FORGE PATCH: GPU charts"),
            ("// BEGIN FORGE PATCH: GPU store", "// END FORGE PATCH: GPU store"),
            ("// BEGIN FORGE PATCH: pve-rrd-gpu model", "// END FORGE PATCH: pve-rrd-gpu model"),
        ],
    )

    # Strip the inline lifecycle calls (activate/destroy listener additions);
    # they live inside other functions so they can't be wrapped in BEGIN/END
    # markers without breaking JS.
    src = re.sub(
        r"[ \t]*forgeGpuRrdStore\.(?:startUpdate|stopUpdate)\(\);[^\n]*\n",
        "",
        src,
    )

    # ----- bump StatusView height (350 -> 540) to make room for new rows.
    height_re = re.compile(
        r"(Ext\.define\('PVE\.node\.StatusView',\s*\{\s*\n"
        r"\s*extend:\s*'Proxmox\.panel\.StatusView',\s*\n"
        r"\s*alias:\s*'widget\.pveNodeStatus',\s*\n"
        r"\s*)height:\s*\d+,",
    )
    new_src, n = height_re.subn(r"\1height: 540,", src, count=1)
    if n != 1:
        raise RuntimeError("StatusView height anchor not found")
    src = new_src

    # ----- inject sensor rows immediately before the `version` itemId row.
    version_anchor = (
        "        {\n"
        "            itemId: 'version',\n"
        "            colspan: 2,\n"
        "            printBar: false,\n"
        "            title: gettext('Manager Version'),\n"
        "            textField: 'pveversion',\n"
        "            value: '',\n"
        "        },\n"
    )
    if version_anchor not in src:
        raise RuntimeError("StatusView 'version' row anchor not found")
    src = src.replace(version_anchor, STATUSVIEW_JS_SNIPPET + version_anchor, 1)

    if with_gpu:
        # 1) pve-rrd-gpu Ext data model: insert right after the pve-rrd-node
        #    model definition closes.
        model_pattern = re.compile(
            r"(Ext\.define\('pve-rrd-node',\s*\{.*?\}\);\n)",
            re.DOTALL,
        )
        m = model_pattern.search(src)
        if not m:
            raise RuntimeError("pve-rrd-node model anchor not found")
        src = src[: m.end()] + GPU_MODEL_SNIPPET + src[m.end():]

        # 2) GPU RRDStore: insert right after the existing rrdstore for
        #    PVE.node.Summary.
        rrdstore_anchor = (
            "        var rrdstore = Ext.create('Proxmox.data.RRDStore', {\n"
            "            rrdurl: '/api2/json/nodes/' + nodename + '/rrddata',\n"
            "            model: 'pve-rrd-node',\n"
            "        });\n"
        )
        if rrdstore_anchor not in src:
            raise RuntimeError("PVE.node.Summary rrdstore anchor not found")
        src = src.replace(rrdstore_anchor, rrdstore_anchor + GPU_STORE_SNIPPET, 1)

        # 3) GPU chart panels: insert right after the CPU Usage chart panel
        #    inside the Summary items array.
        cpu_chart_pattern = re.compile(
            r"(                        \{\s*\n"
            r"                            xtype: 'proxmoxRRDChart',\s*\n"
            r"                            title: gettext\('CPU Usage'\),.*?\n"
            r"                            store: rrdstore,\s*\n"
            r"                        \},\n)",
            re.DOTALL,
        )
        m = cpu_chart_pattern.search(src)
        if not m:
            raise RuntimeError("CPU Usage chart anchor not found")
        src = src[: m.end()] + GPUCHARTS_JS_SNIPPET + src[m.end():]

        # 4) Wire forgeGpuRrdStore into the Summary panel's activate/destroy
        #    lifecycle. Without this, the store never polls /gpu_rrddata and
        #    the chart panels stay empty.
        activate_anchor = (
            "                    rrdstore.startUpdate();\n"
            "                },\n"
        )
        if activate_anchor not in src:
            raise RuntimeError("rrdstore.startUpdate() activate anchor not found")
        src = src.replace(
            activate_anchor,
            (
                "                    rrdstore.startUpdate();\n"
                "                    forgeGpuRrdStore.startUpdate(); // FORGE PATCH: GPU lifecycle\n"
                "                },\n"
            ),
            1,
        )
        destroy_anchor = (
            "                    rrdstore.stopUpdate();\n"
            "                },\n"
        )
        if destroy_anchor not in src:
            raise RuntimeError("rrdstore.stopUpdate() destroy anchor not found")
        src = src.replace(
            destroy_anchor,
            (
                "                    rrdstore.stopUpdate();\n"
                "                    forgeGpuRrdStore.stopUpdate(); // FORGE PATCH: GPU lifecycle\n"
                "                },\n"
            ),
            1,
        )

    return src


def perl_syntax_ok(path: Path) -> bool:
    try:
        out = subprocess.run(
            ["perl", "-c", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return "syntax OK" in out.stderr
    except Exception as exc:
        log(f"perl -c failed to run: {exc}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-gpu", action="store_true", help="apply GPU charts & API method")
    ap.add_argument("--dry-run", action="store_true", help="print results without overwriting")
    args = ap.parse_args()

    for p in (NODES_PM, PVEUI_JS):
        if not p.is_file():
            die(f"missing {p}; is pve-manager installed?")

    backup_once(NODES_PM)
    backup_once(PVEUI_JS)

    src_pm = NODES_PM.read_text()
    src_js = PVEUI_JS.read_text()

    try:
        new_pm = patch_nodes_pm(src_pm, args.with_gpu)
    except Exception as exc:
        die(f"Nodes.pm patch failed: {exc}")

    try:
        new_js = patch_pveui_js(src_js, args.with_gpu)
    except Exception as exc:
        die(f"pvemanagerlib.js patch failed: {exc}")

    if args.dry_run:
        print(new_pm)
        print("=" * 80)
        print(new_js[:10000])
        return 0

    # Write to temp files in same dir, perl -c the Perl one, then atomic mv.
    tmp_pm = NODES_PM.with_suffix(".forge-tmp")
    tmp_js = PVEUI_JS.with_suffix(".forge-tmp")
    tmp_pm.write_text(new_pm)
    tmp_js.write_text(new_js)
    # Preserve owner/perms from original
    pm_stat = NODES_PM.stat()
    js_stat = PVEUI_JS.stat()
    os.chmod(tmp_pm, pm_stat.st_mode)
    os.chmod(tmp_js, js_stat.st_mode)
    os.chown(tmp_pm, pm_stat.st_uid, pm_stat.st_gid)
    os.chown(tmp_js, js_stat.st_uid, js_stat.st_gid)

    if not perl_syntax_ok(tmp_pm):
        out = subprocess.run(
            ["perl", "-c", str(tmp_pm)],
            capture_output=True, text=True,
        )
        tmp_pm.unlink(missing_ok=True)
        tmp_js.unlink(missing_ok=True)
        die(f"Perl syntax check failed on patched Nodes.pm:\n{out.stderr}")

    # Activate
    os.replace(tmp_pm, NODES_PM)
    os.replace(tmp_js, PVEUI_JS)
    log(f"updated {NODES_PM}")
    log(f"updated {PVEUI_JS}")

    # Reload services
    for svc in ("pveproxy", "pvedaemon"):
        r = subprocess.run(["systemctl", "is-active", "--quiet", svc])
        if r.returncode == 0:
            reload_r = subprocess.run(["systemctl", "reload", svc])
            if reload_r.returncode != 0:
                subprocess.run(["systemctl", "restart", svc], check=True)
                log(f"restarted {svc}")
            else:
                log(f"reloaded {svc}")

    log("done. Hard-reload the browser (Ctrl+Shift+R) to pick up the new JS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
