#!/bin/bash
# The WCD9395 headphone route, transcribed from the vendor HAL's "headphones"
# path (mixer_paths_pineapple_mtp.xml:744). Without a complete DAPM path from the
# backend to a real endpoint the DAI has nothing to start, which is its own -EIO
# independent of anything on the DSP side.
C=-c0
set_ctl() { amixer $C -q cset name="$1" "$2" 2>&1 | grep -v "^$" | head -1; }

set_ctl 'RX_CODEC_DMA_RX_0 Audio Mixer MultiMedia2' 1,1
set_ctl 'RX_MACRO RX0 MUX' AIF1_PB
set_ctl 'RX_MACRO RX1 MUX' AIF1_PB
set_ctl 'RX INT0_1 MIX1 INP0' RX0
set_ctl 'RX INT1_1 MIX1 INP0' RX1
set_ctl 'RX INT0 DEM MUX' CLSH_DSM_OUT
set_ctl 'RX INT1 DEM MUX' CLSH_DSM_OUT
set_ctl 'HPHL_RDAC Switch' 1
set_ctl 'HPHR_RDAC Switch' 1
set_ctl 'HPHL Switch' 1
set_ctl 'HPHR Switch' 1
set_ctl 'RX_RX0 Digital Volume' 84
set_ctl 'RX_RX1 Digital Volume' 84
echo "--- state ---"
for c in 'RX_MACRO RX0 MUX' 'RX INT0_1 MIX1 INP0' 'RX INT0 DEM MUX' 'HPHL_RDAC Switch' 'HPHL Switch'; do
	printf '%-34s %s\n' "$c" "$(amixer $C cget name="$c" | grep -E '^  : values' | head -1)"
done
