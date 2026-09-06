#!/usr/bin/env python3
"""Give the left SIA9187 its spksw-gpio (tlmm 70).

The vendor's si_pa_L carries `spksw-gpio = <&tlmm 70 0>` and si_pa_R has none.
Its own driver never drives the pin -- it is the sia91xx_spk_sw_gpio_switch
kcontrol and the HAL owns it -- but on a running Android the left one reads 1,
so the mainline driver asserts it at probe and leaves it there.

    ./patch-dt-spksw.py          # zorn-audio-mi2s.dtb -> zorn-audio-spksw.dtb
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PH_TLMM = 0x92
SPKSW_GPIO = 70


def sh(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True)


def node_span(s, header, start=0):
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


def add_props(s, header, props):
    i, j = node_span(s, header)
    body = s[i:j]
    cut = re.search(r'\n\t+[\w@,.+-]+ \{', body)
    at = cut.start() if cut else body.rindex('\n\t')
    return s[:i] + body[:at] + '\n' + props.rstrip('\n') + body[at:] + s[j:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dtb', default=HERE / 'zorn-audio-mi2s.dtb')
    ap.add_argument('--out', default=HERE / 'zorn-audio-spksw.dtb')
    args = ap.parse_args()

    src = Path(args.dtb)
    dts = sh('dtc', '-I', 'dtb', '-O', 'dts', str(src)).stdout.decode()
    print(f"=== {src.name}: {len(dts.splitlines())} lines ===")

    if 'spksw-gpios' in dts:
        sys.exit("already patched")

    header = '\t\t\t\tspeaker@6c {'
    dts = add_props(dts, header,
                    f'\t\t\t\t\tspksw-gpios = <{PH_TLMM:#x} {SPKSW_GPIO:#x} 0x00>;')
    print(f"  speaker@6c: spksw-gpios = <&tlmm {SPKSW_GPIO} 0>")

    out = Path(args.out)
    tmp = out.with_suffix('.dts')
    tmp.write_text(dts)
    sh('dtc', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(tmp))
    print(f"\nwrote {out}  ({out.stat().st_size} bytes)")


if __name__ == '__main__':
    main()
