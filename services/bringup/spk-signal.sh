#!/bin/bash
# Does the amplifier see samples? Compare its registers during a silent stretch
# and a full-scale stretch of the SAME playback, so the part stays enabled and
# only the audio content differs.
REGS=$(for r in 0 1 2 3 4 5 6 8 9 10 $(seq 17 49) $(seq 80 87) $(seq 110 119) 254 255; do printf '0x%02x ' $r; done)
dump() {
	for r in $REGS; do
		v=$(i2cget -y -f 0 $1 $r w 2>/dev/null) || continue
		printf "%s %04x\n" $r $(( ((0x${v#0x} & 0xff) << 8) | ((0x${v#0x} >> 8) & 0xff) ))
	done
}
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1
python3 - <<'PY'
import math, struct, wave
w = wave.open("/tmp/sig.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
q = [0]*(48000*4) + [int(30000*math.sin(2*math.pi*440*i/48000)) for i in range(48000*5)]
w.writeframes(b"".join(struct.pack("<hh",s,s) for s in q)); w.close()
PY
aplay -D hw:0,0 /tmp/sig.wav >/dev/null 2>&1 &
APID=$!
sleep 2
for a in 0x6c 0x6d; do dump $a > /tmp/silent-$a.txt; done
sleep 4
for a in 0x6c 0x6d; do dump $a > /tmp/loud-$a.txt; done
wait $APID
for a in 0x6c 0x6d; do
	echo "=== $a: digital silence -> full-scale 440 Hz (amp enabled throughout) ==="
	join /tmp/silent-$a.txt /tmp/loud-$a.txt | awk '$2!=$3 {printf "  %s  %s -> %s\n",$1,$2,$3}'
done
