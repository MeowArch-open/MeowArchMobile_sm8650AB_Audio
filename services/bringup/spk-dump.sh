#!/bin/bash
# Dump every readable SIA9187 register with and without audio on the link.
REGS="0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x08 0x09 0x0a $(seq -f '0x%02x' 17 49) $(seq -f '0x%02x' 80 87) $(seq -f '0x%02x' 110 119) 0xfe 0xff"
dump() {
	for r in $REGS; do
		v=$(i2cget -y -f 0 $1 $r w 2>/dev/null) || continue
		# i2cget prints little-endian; swap back to the chip's big-endian value
		printf "%s %04x\n" $r $(( ((0x${v#0x} & 0xff) << 8) | ((0x${v#0x} >> 8) & 0xff) ))
	done
}
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1
python3 - <<'PY'
import math, struct, wave
w = wave.open("/tmp/tone.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
f=[int(20000*math.sin(2*math.pi*440*i/48000)) for i in range(48000*8)]
w.writeframes(b"".join(struct.pack("<hh",s,s) for s in f)); w.close()
PY
for a in 0x6c 0x6d; do dump $a > /tmp/idle-$a.txt; done
aplay -D hw:0,0 /tmp/tone.wav >/dev/null 2>&1 &
APID=$!
sleep 3
for a in 0x6c 0x6d; do dump $a > /tmp/play-$a.txt; done
wait $APID
for a in 0x6c 0x6d; do
	echo "=== $a: idle -> playing ==="
	join /tmp/idle-$a.txt /tmp/play-$a.txt | awk '$2!=$3 {printf "  %s  %s -> %s\n",$1,$2,$3}'
done
