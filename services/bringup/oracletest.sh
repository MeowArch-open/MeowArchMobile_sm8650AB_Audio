#!/bin/bash
# The Android reference state, now checkable without ears:
#   02 == 006c (bit 4 = TDMERR clear)   03 == 0000   04 == 0000
#   05 == 0000                          08 == 0000   0a == 0000
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
rd() { v=$(i2cget -y -f 0 $1 $2 w 2>/dev/null) || { printf "----"; return; }
	printf "%04x" $(( ((0x${v#0x} & 0xff) << 8) | ((0x${v#0x} >> 8) & 0xff) )); }
row() { printf "  %s  00:%s 01:%s 02:%s 03:%s 04:%s 05:%s 08:%s 0a:%s\n" "$1" \
	"$(rd $2 0x00)" "$(rd $2 0x01)" "$(rd $2 0x02)" "$(rd $2 0x03)" \
	"$(rd $2 0x04)" "$(rd $2 0x05)" "$(rd $2 0x08)" "$(rd $2 0x0a)"; }
python3 - <<'PY'
import math, struct, wave
t=[int(20000*math.sin(2*math.pi*440*i/48000)) for i in range(48000*12)]
w=wave.open("/tmp/t16.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
w.writeframes(b"".join(struct.pack("<hh",x,x) for x in t)); w.close()
w=wave.open("/tmp/t32.wav","wb"); w.setnchannels(2); w.setsampwidth(4); w.setframerate(48000)
w.writeframes(b"".join(struct.pack("<ii", x<<16, x<<16) for x in t)); w.close()
PY
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1,1
echo "  Android reference:  00:0502 01:8415 02:006c 03:0000 04:0000 05:0000 08:0000 0a:0000"
echo
for W in 16 32; do
	echo "$W" > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
	for F in t16 t32; do
		aplay -D hw:0,0 /tmp/$F.wav >/tmp/ap.log 2>&1 &
		AP=$!
		sleep 2
		if ! kill -0 $AP 2>/dev/null; then
			echo "  width=$W file=$F  -> aplay failed: $(tail -1 /tmp/ap.log)"
			continue
		fi
		echo "== BE width=$W, file=$F =="
		row "6c" 0x6c
		row "6d" 0x6d
		dmesg | grep q6dma_dbg | tail -1 | sed 's/^.*q6dma_dbg/     q6dma_dbg/'
		kill $AP 2>/dev/null; wait 2>/dev/null
		sleep 1
	done
done
echo 16 > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
