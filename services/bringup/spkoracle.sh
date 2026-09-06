#!/bin/bash
# Play a tone on the speakers, listen with the phone's own microphone.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
MIC=${MIC:-DMIC3}
FREQ=${FREQ:-1000}
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
C=-c0
amixer $C -q cset name='MultiMedia4 Mixer VA_CODEC_DMA_TX_0' 1,1
amixer $C -q cset name='VA_AIF1_CAP Mixer DEC0' 1
amixer $C -q cset name='VA DEC0 MUX' VA_DMIC
amixer $C -q cset name='VA DMIC MUX0' $MIC
amixer $C -q cset name='VA_DEC0 Volume' 84
amixer $C -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1,1
python3 - "$FREQ" <<'PY'
import math, struct, sys, wave
f0 = float(sys.argv[1])
for nm, amp in (("/tmp/o-mute.wav", 0), ("/tmp/o-tone.wav", 30000)):
    w=wave.open(nm,"wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
    s=[int(amp*math.sin(2*math.pi*f0*i/48000)) for i in range(48000*6)]
    w.writeframes(b"".join(struct.pack("<hh",x,x) for x in s)); w.close()
PY
for tag in mute tone; do
	aplay -D hw:0,0 /tmp/o-$tag.wav >/dev/null 2>&1 &
	AP=$!
	sleep 1
	rm -f /tmp/mic-$tag.wav
	timeout 8 arecord -D hw:0,3 -f S16_LE -r 48000 -c 2 -d 3 /tmp/mic-$tag.wav >/dev/null 2>&1
	kill $AP 2>/dev/null; wait 2>/dev/null
	printf '  %-5s ' "$tag"
	python3 /root/oracle.py /tmp/mic-$tag.wav $FREQ
done
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
