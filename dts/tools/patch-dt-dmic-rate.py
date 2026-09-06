#!/usr/bin/env python3
"""Raise the VA macro's DMIC clock from 600 kHz to 2.4 MHz.

600 kHz is what the vendor puts on the VA macro (qcom,va-dmic-sample-rate =
600000), but that is their island / low-power voice-trigger path. Their actual
recording path is the TX macro at qcom,tx-dmic-sample-rate = 2400000, and a PDM
microphone that is only clocked at 600 kHz may never leave standby -- which looks
exactly like what we get: the whole DAPM path powers up, MIC BIAS3 is on, the LPI
pins are muxed to dmic1_clk/dmic1_data, and every sample is zero.

9.6 MHz / 2.4 MHz = 4, which is one of the divisors lpass-va-macro accepts
(2, 3, 4, 6, 8, 16), so this is a legal rate for the same code path.

    ./patch-dt-dmic-rate.py --rate 2400000
"""
import argparse, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sh(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dtb', default=HERE / 'zorn-audio-sense.dtb')
    ap.add_argument('--out', default=HERE / 'zorn-audio-dmicrate.dtb')
    ap.add_argument('--rate', type=int, default=2400000)
    args = ap.parse_args()

    src = Path(args.dtb)
    dts = sh('dtc', '-I', 'dtb', '-O', 'dts', str(src)).stdout.decode()
    print(f"=== {src.name}: {len(dts.splitlines())} lines ===")

    m = re.search(r'qcom,dmic-sample-rate = <(0x[0-9a-f]+)>;', dts)
    if not m:
        sys.exit("no qcom,dmic-sample-rate in this tree")
    old = int(m.group(1), 16)
    print(f"  qcom,dmic-sample-rate {old} -> {args.rate}  (div {9600000 // args.rate})")
    dts = dts[:m.start(1)] + f'{args.rate:#x}' + dts[m.end(1):]

    out = Path(args.out)
    tmp = out.with_suffix('.dts')
    tmp.write_text(dts)
    sh('dtc', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(tmp))
    print(f"\nwrote {out}  ({out.stat().st_size} bytes)")


if __name__ == '__main__':
    main()
