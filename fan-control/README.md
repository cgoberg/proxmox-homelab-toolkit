# Proxmox homelab fan control

Silence-first fan tuning for four Proxmox test hosts, tuned 2026-08-30 from
measured PWM→RPM sweeps rather than `pwmconfig` guesses.

## Why the previous setup was louder, not quieter

`pwmconfig` picks `MINTEMP` without knowing the CPU's idle temperature. On
Ryzen, which idles near 50 °C, its default of 25 °C puts the fans most of the
way up the ramp *while the machine is doing nothing*.

fancontrol's curve is:

```
pwm = MINSTOP + (T - MINTEMP) / (MAXTEMP - MINTEMP) × (MAXPWM - MINSTOP)
```

On `Profile C` the old file had `MINSTOP=90, MINTEMP=25, MAXTEMP=65`, and Tdie idled
at 52.4 °C:

```
(52.4 - 25) / (65 - 25) = 0.685  →  90 + 0.685 × (255 - 90) = 203
```

Measured `pwm1` was **202**. The rule that follows: **MINTEMP must sit above
the CPU's idle temperature**, or the fans never reach their floor.

## Measured hardware profiles

| Profile | Board / CPU | Controller | Mechanism | Example config |
|---------|-------------|-----------|-----------|----------------|
| `Profile A` | Dell OptiPlex 7010, i7-3770S | `dell_smm` | `forge-fanctl` | `dell-optiplex-7010.conf` |
| `Profile B` | MSI P67A-GD55, i7-2600K | `f71889a` | `forge-fanctl` ×2 (case + GPU) | `msi-p67-case.conf`, `msi-p67-gpu.conf` |
| `Profile C` | MSI X470 Gaming Pro Carbon, Ryzen 2700X | `nct6795` | stock `fancontrol` | `msi-x470-fancontrol.conf` |
| `Profile D` | MSI B450M Mortar Max, Ryzen 1700X | `nct6797` | stock `fancontrol` | `msi-b450m-fancontrol.conf` |

`fancontrol` cannot be used on `Profile A` or `Profile B`:

- **`Profile A`** — `dell_smm` exposes **write-only** pwm (reads return `-ENODATA`).
  fancontrol must read pwm back, so it refuses the device. Writes do work.
  Requires `dell-smm-hwmon` loaded with `force=1` (the OptiPlex 7010 is not in
  the driver's supported list); see `/etc/modprobe.d/dell-smm-hwmon.conf`.
- **`Profile B`** — the `f71882fg` driver is old-style and publishes its attributes on
  the *platform device* (`/sys/devices/platform/f71882fg.656/`) rather than under
  `hwmon/hwmonN/`. fancontrol only understands `hwmonN/pwmM` addressing, which is
  why `pwmconfig` skipped the real fans and latched onto the GPU instead.

## Measured PWM → RPM

Stall points are the operative numbers; floors are set at or above them.

**`Profile C` nct6795** — fan1 stalls below 85; fan2/fan5 never stall.

| PWM | 255 | 170 | 120 | 85 | 70 | 45 | 25 |
|-----|-----|-----|-----|----|----|----|----|
| fan1 | 2331 | 1841 | 1412 | 1062 | **0** | 0 | 0 |
| fan2 | 2947 | 2083 | 1580 | 1208 | 1048 | 799 | 601 |
| fan5 | 2890 | 2070 | 1584 | 1216 | 1057 | 797 | 605 |

**`Profile D` nct6797** — fan2 never stalls; fan3/fan4 stall below 45; fan5 below 70.

| PWM | 255 | 170 | 120 | 85 | 70 | 55 | 45 | 35 |
|-----|-----|-----|-----|----|----|----|----|----|
| fan2 | 2824 | 2142 | 1628 | 1294 | 1152 | 1006 | 902 | 804 |
| fan3 | 1424 | 1167 | 924 | 704 | 602 | 494 | 410 | **0** |
| fan4 | 1318 | 1060 | 849 | 667 | 576 | 486 | 414 | **0** |
| fan5 | 2947 | 2509 | 1872 | 1331 | 1108 | stall | **0** | 0 |

**`Profile B` f71889a** — fan1 has a hardware floor near 585 RPM and cannot stall;
fan2 stalls below 55.

| PWM | 255 | 170 | 120 | 85 | 70 | 55 | 35 |
|-----|-----|-----|-----|----|----|----|----|
| fan1 | 1718 | 1429 | 995 | 608 | 587 | 587 | 588 |
| fan2 | 1061 | 951 | 690 | 503 | 404 | **0** | 0 |

**`Profile A` dell_smm** — quantised into discrete steps, not a smooth ramp. Fans
**never stop**, even at pwm 0 (Dell enforces a minimum).

| PWM written | ≤55 | 70–120 | 140 | 170 | 200+ |
|-------------|-----|--------|-----|-----|------|
| Processor Fan | ~1088 | ~1797 | 1916 | 2591 | ~3064 |
| Motherboard Fan | ~1123 | ~1505 | 2088 | 3059 | ~3898 |

## Results at idle

| Host | Before | After |
|------|--------|-------|
| `Profile A` | 2312 / 1990 | **1088 / 1126** |
| `Profile B` | 1718 / 882, GPU 1890 | **581 / 434, GPU 1560** |
| `Profile C` | 1898 / 1875 / 1872 | **1138 / 757 / 758** |
| `Profile D` | 823, fans 3/4/5 stopped | **713, fans 3/4/5 stopped** |

## Watch the idle spike range, not just the idle average

Setting `MINTEMP` just above the *average* idle temperature is not enough on a
part that boost-spikes. `Profile C` was first tuned to `MINTEMP=55` against a ~52 °C
idle. Sampling every 10 s for 3 minutes showed the fans at their floor in only
14 of 18 samples; the other 4 had surged to ~1800 RPM. Tdie on a 2700X spikes
briefly past 55 °C at idle, fancontrol catches the spike, ramps, and the
temperature has already fallen back by the next read — so the fans hunt up and
down, which is *more* audible than steady noise.

Moving the band to 65–80 fixed it: 18 of 18 samples at the floor, fans steady at
1138 / 757 / 758. Full-load peak was 74 °C against a 95 °C limit, so the higher
`MINTEMP` costs no real headroom.

The same check on `Profile B` found no hunting (16/16 at floor, fan1 580-586 RPM) even
with only ~3 °C of margin, because the i7-2600K does not boost-spike like Ryzen.
Verify per-part rather than assuming.

## Safety properties

- **Load-tested.** All four ramp correctly. Peaks under a synthetic all-core
  load: `Profile B` 63 °C, `Profile C` 74 °C, `Profile D` 52 °C — all far inside spec.
- **`Profile D`'s stopped fans do restart.** Verified under load: at Tdie 38 °C fans
  3/4/5 read 0 RPM; 30 s into a full load Tdie crossed `MINTEMP=50` and all
  three started unaided (612 / 580 / 1072 RPM). `MINPWM=0` with a `MINSTART`
  above the measured stall point is therefore safe here, and is what keeps the
  host silent at idle.
- **`Profile A` is thermally limited in hardware.** It reaches 95–96 °C under a full
  synthetic load *with fans already maxed at 4477/4205 RPM*, against a 93 °C
  high / 103 °C critical threshold. No fan curve can fix this; the fans are
  already at 100%. Its real workload is a single VM at load ~0.12 where it sits
  at 60–64 °C. **This host wants dust removal and fresh thermal paste.**
- **`Profile A` cannot fail safe by stopping.** A pwm written through Dell SMM
  persists across module unload — the BIOS does *not* resume automatic control.
  `forge-fanctl` therefore drives fans to `SAFE_PWM` on exit and systemd sets
  `Restart=always`.
- **Unreadable sensor means "assume hot".** `forge-fanctl` substitutes 95 °C if
  the temperature source cannot be read, so a broken path spins fans up rather
  than down.
- **`MINSTOP >= MINPWM`** is a fancontrol requirement. `MINPWM` is the floor used
  below `MINTEMP`; `MINSTOP` is where the active ramp begins.

## Known limits

- **Unused GPUs dominate what noise remains.** Neither GPU is passed through to
  any guest. `Profile B`'s GTX 560 Ti has a VBIOS floor of ~1590 RPM. `Profile D`'s GTX 1060
  reports `pwm1_enable=-1` — nouveau **cannot** control it at all, and it sits at
  ~1490–1767 RPM. Replacing both with passive cards is the largest remaining
  win, but neither board can boot headless for BIOS access (P67 has no iGPU
  output; the 1700X has no iGPU).
- `Profile D`'s `pwm1` is deliberately unmanaged: `fan1` reports no tacho yet the CPU
  stays cool, so that header is not safely assumed empty.

## Deploying

```bash
install -m755 forge-fanctl /usr/local/sbin/forge-fanctl
install -m644 forge-fanctl.service /etc/systemd/system/
install -m644 configs/<matching-forge-fanctl-config>.conf /etc/forge-fanctl.conf
systemctl daemon-reload && systemctl enable --now forge-fanctl
```

For `Profile C`/`Profile D`, install the matching `*-fancontrol.conf` file to
`/etc/fancontrol` and restart `fancontrol`. Back up the existing configuration
yourself before replacing it.
