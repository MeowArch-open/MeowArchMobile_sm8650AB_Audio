#!/usr/bin/env python3
"""Turn on zorn's audio card: the WCD9395 codec on SoundWire, and a sound node
that actually has links to it.

The booted DT comes from upstream sm8650-mtp.dts, so its `sound` node exists but
is status = "disabled" and has exactly one dai-link -- WSA Playback, pointing at
two wsa884x SoundWire speaker amps that zorn does not have. zorn's own vendor DT
has all four wsa884x nodes status = "disabled" and drives the speakers from two
Awinic aw882xx smart PAs on qupv3_se7_i2c instead, so that link can never work
here and is replaced rather than kept.

What zorn does have, and what upstream already supports, is the WCD9395: the
vendor tree carries a wcd939x-codec node with rx/tx SoundWire slaves and
qcom,wcd-rst-gpio-node pointing at gpio107 -- the same pin sm8650-qrd.dts uses.
So the QRD's audio wiring transfers almost verbatim:

  1. soundwire@6ad0000 (swr1, RX)  disabled -> okay, plus a wcd_rx slave at 0,4
  2. soundwire@6d30000 (swr2, TX)  disabled -> okay, plus a wcd_tx slave at 0,3
  3. a new top-level audio-codec node: qcom,wcd9395-codec, reset on tlmm 107,
     supplies from vreg_l15b_1p8 and vreg_bob1, micbias at the vendor's 2.75 V
     rather than the QRD's 1.8 V
  4. sound: disabled -> okay, WSA Playback replaced by WCD Playback and
     WCD Capture, audio-routing rewritten for HPH and AMIC1-5
  5. tlmm gpio-reserved-ranges narrowed so gpio107 becomes usable -- 97..125 is
     reserved wholesale in this DT and reset-gpios would get -EINVAL

The speakers are deliberately out of scope here: they need an aw88xx codec driver
plus an MI2S/TDM dai-link, which is a separate piece of work.

    ./patch-dt-audio.py                    # booted-fdt-20260905.dtb -> zorn-audio.dtb
    ./patch-dt-audio.py --dtb other.dtb --out other-audio.dtb
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

WCD_RESET_GPIO = 107     # qcom,wcd939x_reset_active: pins = "gpio107"
MICBIAS_UV = 2750000     # qcom,cdc-micbias{1..4}-mv = <0xabe> in the vendor tree

# Phandles already in the tree, read out of it rather than guessed.
PH_TLMM = 0x92
PH_L15B = 0xc1           # vreg_l15b_1p8, also the speakers' vdd-1p8-supply
PH_BOB1 = 0x116          # vreg_bob1
PH_RXMACRO = 0xbb        # codec@6ac0000
PH_TXMACRO = 0xc4        # codec@6ae0000
PH_BEDAI = 0x13d         # q6apmbedai, as used by the existing wsa-dai-link
PH_APM = 0x141           # q6apm

# Free phandles: the tree tops out at 0x150.
PH_WCD = 0x151
PH_WCD_RX = 0x152
PH_SWR1 = 0x153
PH_WCD_TX = 0x154
PH_SWR2 = 0x155

RX_CODEC_DMA_RX_0 = 113  # include/dt-bindings/sound/qcom,q6dsp-lpass-ports.h
TX_CODEC_DMA_TX_3 = 120


def sh(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True)


def node_span(s: str, header: str, start: int = 0) -> tuple[int, int]:
    """Byte range of the node whose header is `header`, braces balanced."""
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


def enable(s: str, header: str, phandle: int | None = None) -> str:
    """status = "disabled" -> "okay" inside one node, optionally adding a phandle."""
    i, j = node_span(s, header)
    body = s[i:j]
    if 'status = "disabled";' not in body:
        sys.exit(f"{header!r} is not disabled -- already patched?")
    new = body.replace('status = "disabled";', 'status = "okay";', 1)
    if phandle is not None and 'phandle = <' not in new:
        # dtc puts phandle last in a node it generated; match that.
        k = new.rindex('}')
        indent = re.search(r'\n(\t+)\w', new).group(1)
        new = new[:k] + f'{indent}phandle = <{phandle:#x}>;\n' + new[k:]
    return s[:i] + new + s[j:]


def add_child(s: str, header: str, child: str) -> str:
    """Insert `child` as the last child of the node `header`."""
    i, j = node_span(s, header)
    body = s[i:j]
    k = body.rindex('}')           # the node's own closing brace
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


WCD_RX_SLAVE = f"""
			codec@0,4 {{
				compatible = "sdw20217010e00";
				reg = <0x00 0x04>;
				qcom,rx-port-mapping = <0x01 0x02 0x03 0x04 0x05 0x09>;
				phandle = <{PH_WCD_RX:#x}>;
			}};
"""

WCD_TX_SLAVE = f"""
			codec@0,3 {{
				compatible = "sdw20217010e00";
				reg = <0x00 0x03>;
				qcom,tx-port-mapping = <0x02 0x02 0x03 0x04>;
				phandle = <{PH_WCD_TX:#x}>;
			}};
"""


WCD_CODEC = f"""
	audio-codec {{
		compatible = "qcom,wcd9395-codec", "qcom,wcd9390-codec";
		qcom,micbias1-microvolt = <{MICBIAS_UV:#x}>;
		qcom,micbias2-microvolt = <{MICBIAS_UV:#x}>;
		qcom,micbias3-microvolt = <{MICBIAS_UV:#x}>;
		qcom,micbias4-microvolt = <{MICBIAS_UV:#x}>;
		qcom,mbhc-buttons-vthreshold-microvolt = <0x124f8 0x24990 0x39d68 0x7a120 0x7a120 0x7a120 0x7a120 0x7a120>;
		qcom,mbhc-headset-vthreshold-microvolt = <0x19f0a0>;
		qcom,mbhc-headphone-vthreshold-microvolt = <0xc350>;
		qcom,rx-device = <{PH_WCD_RX:#x}>;
		qcom,tx-device = <{PH_WCD_TX:#x}>;
		reset-gpios = <{PH_TLMM:#x} {WCD_RESET_GPIO:#x} 0x01>;
		vdd-buck-supply = <{PH_L15B:#x}>;
		vdd-rxtx-supply = <{PH_L15B:#x}>;
		vdd-io-supply = <{PH_L15B:#x}>;
		vdd-mic-bias-supply = <{PH_BOB1:#x}>;
		#sound-dai-cells = <0x01>;
		phandle = <{PH_WCD:#x}>;
	}};
"""

# Replaces the MTP's WSA link wholesale: zorn has no wsa884x, and a dai-link whose
# codec never attaches is a good way to lose the whole card.
WCD_DAI_LINKS = f"""
		wcd-playback-dai-link {{
			link-name = "WCD Playback";

			cpu {{
				sound-dai = <{PH_BEDAI:#x} {RX_CODEC_DMA_RX_0:#x}>;
			}};

			codec {{
				sound-dai = <{PH_WCD:#x} 0x00 {PH_SWR1:#x} 0x00 {PH_RXMACRO:#x} 0x00>;
			}};

			platform {{
				sound-dai = <{PH_APM:#x}>;
			}};
		}};

		wcd-capture-dai-link {{
			link-name = "WCD Capture";

			cpu {{
				sound-dai = <{PH_BEDAI:#x} {TX_CODEC_DMA_TX_3:#x}>;
			}};

			codec {{
				sound-dai = <{PH_WCD:#x} 0x01 {PH_SWR2:#x} 0x00 {PH_TXMACRO:#x} 0x00>;
			}};

			platform {{
				sound-dai = <{PH_APM:#x}>;
			}};
		}};
"""

AUDIO_ROUTING = ('audio-routing = "IN1_HPHL", "HPHL_OUT", "IN2_HPHR", "HPHR_OUT", '
                 '"AMIC1", "MIC BIAS1", "AMIC2", "MIC BIAS2", "AMIC3", "MIC BIAS3", '
                 '"AMIC4", "MIC BIAS3", "AMIC5", "MIC BIAS4", '
                 '"TX SWR_INPUT0", "ADC1_OUTPUT", "TX SWR_INPUT1", "ADC2_OUTPUT", '
                 '"TX SWR_INPUT2", "ADC3_OUTPUT", "TX SWR_INPUT3", "ADC4_OUTPUT";')


def patch_sound(s: str) -> str:
    """Enable the sound node, swap its WSA link for the two WCD links."""
    i, j = node_span(s, '\tsound {')
    body = s[i:j]

    if 'wcd-playback-dai-link' in body:
        sys.exit("sound node already has the WCD links -- already patched?")

    body = body.replace('status = "disabled";\n', '', 1)
    body = re.sub(r'audio-routing = [^;]*;', AUDIO_ROUTING, body, count=1)

    k, l = node_span(body, '\t\twsa-dai-link {')
    body = body[:k] + WCD_DAI_LINKS.lstrip('\n') + body[l + 1:]
    return s[:i] + body + s[j:]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dtb', default=HERE / 'booted-fdt-20260905.dtb')
    ap.add_argument('--out', default=HERE / 'zorn-audio.dtb')
    args = ap.parse_args()

    src = Path(args.dtb)
    dts = sh('dtc', '-I', 'dtb', '-O', 'dts', str(src)).stdout.decode()
    print(f"=== {src.name}: {len(dts.splitlines())} lines ===")

    print("1. soundwire@6ad0000 (swr1, RX)")
    dts = enable(dts, '\t\tsoundwire@6ad0000 {', PH_SWR1)
    dts = add_child(dts, '\t\tsoundwire@6ad0000 {', WCD_RX_SLAVE)

    print("2. soundwire@6d30000 (swr2, TX)")
    dts = enable(dts, '\t\tsoundwire@6d30000 {', PH_SWR2)
    dts = add_child(dts, '\t\tsoundwire@6d30000 {', WCD_TX_SLAVE)

    print("3. audio-codec (WCD9395)")
    i, j = node_span(dts, '\tsound {')
    dts = dts[:i] + WCD_CODEC.lstrip('\n') + '\n' + dts[i:]

    print("4. sound")
    dts = patch_sound(dts)

    print(f"5. tlmm gpio-reserved-ranges")
    dts = free_gpio(dts, WCD_RESET_GPIO)

    out = Path(args.out)
    tmp = out.with_suffix('.dts')
    tmp.write_text(dts)
    sh('dtc', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(tmp))
    print(f"\nwrote {out}  ({out.stat().st_size} bytes), source kept as {tmp.name}")


if __name__ == '__main__':
    main()
