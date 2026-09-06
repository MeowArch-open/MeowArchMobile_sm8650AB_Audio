#!/bin/bash
# Try both DMIC routes now that the WCD is configured, and measure each.
C=-c0
s() { amixer $C -q cset name="$1" "$2" >/dev/null 2>&1; }

echo "=== TX macro route (vendor's dmic2: DEC2 <- MSM_DMIC <- DMIC1) ==="
s 'MultiMedia4 Mixer VA_CODEC_DMA_TX_0' 0,0
s 'MultiMedia4 Mixer TX_CODEC_DMA_TX_3' 1,1
s 'TX_AIF1_CAP Mixer DEC2' 1
s 'TX DEC2 MUX' MSM_DMIC
s 'TX DMIC MUX2' DMIC1
s 'TX_DEC2 Volume' 100
arecord -D hw:0,3 -f S16_LE -r 48000 -c 2 -d 2 /tmp/tx.wav 2>&1 | tail -1
python3 /root/wavlevel.py /tmp/tx.wav 2>/dev/null | head -2

echo "=== TX route, sweep DMIC0..3 ==="
for m in DMIC0 DMIC1 DMIC2 DMIC3; do
	s 'TX DMIC MUX2' $m
	arecord -D hw:0,3 -f S16_LE -r 48000 -c 2 -d 1 /tmp/tx.wav >/dev/null 2>&1
	printf '%-6s ' "$m"; python3 /root/wavlevel.py /tmp/tx.wav 2>/dev/null | head -1
done
