#!/bin/bash
# DMIC sweep at the new clock rate. Speak / make noise near the phone while this
# runs; any non-zero level means the microphone is alive.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
C=-c0
echo "dmic-sample-rate in DT: $(od -An -tu4 --endian=big /proc/device-tree/soc@0/codec@6d44000/qcom,dmic-sample-rate 2>/dev/null | tr -d ' ')"
dmesg | grep -i "Invalid rate" | tail -2
amixer $C -q cset name='MultiMedia4 Mixer VA_CODEC_DMA_TX_0' 1,1
amixer $C -q cset name='VA_AIF1_CAP Mixer DEC0' 1
amixer $C -q cset name='VA DEC0 MUX' VA_DMIC
amixer $C -q cset name='VA_DEC0 Volume' 84
for m in DMIC0 DMIC1 DMIC2 DMIC3 DMIC4 DMIC5 DMIC6 DMIC7; do
	amixer $C -q cset name='VA DMIC MUX0' $m 2>/dev/null || continue
	rm -f /tmp/s.wav
	timeout 6 arecord -D hw:0,3 -f S16_LE -r 48000 -c 2 -d 2 /tmp/s.wav >/dev/null 2>&1
	printf '  %-7s ' "$m"
	python3 /root/wavlevel.py /tmp/s.wav 2>/dev/null | head -1
done
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
