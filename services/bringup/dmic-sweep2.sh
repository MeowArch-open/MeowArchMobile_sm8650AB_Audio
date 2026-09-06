#!/bin/bash
# VA DEC0 MUX = VA_DMIC is the piece that was missing: it connects the decimator
# to the DMIC mux at all (same role as TX DEC0 MUX on the TX macro).
C=-c0
amixer $C -q cset name='MultiMedia4 Mixer VA_CODEC_DMA_TX_0' 1,1
amixer $C -q cset name='VA_AIF1_CAP Mixer DEC0' 1
amixer $C -q cset name='VA DEC0 MUX' VA_DMIC
for m in DMIC0 DMIC1 DMIC2 DMIC3; do
	amixer $C -q cset name='VA DMIC MUX0' $m
	arecord -D hw:0,3 -f S16_LE -r 48000 -c 2 -d 1 /tmp/s.wav >/dev/null 2>&1
	printf '%-6s ' "$m"
	python3 /root/wavlevel.py /tmp/s.wav 2>/dev/null | head -1
done
