#!/bin/bash
# Automated search with the Android criterion: clear 0x02 bit 4 (TDMERR) and get
# 0x03/0x04/0x05/0x08/0x0a to zero. 0x14's two moving fields are bits[13:12]
# (vendor 10, factory 01) and bits[7:5] (vendor 110, factory 001), so walk both.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
sw() { printf '0x%04x' $(( (($1 & 0xff) << 8) | (($1 >> 8) & 0xff) )); }
rd() { v=$(i2cget -y -f 0 $1 $2 w 2>/dev/null) || { echo 65535; return; }
	printf "%d" $(( ((0x${v#0x} & 0xff) << 8) | ((0x${v#0x} >> 8) & 0xff) )); }
bring() { A=$1; V14=$2; V15=$3; V16=$4
	i2cset -y -f 0 $A 0x13 $(sw 0x0381) w 2>/dev/null
	i2cget -y -f 0 $A 0x08 w >/dev/null 2>&1
	for pair in "0x09 0xffff" "0x14 $V14" "0x15 $V15" "0x16 $V16" "0x12 0x9d60" "0x13 0x0384" "0x17 0x0418"; do
		set -- $pair; i2cset -y -f 0 $A $1 $(sw $2) w 2>/dev/null
	done
}
python3 - <<'PY'
import math, struct, wave
w=wave.open("/tmp/sw.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
f=[int(20000*math.sin(2*math.pi*440*i/48000)) for i in range(48000*180)]
w.writeframes(b"".join(struct.pack("<hh",x,x) for x in f)); w.close()
PY
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1,1
echo 32 > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
aplay -D hw:0,0 /tmp/sw.wav >/dev/null 2>&1 &
AP=$!
sleep 2
printf "%-8s %-6s %-6s %-6s %-6s %-6s %-6s %-6s %s\n" 0x14 02 03 04 05 08 0a 01 verdict
BEST=""
for HI in 0 1 2 3; do
 for MID in 0 1 2 3 4 5 6 7; do
  V=$(( (0xa3c8 & ~0x30e0) | (HI << 12) | (MID << 5) ))
  V14=$(printf '0x%04x' $V)
  bring 0x6c $V14 0x0a0a 0x101b
  sleep 0.35
  r02=$(rd 0x6c 0x02); r03=$(rd 0x6c 0x03); r04=$(rd 0x6c 0x04)
  r05=$(rd 0x6c 0x05); r08=$(rd 0x6c 0x08); r0a=$(rd 0x6c 0x0a); r01=$(rd 0x6c 0x01)
  V=""
  [ $(( r02 & 0x10 )) -eq 0 ] && V="TDMERR-CLEAR"
  [ $r03 -eq 0 ] && [ $r04 -eq 0 ] && [ $r05 -eq 0 ] && V="$V diag-zero"
  printf "%-8s %-604x %-604x %-604x %-604x %-604x %-604x %-604x %s\n" \
    "$V14" $r02 $r03 $r04 $r05 $r08 $r0a $r01 "$V"
 done
done
kill $AP 2>/dev/null; wait 2>/dev/null
echo 16 > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
