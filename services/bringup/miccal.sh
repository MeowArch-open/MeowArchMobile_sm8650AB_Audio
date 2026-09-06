#!/bin/bash
# Which mic hears best, and does the path scale with gain? Also: is the noise
# floor real (a live mic) or a dead zero (broken path)?
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
C=-c0
amixer $C -q cset name='MultiMedia4 Mixer VA_CODEC_DMA_TX_0' 1,1
amixer $C -q cset name='VA_AIF1_CAP Mixer DEC0' 1
amixer $C -q cset name='VA DEC0 MUX' VA_DMIC
echo "=== VA_DEC0 Volume range ==="
amixer $C cget name='VA_DEC0 Volume' | grep -E "min=|: values"
for G in 84 104 124; do
	amixer $C -q cset name='VA_DEC0 Volume' $G 2>/dev/null || continue
	amixer $C -q cset name='VA DMIC MUX0' DMIC3
	rm -f /tmp/g.wav
	timeout 6 arecord -D hw:0,3 -f S16_LE -r 48000 -c 2 -d 2 /tmp/g.wav >/dev/null 2>&1
	printf '  gain=%-4s ' $G
	python3 /root/wavlevel.py /tmp/g.wav 2>/dev/null | head -1
done
amixer $C -q cset name='VA_DEC0 Volume' 104
echo "=== per-mic ambient level at gain 104 ==="
for m in DMIC0 DMIC1 DMIC2 DMIC3 DMIC4 DMIC5 DMIC6 DMIC7; do
	amixer $C -q cset name='VA DMIC MUX0' $m
	rm -f /tmp/g.wav
	timeout 6 arecord -D hw:0,3 -f S16_LE -r 48000 -c 2 -d 2 /tmp/g.wav >/dev/null 2>&1
	printf '  %-7s ' $m
	python3 /root/wavlevel.py /tmp/g.wav 2>/dev/null | head -1
done
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
