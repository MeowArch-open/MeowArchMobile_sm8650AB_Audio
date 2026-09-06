#!/bin/bash
# Frame-length sweep. The amps are configured for the vendor's four-slot TDM
# frame; two 16-bit channels only make a 32-bit frame. mi2s_width=32 makes the
# SoC send 64 bits per frame, which is what four 16-bit slots occupy. For each
# width, also walk the amps' 0x15 across the slot candidates.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
sw() { printf '0x%04x' $(( (($1 & 0xff) << 8) | (($1 >> 8) & 0xff) )); }
st() { v=$(i2cget -y -f 0 $1 0x01 w); printf "%d" $(( (0x${v#0x} >> 8) & 0xf )); }
on() {
	i2cset -y -f 0 $1 0x13 $(sw 0x0381) w
	i2cget -y -f 0 $1 0x08 w >/dev/null
	A=$1; V=$2
	for pair in "0x09 0xffff" "0x14 0xa3c8" "0x15 $V" "0x16 0x101b" "0x12 0x9d60" "0x13 0x0384" "0x17 0x0418"; do
		set -- $pair; i2cset -y -f 0 $A $1 $(sw $2) w
	done
}
[ -f /tmp/sweep.wav ] || python3 - <<'PY'
import math, struct, wave
w=wave.open("/tmp/sweep.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
f=[int(30000*math.sin(2*math.pi*440*i/48000)) for i in range(48000*60)]
w.writeframes(b"".join(struct.pack("<hh",s,s) for s in f)); w.close()
PY
chmod 644 /tmp/sweep.wav

for W in 32 16; do
	run pactl set-card-profile alsa_card.platform-sound off 2>/dev/null
	sleep 1
	echo "$W" > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
	run pactl set-card-profile alsa_card.platform-sound pro-audio 2>/dev/null
	sleep 2
	amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1
	run pactl set-default-sink alsa_output.platform-sound.pro-output-0 2>/dev/null
	run wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0 2>/dev/null
	run wpctl set-mute @DEFAULT_AUDIO_SINK@ 0 2>/dev/null
	echo "############ mi2s_width = $W ############"
	run paplay /tmp/sweep.wav >/dev/null 2>&1 &
	PP=$!
	sleep 3
	i=0
	for pair in "0x0a0a 0x0b0b" "0x0808 0x0909" "0x0000 0x0101"; do
		set -- $pair; i=$((i+1))
		on 0x6c $1; on 0x6d $2
		sleep 1
		echo "  w=$W step $i: 6c 0x15=$1 (st $(st 0x6c))  6d 0x15=$2 (st $(st 0x6d))"
		sleep 4
	done
	kill $PP 2>/dev/null; wait 2>/dev/null
done
echo "mi2s_width left at $(cat /sys/module/snd_soc_sc8280xp/parameters/mi2s_width)"
