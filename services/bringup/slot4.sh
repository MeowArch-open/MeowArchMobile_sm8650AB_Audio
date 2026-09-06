#!/bin/bash
# Four real slots, and now a four-channel front end, so the tone can be put in a
# chosen slot pair instead of relying on the ADSP to upmix. If the amps listen on
# slots 2/3 (0x15 = 0x0a0a/0x0b0b) then only the "hi" file should be audible with
# the vendor's 0x15, and only the "lo" file with 0x15 moved to slots 0/1.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
sw() { printf '0x%04x' $(( (($1 & 0xff) << 8) | (($1 >> 8) & 0xff) )); }
st() { v=$(i2cget -y -f 0 $1 0x01 w 2>/dev/null); [ -z "$v" ] && { printf x; return; }
	printf "%d" $(( (0x${v#0x} >> 8) & 0xf )); }
bring() { A=$1; V=$2
	i2cset -y -f 0 $A 0x13 $(sw 0x0381) w 2>/dev/null
	i2cget -y -f 0 $A 0x08 w >/dev/null 2>&1
	for pair in "0x09 0xffff" "0x14 0xa3c8" "0x15 $V" "0x16 0x101b" "0x12 0x9d60" "0x13 0x0384" "0x17 0x0418"; do
		set -- $pair; i2cset -y -f 0 $A $1 $(sw $2) w 2>/dev/null
	done
}
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1,1
python3 - <<'PY'
import math, struct, wave
t=[int(30000*math.sin(2*math.pi*660*i/48000)) for i in range(48000*5)]
for nm, m in (("/tmp/s4all.wav",(1,1,1,1)), ("/tmp/s4lo.wav",(1,1,0,0)), ("/tmp/s4hi.wav",(0,0,1,1))):
    w=wave.open(nm,"wb"); w.setnchannels(4); w.setsampwidth(2); w.setframerate(48000)
    w.writeframes(b"".join(struct.pack("<hhhh", *[x*c for c in m]) for x in t)); w.close()
PY
i=0
for SL in "0x0a0a 0x0b0b" "0x0808 0x0909"; do
	set -- $SL; L=$1; R=$2
	for f in s4all s4lo s4hi; do
		i=$((i+1))
		aplay -D hw:0,0 /tmp/$f.wav >/tmp/ap.log 2>&1 &
		AP=$!
		sleep 0.7
		if ! kill -0 $AP 2>/dev/null; then echo "  step $i: aplay failed -- $(tail -1 /tmp/ap.log)"; continue; fi
		bring 0x6c $L; bring 0x6d $R
		sleep 0.4
		echo "  step $i:  0x15=$L/$R  content=$f  amps $(st 0x6c)/$(st 0x6d)   (660 Hz, ~3.5 s)"
		sleep 3.4
		kill $AP 2>/dev/null; wait 2>/dev/null
	done
done
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
