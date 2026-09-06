#!/bin/bash
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
C=-c0
amixer $C -q cset name='MultiMedia4 Mixer VA_CODEC_DMA_TX_0' 1,1
amixer $C -q cset name='VA_AIF1_CAP Mixer DEC0' 1
amixer $C -q cset name='VA DEC0 MUX' VA_DMIC
amixer $C -q cset name='VA DMIC MUX0' DMIC0
amixer $C -q cset name='VA_DEC0 Volume' 84
arecord -D hw:0,3 -f S16_LE -r 48000 -c 2 -d 4 /tmp/m.wav >/dev/null 2>&1 &
AR=$!
sleep 2
D=/sys/kernel/debug/asoc/SM8650-MTP
echo "=== VA macro widgets ==="
for w in "VA DMIC0" "VA DMIC MUX0" "VA DEC0 MUX" "VA_AIF1 CAP" "VA_DEC0" "vdd-micb"; do
	f="$D/6d44000.codec/dapm/$w"
	[ -f "$f" ] && head -1 "$f" | sed 's/^/  /'
done
echo "=== WCD mic bias widgets ==="
for w in "MIC BIAS1" "MIC BIAS2" "MIC BIAS3" "MIC BIAS4" "VA MIC BIAS3"; do
	for c in $D/*/dapm; do
		f="$c/$w"
		[ -f "$f" ] && head -1 "$f" | sed "s|^|  $(basename $(dirname $c)): |"
	done
done
echo "=== LPI dmic pins ==="
grep -E "gpio(6|7|8|9)\b" /sys/kernel/debug/pinctrl/*lpi*/pinmux-pins 2>/dev/null | head -6
grep -E "pin (6|7|8|9) " /sys/kernel/debug/pinctrl/6e80000.pinctrl/pinmux-pins 2>/dev/null | head -6
wait $AR
python3 /root/wavlevel.py /tmp/m.wav 2>/dev/null | sed 's/^/  /'
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
