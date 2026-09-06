#!/bin/bash
# zorn's built-in mics are DMICs on the TX macro, not the WCD's analog inputs.
# From the vendor HAL (mixer_paths_pineapple_mtp.xml):
#     handset-mic = dmic2 = TX_AIF1_CAP Mixer DEC2 + TX DMIC MUX2=DMIC1
# and TX DEC2 MUX has to be MSM_DMIC rather than SWR_MIC, which is the analog
# route through the WCD over SoundWire.
set -e
C=-c0
set_ctl() { amixer $C -q cset name="$1" "$2"; }

set_ctl 'MultiMedia3 Mixer TX_CODEC_DMA_TX_3' 1,1
set_ctl 'TX_AIF1_CAP Mixer DEC2' 1
set_ctl 'TX DEC2 MUX' MSM_DMIC
set_ctl 'TX DMIC MUX2' DMIC1
set_ctl 'TX_DEC2 Volume' 84

echo "--- verify ---"
for c in 'MultiMedia3 Mixer TX_CODEC_DMA_TX_3' 'TX_AIF1_CAP Mixer DEC2' \
         'TX DEC2 MUX' 'TX DMIC MUX2' 'TX_DEC2 Volume'; do
	printf '%-42s %s\n' "$c" "$(amixer $C cget name="$c" | grep -E '^  : values' | head -1)"
done
