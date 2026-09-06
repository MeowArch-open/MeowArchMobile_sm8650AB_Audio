#!/bin/bash
# Stop PipeWire so aplay can own hw:0,0 exclusively, dump both amps mid-stream,
# then bring PipeWire back.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
python3 - <<'PY'
import math, struct, wave
w=wave.open("/tmp/t30.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
f=[int(30000*math.sin(2*math.pi*440*i/48000)) for i in range(48000*20)]
w.writeframes(b"".join(struct.pack("<hh",s,s) for s in f)); w.close()
PY
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1
aplay -D hw:0,0 /tmp/t30.wav >/tmp/aplay.log 2>&1 &
AP=$!
sleep 4
v=$(i2cget -y -f 0 0x6c 0x01 w); echo "state 6c=$(( (0x${v#0x} >> 8) & 0xf ))"
v=$(i2cget -y -f 0 0x6d 0x01 w); echo "state 6d=$(( (0x${v#0x} >> 8) & 0xf ))"
for a in 0-006c 0-006d; do cp /sys/kernel/debug/regmap/$a/registers /root/linux-$a.txt; done
kill $AP 2>/dev/null; wait 2>/dev/null
cat /tmp/aplay.log
for a in 0-006c 0-006d; do
	echo "=== $a while playing ==="
	tr '\n' ' ' < /root/linux-$a.txt | fold -w 96
	echo
done
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
