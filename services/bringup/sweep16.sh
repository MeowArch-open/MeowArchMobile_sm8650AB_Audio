#!/bin/bash
# 0x14 = 0x9328 (the part's factory value) already reproduces Android's 0x01 =
# 8415 and gets 0x03/0x04/0x05/0x08/0x0a to zero -- only 0x02 bit 4 is still set.
# Now walk 0x16's low five bits with 0x14 pinned to the good candidates.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
sw() { printf '0x%04x' $(( (($1 & 0xff) << 8) | (($1 >> 8) & 0xff) )); }
rd() { v=$(i2cget -y -f 0 $1 $2 w 2>/dev/null) || { echo 65535; return; }
	printf "%d" $(( ((0x${v#0x} & 0xff) << 8) | ((0x${v#0x} >> 8) & 0xff) )); }
bring() { A=$1; V14=$2; V16=$3
	i2cset -y -f 0 $A 0x13 $(sw 0x0381) w 2>/dev/null
	i2cget -y -f 0 $A 0x08 w >/dev/null 2>&1
	for pair in "0x09 0xffff" "0x14 $V14" "0x15 0x0a0a" "0x16 $V16" "0x12 0x9d60" "0x13 0x0384" "0x17 0x0418"; do
		set -- $pair; i2cset -y -f 0 $A $1 $(sw $2) w 2>/dev/null
	done
}
[ -f /tmp/sw.wav ] || python3 - <<'PY'
import math, struct, wave
w=wave.open("/tmp/sw.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
f=[int(20000*math.sin(2*math.pi*440*i/48000)) for i in range(48000*180)]
w.writeframes(b"".join(struct.pack("<hh",x,x) for x in f)); w.close()
PY
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1,1
for W in 32 16; do
echo "############ BE width = $W ############"
echo "$W" > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
aplay -D hw:0,0 /tmp/sw.wav >/dev/null 2>&1 &
AP=$!
sleep 2
echo "  target (Android): 00:502 01:8415 02:6c 03:0 04:0 05:0 08:0 0a:0"
printf "  %-8s %-8s %-5s %-6s %-5s %-5s %-5s %-5s %-5s %s\n" 0x14 0x16 00 01 02 03 04 05 08 0a
for V14 in 0x9328 0xa328; do
 for LOW in 0x00 0x08 0x0b 0x10 0x13 0x18 0x1b 0x1f; do
  V16=$(printf '0x%04x' $(( (0x101b & ~0x1f) | LOW )))
  bring 0x6c $V14 $V16
  sleep 0.3
  printf "  %-8s %-8s %-5x %-6x %-5x %-5x %-5x %-5x %-5x %-5x" "$V14" "$V16" \
    $(rd 0x6c 0x00) $(rd 0x6c 0x01) $(rd 0x6c 0x02) $(rd 0x6c 0x03) \
    $(rd 0x6c 0x04) $(rd 0x6c 0x05) $(rd 0x6c 0x08) $(rd 0x6c 0x0a)
  echo
 done
done
kill $AP 2>/dev/null; wait 2>/dev/null
done
echo 16 > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
