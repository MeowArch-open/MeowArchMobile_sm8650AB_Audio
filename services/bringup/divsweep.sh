#!/bin/bash
# Sweep every legal DMIC clock divider against every DMIC. The objective is the
# fraction of non-zero samples: a live PDM mic gives essentially 100%, while the
# decimator's HPF start-up transient alone gives ~600 out of 96000.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
C=-c0
amixer $C -q cset name='MultiMedia4 Mixer VA_CODEC_DMA_TX_0' 1,1
amixer $C -q cset name='VA_AIF1_CAP Mixer DEC0' 1
amixer $C -q cset name='VA DEC0 MUX' VA_DMIC
amixer $C -q cset name='VA_DEC0 Volume' 104
nz() { python3 - "$1" <<'PY'
import struct, sys, wave
try:
    w=wave.open(sys.argv[1],'rb'); ch=w.getnchannels()
    d=w.readframes(w.getnframes()); s=struct.unpack('<%dh'%(len(d)//2), d)
    l=list(s[0::ch])
    print("%5d/%d  peak=%d" % (sum(1 for x in l if x), len(l), max((abs(x) for x in l), default=0)))
except Exception as e:
    print("err", e)
PY
}
printf "%-6s %-7s %s\n" div mic "nonzero/total  peak"
for DIV in 1 2 3 4 5 6; do
	echo "$DIV" > /sys/module/snd_soc_lpass_va_macro/parameters/dmic_div
	R=$((9600000 / $(echo "2 3 4 6 8 16" | cut -d' ' -f$DIV)))
	for m in DMIC0 DMIC2 DMIC4 DMIC6; do
		amixer $C -q cset name='VA DMIC MUX0' $m
		rm -f /tmp/d.wav
		timeout 6 arecord -D hw:0,3 -f S16_LE -r 48000 -c 2 -d 2 /tmp/d.wav >/dev/null 2>&1
		printf "%-6s %-7s " "$R" "$m"
		nz /tmp/d.wav
	done
done
echo 0 > /sys/module/snd_soc_lpass_va_macro/parameters/dmic_div
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
