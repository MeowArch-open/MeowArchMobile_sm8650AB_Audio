#!/usr/bin/env python3
"""Mux the third DMIC pair, LPI gpio12/13.

The vendor DT declares three DMIC pairs -- cdc_dmic01 (LPI gpio6/7), cdc_dmic23
(gpio8/9) and cdc_dmic45 (gpio12/13) -- and our tree only ever muxed the first
two, so VA DMIC4/DMIC5 could never carry anything no matter what the mux said.
Upstream's LPI pinctrl calls that pair dmic3_clk / dmic3_data.

    ./patch-dt-dmic45.py      # zorn-audio-dmicrate.dtb -> zorn-audio-dmic45.dtb
"""
import argparse, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PH_DMIC45 = 0x15b
LPI_NODE = '\t\tpinctrl@6e80000 {'

STATE = f"""
			dmic45-default-state {{
				phandle = <{PH_DMIC45:#x}>;

				clk-pins {{
					pins = "gpio12";
					function = "dmic3_clk";
					drive-strength = <0x08>;
					output-high;
				}};

				data-pins {{
					pins = "gpio13";
					function = "dmic3_data";
					drive-strength = <0x08>;
					input-enable;
				}};
			}};
"""


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


def add_child(s, header, child):
    i, j = node_span(s, header)
    body = s[i:j]
    k = body.rindex('}')
    return s[:i] + body[:k] + child + body[k:] + s[j:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dtb', default=HERE / 'zorn-audio-dmicrate.dtb')
    ap.add_argument('--out', default=HERE / 'zorn-audio-dmic45.dtb')
    args = ap.parse_args()

    src = Path(args.dtb)
    dts = sh('dtc', '-I', 'dtb', '-O', 'dts', str(src)).stdout.decode()
    print(f"=== {src.name}: {len(dts.splitlines())} lines ===")
    if 'dmic45-default-state' in dts:
        sys.exit("already patched")

    dts = add_child(dts, LPI_NODE, STATE)
    print("  lpi: dmic45-default-state (gpio12 dmic3_clk, gpio13 dmic3_data)")

    old = 'pinctrl-0 = <0x156 0x157>;'
    new = f'pinctrl-0 = <0x156 0x157 {PH_DMIC45:#x}>;'
    if old not in dts:
        sys.exit("va macro pinctrl-0 not in the expected shape")
    dts = dts.replace(old, new, 1)
    print(f"  va macro: pinctrl-0 += {PH_DMIC45:#x}")

    out = Path(args.out)
    tmp = out.with_suffix('.dts')
    tmp.write_text(dts)
    sh('dtc', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(tmp))
    print(f"\nwrote {out}  ({out.stat().st_size} bytes)")


if __name__ == '__main__':
    main()
