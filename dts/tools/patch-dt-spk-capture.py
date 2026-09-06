#!/usr/bin/env python3
"""Add the amplifiers' I/V sense capture link (SECONDARY_MI2S_TX).

Diagnostic: the sense stream is the only on-device way to see whether the parts
are actually driving the speakers, and it exercises the same link in the other
direction. Playback stays on data1 (gpio124); the sense arrives on data0
(gpio122), which is already in the sec-mi2s pinctrl.

    ./patch-dt-spk-capture.py     # zorn-audio-spksw.dtb -> zorn-audio-sense.dtb
"""
import argparse, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PH_BEDAI, PH_APM = 0x13d, 0x141
PH_SPK_L, PH_SPK_R = 0x158, 0x159
SECONDARY_MI2S_TX = 19
SOUND_NODE = '\tsound {'

LINK = f"""
		spk-capture-dai-link {{
			link-name = "SIA9187 IV Sense";

			cpu {{
				sound-dai = <{PH_BEDAI:#x} {SECONDARY_MI2S_TX:#x}>;
			}};

			codec {{
				sound-dai = <{PH_SPK_L:#x} {PH_SPK_R:#x}>;
			}};

			platform {{
				sound-dai = <{PH_APM:#x}>;
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
    ap.add_argument('--dtb', default=HERE / 'zorn-audio-spksw.dtb')
    ap.add_argument('--out', default=HERE / 'zorn-audio-sense.dtb')
    args = ap.parse_args()
    src = Path(args.dtb)
    dts = sh('dtc', '-I', 'dtb', '-O', 'dts', str(src)).stdout.decode()
    print(f"=== {src.name}: {len(dts.splitlines())} lines ===")
    if 'spk-capture-dai-link' in dts:
        sys.exit("already patched")
    dts = add_child(dts, SOUND_NODE, LINK)
    print(f"  sound: spk-capture-dai-link, cpu <&q6apmbedai {SECONDARY_MI2S_TX}>")
    out = Path(args.out)
    tmp = out.with_suffix('.dts')
    tmp.write_text(dts)
    sh('dtc', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(tmp))
    print(f"\nwrote {out}  ({out.stat().st_size} bytes)")


if __name__ == '__main__':
    main()
