#!/bin/bash
# Automated search with an objective function instead of ears: for each SoC-side
# frame shape and amp slot setting, play 3 s of digital silence then 3 s of a
# full-scale square wave and measure how much the amps' live registers move. A
# combination where the parts actually receive audio cannot look the same under
# both halves.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
sw() { printf '0x%04x' $(( (($1 & 0xff) << 8) | (($1 >> 8) & 0xff) )); }
st() { v=$(i2cget -y -f 0 $1 0x01 w 2>/dev/null); [ -z "$v" ] && { echo x; return; }
	printf "%d" $(( (0x${v#0x} >> 8) & 0xf )); }
rd() { v=$(i2cget -y -f 0 $1 $2 w 2>/dev/null) || { echo 0; return; }
	printf "%d" $(( ((0x${v#0x} & 0xff) << 8) | ((0x${v#0x} >> 8) & 0xff) )); }
setslot() {
	A=$1; V=$2
	i2cset -y -f 0 $A 0x13 $(sw 0x0381) w 2>/dev/null
	i2cget -y -f 0 $A 0x08 w >/dev/null 2>&1
	for pair in "0x09 0xffff" "0x14 0xa3c8" "0x15 $V" "0x16 0x101b" "0x12 0x9d60" "0x13 0x0384" "0x17 0x0418"; do
		set -- $pair; i2cset -y -f 0 $A $1 $(sw $2) w 2>/dev/null
	done
}
python3 - <<'PY'
import struct, wave
w=wave.open("/tmp/g.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
q=[0]*(48000*4)
p=[(32767 if (i//50)%2==0 else -32768) for i in range(48000*4)]
w.writeframes(b"".join(struct.pack("<hh",s,s) for s in q+p)); w.close()
PY
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1
printf "%-4s %-4s %-14s %-8s %s\n" ch w "slots(L/R)" "state" "delta 03/04/05 (6c | 6d)"
for CH in 2 4; do
 for W in 16 32; do
  echo "$CH" > /sys/module/snd_soc_sc8280xp/parameters/mi2s_channels
  echo "$W"  > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
  for pair in "0x0a0a 0x0b0b" "0x0808 0x0909" "0x0000 0x0101"; do
	set -- $pair; L=$1; R=$2
	aplay -D hw:0,0 /tmp/g.wav >/tmp/ap.log 2>&1 &
	AP=$!
	sleep 1
	setslot 0x6c $L; setslot 0x6d $R
	sleep 1.5
	a1=$(rd 0x6c 0x03); a2=$(rd 0x6c 0x04); a3=$(rd 0x6c 0x05)
	b1=$(rd 0x6d 0x03); b2=$(rd 0x6d 0x04); b3=$(rd 0x6d 0x05)
	S="$(st 0x6c)/$(st 0x6d)"
	sleep 3
	c1=$(rd 0x6c 0x03); c2=$(rd 0x6c 0x04); c3=$(rd 0x6c 0x05)
	d1=$(rd 0x6d 0x03); d2=$(rd 0x6d 0x04); d3=$(rd 0x6d 0x05)
	kill $AP 2>/dev/null; wait 2>/dev/null
	ERR=$(grep -ciE "error|underrun" /tmp/ap.log)
	printf "%-4s %-4s %-14s %-8s %5d/%3d/%3d | %5d/%3d/%3d %s\n" $CH $W "$L/$R" "$S" \
		$((c1-a1)) $((c2-a2)) $((c3-a3)) $((d1-b1)) $((d2-b2)) $((d3-b3)) \
		"$([ $ERR -gt 0 ] && echo APLAY-ERR)"
  done
 done
done
echo 2  > /sys/module/snd_soc_sc8280xp/parameters/mi2s_channels
echo 16 > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
