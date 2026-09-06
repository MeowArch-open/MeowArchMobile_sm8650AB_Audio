#!/usr/bin/env python3
"""Open the road to zorn's speaker amplifiers: the QUP the two SIA9187s sit on.

zorn's speakers are two Silicon Integrated SIA9187 digital smart PAs on I2C
0x6c/0x6d -- not the Awinic parts the vendor DT also declares, which never bind
(checked on a running Android: 9-006c/9-006d have driver `sipa`, 9-0034/9-0035
have none). The bus is qupv3_se7 = i2c@a9c000, and in this tree it is
status = "disabled", so Linux has no i2c adapter for it at all.

Three GPIOs also have to come out of tlmm's gpio-reserved-ranges, the same wide
reservation that hid the display pins and the WCD reset:

    111  si,si_pa_reset for si_pa_L        (vendor: <&tlmm 111>)
     85  si,si_pa_reset for si_pa_R
     70  spksw-gpio, only si_pa_L has one

This patch stops at the bus and the pins on purpose: with the adapter present,
the chip ID can be read from userspace and checked against what the vendor
driver expects before a single line of codec driver is written. Per
reg_map_info_table in sia91xx_dlkm.ko, chip type 0x13 ("sia9187") is 8-bit
register addresses, 16-bit values, ID register 0x06, valid IDs 0x5d80..0x5d90.

    ./patch-dt-sia9187.py            # zorn-audio-dmic.dtb -> zorn-audio-sia.dtb
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The two I2C pins have to come out of the reservation as well, or geni_i2c's
# probe dies in pinctrl before it ever creates an adapter:
#   sm8650-tlmm: error -EINVAL: could not request pin 60 (GPIO_60)
#   geni_i2c a9c000.i2c: Error applying setting, reverse things back
# qup-i2c7-data-clk-state is gpio60 (SDA) + gpio61 (SCL), function qup1_se7.
SIPA_GPIOS = (60, 61, 70, 85, 111)   # i2c7 data/clk, spksw, si_pa_R/L reset
I2C_NODE = '\t\t\ti2c@a9c000 {'


def sh(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True)


def node_span(s: str, header: str, start: int = 0) -> tuple[int, int]:
    i = s.index(header, start)
    j = i + len(header)
    depth = 1
    while depth and j < len(s):
        if s[j] == '{':
            depth += 1
        elif s[j] == '}':
            depth -= 1
        j += 1
    if depth:
        sys.exit(f"unbalanced braces looking for {header!r}")
    return i, j


def add_props(s: str, header: str, props: str) -> str:
    """Insert properties into a node, before its first child -- dtc rejects a
    property that follows a subnode."""
    i, j = node_span(s, header)
    body = s[i:j]
    cut = re.search(r'\n\t+[\w@,.+-]+ \{', body)
    at = cut.start() if cut else body.rindex('\n\t')
    return s[:i] + body[:at] + '\n' + props.rstrip('\n') + body[at:] + s[j:]


def add_phandle(s: str, header: str, phandle: int) -> str:
    """Give a node a phandle so it can be referenced. dtc drops phandles from
    nodes nothing points at, which is why the dmic pin states have none."""
    i, j = node_span(s, header)
    if 'phandle = <' in s[i:j]:
        sys.exit(f"{header!r} already has a phandle -- already patched?")
    indent = re.search(r'\n(\t+)\w', s[i:j]).group(1)
    return add_props(s, header, f'{indent}phandle = <{phandle:#x}>;')




def add_child(s: str, header: str, child: str) -> str:
    """Insert `child` as the last child of the node `header`."""
    i, j = node_span(s, header)
    body = s[i:j]
    k = body.rindex('}')
    return s[:i] + body[:k] + child + body[k:] + s[j:]


PH_TLMM = 0x92

# Vendor: si_pa_L reset = <&tlmm 111 0>, si_pa_R reset = <&tlmm 85 0>, both
# active high; channel_num 0 and 1; sound-name-prefix from the sipa_i2c_L/R
# nodes. spksw-gpio (tlmm 70) belongs to the left one only and is not modelled
# yet -- nothing is known about what it switches.
AMPS = f"""
				speaker@6c {{
					compatible = "si,sia9187";
					reg = <0x6c>;
					reset-gpios = <{PH_TLMM:#x} 0x6f 0x00>;
					sound-name-prefix = "SpkrLeft";
					#sound-dai-cells = <0x00>;
				}};

				speaker@6d {{
					compatible = "si,sia9187";
					reg = <0x6d>;
					reset-gpios = <{PH_TLMM:#x} 0x55 0x00>;
					sound-name-prefix = "SpkrRight";
					#sound-dai-cells = <0x00>;
				}};
"""


def free_gpio(s: str, gpio: int) -> str:
    """Punch `gpio` out of tlmm's gpio-reserved-ranges, leaving the rest alone."""
    m = re.search(r'gpio-reserved-ranges = <([^>]*)>;', s)
    if not m:
        sys.exit("no gpio-reserved-ranges in this tree")
    vals = [int(x, 16) for x in m.group(1).split()]
    pairs = list(zip(vals[0::2], vals[1::2]))

    out = []
    hit = False
    for base, count in pairs:
        if base <= gpio < base + count:
            hit = True
            if gpio > base:
                out.append((base, gpio - base))
            if gpio + 1 < base + count:
                out.append((gpio + 1, base + count - gpio - 1))
        else:
            out.append((base, count))
    if not hit:
        print(f"  gpio{gpio} was already usable")
        return s

    flat = ' '.join(f'{v:#x}' for pair in out for v in pair)
    print(f"  freed gpio{gpio}: {len(pairs)} ranges -> {len(out)}")
    return s[:m.start(1)] + flat + s[m.end(1):]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dtb', default=HERE / 'zorn-audio-dmic.dtb')
    ap.add_argument('--out', default=HERE / 'zorn-audio-sia.dtb')
    args = ap.parse_args()

    src = Path(args.dtb)
    dts = sh('dtc', '-I', 'dtb', '-O', 'dts', str(src)).stdout.decode()
    print(f"=== {src.name}: {len(dts.splitlines())} lines ===")

    print("1. i2c@a9c000 (qupv3_se7, the SIA9187 bus)")
    i, j = node_span(dts, I2C_NODE)
    body = dts[i:j]
    if 'status = "disabled";' not in body:
        sys.exit("i2c@a9c000 is not disabled -- already patched?")
    dts = dts[:i] + body.replace('status = "disabled";', 'status = "okay";', 1) + dts[j:]

    print("2. the two SIA9187 amplifiers")
    dts = add_child(dts, I2C_NODE, AMPS)

    print("3. tlmm gpio-reserved-ranges")
    for g in SIPA_GPIOS:
        dts = free_gpio(dts, g)

    out = Path(args.out)
    tmp = out.with_suffix('.dts')
    tmp.write_text(dts)
    sh('dtc', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(tmp))
    print(f"\nwrote {out}  ({out.stat().st_size} bytes)")


if __name__ == '__main__':
    main()
