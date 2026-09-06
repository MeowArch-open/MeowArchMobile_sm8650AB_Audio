#!/usr/bin/env python3
"""Wire zorn's two SIA9187 amps to the ADSP: secondary MI2S playback link.

The data plane. `patch-dt-sia9187.py` only opened the I2C control bus; the
amplifiers still had no way to receive samples. On Android the amps hang off
LPAIF secondary -- that is the one MI2S/TDM pinctrl the vendor DT leaves
`status = "ok"` (`sec_tdm_pinctrl`), and the one MI2S/TDM front end in
Android's /proc/asound/pcm that has a real codec rather than `msm-stub`:

    00-36: TDM-LPAIF-RX-SECONDARY multicodec-36 : : playback 1
    00-22: MI2S-LPAIF-RX-SECONDARY msm-stub-rx-22 : : playback 1

Secondary TDM and secondary MI2S are the same block on the same four pins, and
2-slot TDM is I2S, so this uses upstream's SECONDARY_MI2S_RX (18) -- the
AudioReach topology has an i2s-playback subgraph but no TDM module at all.

The pins, from the vendor's sec_tdm_pinctrl (all four inside tlmm's
97..125 reservation, so all four have to be freed):

    gpio121  i2s1_sck    bit clock, SoC-driven
    gpio123  i2s1_ws     frame clock, SoC-driven
    gpio124  i2s1_data1  SoC data out -> amp DIN   (vendor `tdm1_dout`)
    gpio122  i2s1_data0  amp I/V sense -> SoC      (vendor `tdm1_din`)

Since data1 is the outbound line, the topology's I2S sink is built with
SD_LINE_IDX_I2S_SD1, not SD0 -- see the SECONDARY_MI2S_RX block added to
SM8550-HDK.m4. If there is clocking but silence, SD0 is the thing to try next.

sc8280xp.c already handles the link: cpu_dai->id 18 falls in its
PRIMARY_MI2S_RX...QUATERNARY_MI2S_TX case and gets SND_SOC_DAIFMT_BP_FP, so
the SoC is clock master, and qcom_snd_is_sdw_dai(18) is false so the SoundWire
startup/prepare helpers pass straight through.

    ./patch-dt-sec-mi2s.py           # zorn-audio-sia.dtb -> zorn-audio-mi2s.dtb
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

MI2S_GPIOS = (121, 122, 123, 124)

TLMM_NODE = '\t\tpinctrl@f100000 {'
SOUND_NODE = '\tsound {'

PH_BEDAI = 0x13d          # q6apmbedai, #sound-dai-cells = <1>
PH_APM = 0x141            # q6apm platform
PH_SPK_L = 0x158          # new: speaker@6c
PH_SPK_R = 0x159          # new: speaker@6d
PH_PINCTRL = 0x15a        # new: sec-mi2s-active-state

SECONDARY_MI2S_RX = 18

PINCTRL_STATE = f"""
			sec-mi2s-active-state {{
				phandle = <{PH_PINCTRL:#x}>;

				sck-pins {{
					pins = "gpio121";
					function = "i2s1_sck";
					drive-strength = <0x08>;
					bias-disable;
					output-high;
				}};

				ws-pins {{
					pins = "gpio123";
					function = "i2s1_ws";
					drive-strength = <0x08>;
					bias-disable;
					output-high;
				}};

				dout-pins {{
					pins = "gpio124";
					function = "i2s1_data1";
					drive-strength = <0x08>;
					bias-pull-down;
				}};

				din-pins {{
					pins = "gpio122";
					function = "i2s1_data0";
					drive-strength = <0x08>;
					bias-disable;
				}};
			}};
"""

SPK_LINK = f"""
		spk-dai-link {{
			link-name = "SIA9187 Speakers";

			cpu {{
				sound-dai = <{PH_BEDAI:#x} {SECONDARY_MI2S_RX:#x}>;
			}};

			codec {{
				sound-dai = <{PH_SPK_L:#x} {PH_SPK_R:#x}>;
			}};

			platform {{
				sound-dai = <{PH_APM:#x}>;
			}};
		}};
"""

SOUND_PINCTRL = f"""\t\tpinctrl-names = "default";
\t\tpinctrl-0 = <{PH_PINCTRL:#x}>;"""


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


def add_child(s: str, header: str, child: str) -> str:
    """Insert `child` as the last child of the node `header`."""
    i, j = node_span(s, header)
    body = s[i:j]
    k = body.rindex('}')
    return s[:i] + body[:k] + child + body[k:] + s[j:]


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


def add_phandle(s: str, header: str, phandle: int) -> str:
    """dtc drops phandles from nodes nothing points at, so the two amplifier
    nodes have none until the dai-link below references them."""
    i, j = node_span(s, header)
    if 'phandle = <' in s[i:j]:
        sys.exit(f"{header!r} already has a phandle -- already patched?")
    indent = re.search(r'\n(\t+)[\w#]', s[i:j]).group(1)
    return add_props(s, header, f'{indent}phandle = <{phandle:#x}>;')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dtb', default=HERE / 'zorn-audio-sia.dtb')
    ap.add_argument('--out', default=HERE / 'zorn-audio-mi2s.dtb')
    args = ap.parse_args()

    src = Path(args.dtb)
    dts = sh('dtc', '-I', 'dtb', '-O', 'dts', str(src)).stdout.decode()
    print(f"=== {src.name}: {len(dts.splitlines())} lines ===")

    if 'sec-mi2s-active-state' in dts:
        sys.exit("already patched")

    print("1. tlmm gpio-reserved-ranges (i2s1 sck/ws/data0/data1)")
    for g in MI2S_GPIOS:
        dts = free_gpio(dts, g)

    print("2. tlmm sec-mi2s-active-state")
    dts = add_child(dts, TLMM_NODE, PINCTRL_STATE)

    print("3. phandles on the two amplifiers")
    for header, ph in (('\t\t\t\tspeaker@6c {', PH_SPK_L),
                       ('\t\t\t\tspeaker@6d {', PH_SPK_R)):
        dts = add_phandle(dts, header, ph)
        print(f"  {header.strip()} -> {ph:#x}")

    print("4. sound: pinctrl + spk-dai-link (SECONDARY_MI2S_RX)")
    dts = add_props(dts, SOUND_NODE, SOUND_PINCTRL)
    dts = add_child(dts, SOUND_NODE, SPK_LINK)

    out = Path(args.out)
    tmp = out.with_suffix('.dts')
    tmp.write_text(dts)
    sh('dtc', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(tmp))
    print(f"\nwrote {out}  ({out.stat().st_size} bytes)")


if __name__ == '__main__':
    main()
