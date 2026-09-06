#!/usr/bin/env python3
"""Give the VA macro its own DMIC rail and route the DMICs to it.

lpass-va-macro declares SND_SOC_DAPM_REGULATOR_SUPPLY("vdd-micb", ...) but never
routes it internally, so it only ever powers up if the machine's audio-routing
names it -- which is what qcs6490-rb3gen2 and qrb5165-rb5 do:

    "VA DMIC0", "vdd-micb", ...

Ours had neither the supply nor the route, and the regulator summary showed it
resolved to a dummy: `6d44000.codec-vdd-micb  0  0mA  0mV`. The DMICs power up
the whole path, the LPI pins are muxed and the decimator produces its HPF
transient, then every sample is zero -- which is what an unpowered PDM microphone
looks like.

    ./patch-dt-vdd-micb.py    # zorn-audio-dmic45.dtb -> zorn-audio-micb.dtb
"""
import argparse, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PH_L15B = 0xc1                # vreg_l15b_1p8, the same 1.8 V the WCD runs on
VA_NODE = '\t\tcodec@6d44000 {'
EXTRA = ['"VA DMIC%d", "vdd-micb"' % n for n in range(4)]


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
    ap.add_argument('--dtb', default=HERE / 'zorn-audio-dmic45.dtb')
    ap.add_argument('--out', default=HERE / 'zorn-audio-micb.dtb')
    args = ap.parse_args()

    src = Path(args.dtb)
    dts = sh('dtc', '-I', 'dtb', '-O', 'dts', str(src)).stdout.decode()
    print(f"=== {src.name}: {len(dts.splitlines())} lines ===")
    if 'vdd-micb-supply' in dts:
        sys.exit("already patched")

    dts = add_props(dts, VA_NODE, f'\t\t\tvdd-micb-supply = <{PH_L15B:#x}>;')
    print(f"  va macro: vdd-micb-supply = <&vreg_l15b_1p8>  ({PH_L15B:#x})")

    m = re.search(r'audio-routing = (.*?);\n', dts, re.S)
    if not m:
        sys.exit("no audio-routing")
    dts = dts[:m.end(1)] + ', ' + ', '.join(EXTRA) + dts[m.end(1):]
    print("  sound: audio-routing += " + ', '.join(EXTRA))

    out = Path(args.out)
    tmp = out.with_suffix('.dts')
    tmp.write_text(dts)
    sh('dtc', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(tmp))
    print(f"\nwrote {out}  ({out.stat().st_size} bytes)")


if __name__ == '__main__':
    main()
