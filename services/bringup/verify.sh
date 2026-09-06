#!/bin/bash
# Straight out of the box now: no manual register pokes, just play and compare.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
rd() { v=$(i2cget -y -f 0 $1 $2 w 2>/dev/null) || { printf "----"; return; }
	printf "%04x" $(( ((0x${v#0x} & 0xff) << 8) | ((0x${v#0x} >> 8) & 0xff) )); }
row() { printf "  %s  00:%s 01:%s 02:%s 03:%s 04:%s 05:%s 08:%s 0a:%s  13:%s 14:%s 15:%s\n" "$1" \
	"$(rd $2 0x00)" "$(rd $2 0x01)" "$(rd $2 0x02)" "$(rd $2 0x03)" "$(rd $2 0x04)" \
	"$(rd $2 0x05)" "$(rd $2 0x08)" "$(rd $2 0x0a)" "$(rd $2 0x13)" "$(rd $2 0x14)" "$(rd $2 0x15)"; }
echo "  width default = $(cat /sys/module/snd_soc_sc8280xp/parameters/mi2s_width)"
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
[ -f /tmp/sw.wav ] || python3 -c "
import math, struct, wave
w=wave.open('/tmp/sw.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
f=[int(20000*math.sin(2*math.pi*440*i/48000)) for i in range(48000*30)]
w.writeframes(b''.join(struct.pack('<hh',x,x) for x in f)); w.close()"
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1,1
echo "  Android:  00:0502 01:8415 02:006c 03:0000 04:0000 05:0000 08:0000 0a:0000  13:0384 14:a3c8 15:0a0a"
aplay -D hw:0,0 /tmp/sw.wav >/dev/null 2>&1 &
AP=$!
sleep 3
row "6c" 0x6c
row "6d" 0x6d
kill $AP 2>/dev/null; wait 2>/dev/null
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
