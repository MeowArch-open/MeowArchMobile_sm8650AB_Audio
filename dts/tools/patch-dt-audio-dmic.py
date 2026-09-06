#!/usr/bin/env python3
"""Add zorn's four digital microphones to the audio device tree.

Android says the built-in mics are DMICs, not the analog AMICs the first version
of this DT assumed. `mixer_paths_pineapple_mtp.xml`:

    handset-mic = dmic2
    dmic1: TX_AIF1_CAP Mixer DEC2=1 ; TX DMIC MUX2=DMIC0
    dmic2: TX_AIF1_CAP Mixer DEC2=1 ; TX DMIC MUX2=DMIC1    <- the main mic
    dmic3/dmic4: DMIC2 / DMIC3

and the pins are LPASS-LPI gpio6..9 (vendor `dmic01/23_{clk,data}_active`,
function func1), which is exactly what sm8650.dtsi already declares as
dmic01_default / dmic23_default -- same pins, same drive strength.

Only the VA macro reads qcom,dmic-sample-rate upstream (lpass-va-macro.c:1560);
it owns the DMIC clock divider that the TX macro's DMIC muxes then sample. So the
DMIC configuration goes on the VA macro even though the capture path runs through
the TX macro's decimators.

Both capture routes are wired up, because which one works is exactly what has not
been measured yet:

  * the vendor's: TX_CODEC_DMA_TX_3 (already in the tree) with
    TX DEC2 MUX=MSM_DMIC + TX DMIC MUX2=DMIC1
  * upstream sm8450-hdk's: a new VA_CODEC_DMA_TX_0 dai-link straight off the
    VA macro

The second is additive -- an unused dai-link costs a PCM device, nothing else.

    ./patch-dt-audio-dmic.py                 # zorn-audio.dtb -> zorn-audio-dmic.dtb
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

DMIC_SAMPLE_RATE = 600000     # vendor: qcom,va-dmic-sample-rate = <0x927c0>
VA_CODEC_DMA_TX_0 = 110       # include/dt-bindings/sound/qcom,q6dsp-lpass-ports.h

PH_VAMACRO = 0xb8
PH_BEDAI = 0x13d
PH_APM = 0x141

# free phandles: the audio tree tops out at 0x155
PH_DMIC01 = 0x156
PH_DMIC23 = 0x157


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


VA_PROPS = f"""			pinctrl-0 = <{PH_DMIC01:#x} {PH_DMIC23:#x}>;
			pinctrl-names = "default";
			qcom,dmic-sample-rate = <{DMIC_SAMPLE_RATE:#x}>;
"""

VA_DAI_LINK = f"""
		va-dai-link {{
			link-name = "VA Capture";

			cpu {{
				sound-dai = <{PH_BEDAI:#x} {VA_CODEC_DMA_TX_0:#x}>;
			}};

			codec {{
				sound-dai = <{PH_VAMACRO:#x} 0x00>;
			}};

			platform {{
				sound-dai = <{PH_APM:#x}>;
			}};
		}};
"""

# The DMIC widgets are sinks fed by the WCD's mic-bias widgets, which is what
# powers the microphones. Upstream has no "Digital Mic<n>" widget -- that name is
# the vendor's intermediate stage, and asking for it makes
# snd_soc_dapm_add_routes() fail, which fails the card. The bias assignment is
# the vendor's own (DMIC0/1 on MIC BIAS3, DMIC2/3 on MIC BIAS1) and happens to be
# exactly what sm8450-hdk.dts uses.
DMIC_ROUTING = (' "TX DMIC0", "MIC BIAS3", "TX DMIC1", "MIC BIAS3", '
                '"TX DMIC2", "MIC BIAS1", "TX DMIC3", "MIC BIAS1", '
                '"VA DMIC0", "MIC BIAS3", "VA DMIC1", "MIC BIAS3", '
                '"VA DMIC2", "MIC BIAS1", "VA DMIC3", "MIC BIAS1"')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dtb', default=HERE / 'zorn-audio.dtb')
    ap.add_argument('--out', default=HERE / 'zorn-audio-dmic.dtb')
    args = ap.parse_args()

    src = Path(args.dtb)
    dts = sh('dtc', '-I', 'dtb', '-O', 'dts', str(src)).stdout.decode()
    print(f"=== {src.name}: {len(dts.splitlines())} lines ===")

    print("1. phandles for the dmic pin states")
    dts = add_phandle(dts, '\t\t\tdmic01-default-state {', PH_DMIC01)
    dts = add_phandle(dts, '\t\t\tdmic23-default-state {', PH_DMIC23)

    print("2. VA macro: dmic pinctrl + sample rate")
    dts = add_props(dts, '\t\tcodec@6d44000 {', VA_PROPS)

    print("3. sound: VA capture dai-link + dmic routing")
    i, j = node_span(dts, '\tsound {')
    body = dts[i:j]
    if 'va-dai-link' in body:
        sys.exit("sound node already has a VA link -- already patched?")
    body = body.replace('"TX SWR_INPUT3", "ADC4_OUTPUT";',
                        '"TX SWR_INPUT3", "ADC4_OUTPUT",' + DMIC_ROUTING + ';', 1)
    k = body.rindex('}')
    body = body[:k] + VA_DAI_LINK + body[k:]
    dts = dts[:i] + body + dts[j:]

    out = Path(args.out)
    tmp = out.with_suffix('.dts')
    tmp.write_text(dts)
    sh('dtc', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(tmp))
    print(f"\nwrote {out}  ({out.stat().st_size} bytes), source kept as {tmp.name}")


if __name__ == '__main__':
    main()
