#!/bin/bash
# Objective test: play full scale on the amps' RX and simultaneously record their
# I/V sense. Non-zero sense means they are driving; zeros mean they are not.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
python3 - <<'PY'
import struct, wave
for nm, amp in (("/tmp/loud.wav", 32000), ("/tmp/mute.wav", 0)):
    w=wave.open(nm,"wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
    p=[(amp if (i//50)%2==0 else -amp) for i in range(48000*8)]
    w.writeframes(b"".join(struct.pack("<hh",s,s) for s in p)); w.close()
PY
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1,1
amixer -c0 -q cset name='MultiMedia3 Mixer SECONDARY_MI2S_TX' 1,1
for tag in mute loud; do
	echo "=== RX playing $tag, recording the sense ==="
	aplay -D hw:0,0 /tmp/$tag.wav >/dev/null 2>&1 &
	AP=$!
	sleep 1
	v=$(i2cget -y -f 0 0x6c 0x01 w); echo "  6c state=$(( (0x${v#0x} >> 8) & 0xf ))"
	rm -f /tmp/s.wav
	timeout 8 arecord -D hw:0,2 -f S16_LE -r 48000 -c 2 -d 4 /tmp/s.wav 2>&1 | tail -1
	kill $AP 2>/dev/null; wait 2>/dev/null
	python3 /root/wavlevel.py /tmp/s.wav 2>/dev/null | sed 's/^/  /'
done
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
