#!/bin/bash
# The interface-config registers, searched against an objective.
#
# The parts' factory values are known from the very first dump taken before any
# driver existed: 0x14 = 0x9328, 0x15 = 0x8808, 0x18 = 0x16b1 ... and the vendor
# writes 0x14 = 0xa3c8, 0x15 = 0x0a0a/0x0b0b. In 0x14 exactly two fields move,
# bits [13:12] 01 -> 10 and bits [7:5] 001 -> 110, which is what an interface
# mode and a frame-length field look like. If the factory value is plain I2S and
# the vendor's is their four-slot TDM, going back to the factory bits should make
# the parts decode what AudioReach can actually send.
#
# Objective: the amps' own I/V sense, recorded while a full-scale square plays.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
sw() { printf '0x%04x' $(( (($1 & 0xff) << 8) | (($1 >> 8) & 0xff) )); }
st() { v=$(i2cget -y -f 0 $1 0x01 w 2>/dev/null); [ -z "$v" ] && { printf x; return; }
	printf "%d" $(( (0x${v#0x} >> 8) & 0xf )); }
bring() {  # addr r14 r15 r16
	i2cset -y -f 0 $1 0x13 $(sw 0x0381) w 2>/dev/null
	i2cget -y -f 0 $1 0x08 w >/dev/null 2>&1
	A=$1
	for pair in "0x09 0xffff" "0x14 $2" "0x15 $3" "0x16 $4" "0x12 0x9d60" "0x13 0x0384" "0x17 0x0418"; do
		set -- $pair; i2cset -y -f 0 $A $1 $(sw $2) w 2>/dev/null
	done
}
python3 - <<'PY'
import struct, wave
w=wave.open("/tmp/sq8.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
p=[(32000 if (i//50)%2==0 else -32000) for i in range(48000*10)]
w.writeframes(b"".join(struct.pack("<hh",s,s) for s in p)); w.close()
PY
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1,1
amixer -c0 -q cset name='MultiMedia3 Mixer SECONDARY_MI2S_TX' 1,1
printf "%-8s %-8s %-8s %-6s %s\n" 0x14 "0x15 L/R" 0x16 state "sense peak / nonzero"
for R14 in 0xa3c8 0x93c8 0x9328 0xa328; do
 for R15 in "0x0a0a 0x0b0b" "0x8808 0x8808" "0x0808 0x0909"; do
  set -- $R15; L=$1; R=$2
  aplay -D hw:0,0 /tmp/sq8.wav >/dev/null 2>&1 &
  AP=$!
  sleep 1
  bring 0x6c $R14 $L 0x101b
  bring 0x6d $R14 $R 0x101b
  sleep 0.5
  S="$(st 0x6c)/$(st 0x6d)"
  rm -f /tmp/s.wav
  timeout 6 arecord -D hw:0,2 -f S16_LE -r 48000 -c 2 -d 2 /tmp/s.wav >/dev/null 2>&1
  kill $AP 2>/dev/null; wait 2>/dev/null
  M=$(python3 - <<'PY'
import wave, struct
try:
    w=wave.open("/tmp/s.wav","rb"); d=w.readframes(w.getnframes())
    s=struct.unpack("<%dh"%(len(d)//2), d) if d else ()
    print("peak=%d nonzero=%d/%d" % (max((abs(x) for x in s), default=0), sum(1 for x in s if x), len(s)))
except Exception as e:
    print("n/a")
PY
)
  printf "%-8s %-8s %-8s %-6s %s\n" $R14 "$L/$R" 0x101b "$S" "$M"
 done
done
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
