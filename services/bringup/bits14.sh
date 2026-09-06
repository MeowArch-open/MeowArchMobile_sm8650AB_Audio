#!/bin/bash
# width=32 + 0x14=0x9328 already matches Android on 01/03/04/05/08/0a.
# Only 0x00 bit 10 and 0x02 bit 4 are left. Toggle each single bit of 0x14, 0x12
# and 0x17 from that state and watch those two.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
sw() { printf '0x%04x' $(( (($1 & 0xff) << 8) | (($1 >> 8) & 0xff) )); }
rd() { v=$(i2cget -y -f 0 $1 $2 w 2>/dev/null) || { echo 65535; return; }
	printf "%d" $(( ((0x${v#0x} & 0xff) << 8) | ((0x${v#0x} >> 8) & 0xff) )); }
bring() { A=$1; V12=$2; V14=$3; V17=$4
	i2cset -y -f 0 $A 0x13 $(sw 0x0381) w 2>/dev/null
	i2cget -y -f 0 $A 0x08 w >/dev/null 2>&1
	for pair in "0x09 0xffff" "0x14 $V14" "0x15 0x0a0a" "0x16 0x101b" "0x12 $V12" "0x13 0x0384" "0x17 $V17"; do
		set -- $pair; i2cset -y -f 0 $A $1 $(sw $2) w 2>/dev/null
	done
}
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1,1
echo 32 > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
aplay -D hw:0,0 /tmp/sw.wav >/dev/null 2>&1 &
AP=$!
sleep 2
show() { printf "  %-22s 00:%-5x 01:%-5x 02:%-4x 03:%-5x 08:%-4x 0a:%-4x%s\n" "$1" \
	$(rd 0x6c 0x00) $(rd 0x6c 0x01) $(rd 0x6c 0x02) $(rd 0x6c 0x03) $(rd 0x6c 0x08) $(rd 0x6c 0x0a) \
	"$( [ $(( $(rd 0x6c 0x02) & 0x10 )) -eq 0 ] && echo '  <== 02 bit4 CLEAR')"; }
echo "  target (Android)       00:502   01:8415  02:6c   03:0     08:0    0a:0"
bring 0x6c 0x9d60 0x9328 0x0418; sleep 0.3; show "baseline 14=9328"
for B in 0 1 2 3 4 8 9 10 11 14 15; do
	V=$(printf '0x%04x' $(( 0x9328 ^ (1 << B) )))
	bring 0x6c 0x9d60 $V 0x0418; sleep 0.3; show "14=$V (bit$B)"
done
for B in 0 1 2 4 5 6 7 8 12 13; do
	V=$(printf '0x%04x' $(( 0x9d60 ^ (1 << B) )))
	bring 0x6c $V 0x9328 0x0418; sleep 0.3; show "12=$V (bit$B)"
done
for B in 0 1 2 3 4 10 11; do
	V=$(printf '0x%04x' $(( 0x0418 ^ (1 << B) )))
	bring 0x6c 0x9d60 0x9328 $V; sleep 0.3; show "17=$V (bit$B)"
done
kill $AP 2>/dev/null; wait 2>/dev/null
echo 16 > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
