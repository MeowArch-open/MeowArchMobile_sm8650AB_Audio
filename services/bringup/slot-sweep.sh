#!/bin/bash
# The vendor's sound node says qcom,tdm-max-slots = <4>, and the only register
# that differs between the two amps is 0x15: 0x0a0a on the left, 0x0b0b on the
# right. Read as bits[1:0] that is slot 2 and slot 3 of a four-slot frame -- and
# a plain two-slot I2S frame has no slot 2 or 3, which would look exactly like
# this: enabled, clock locked, no output.
#
# So walk the amps through slot pairs while a tone keeps playing. Shout out the
# step you can hear.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
sw() { printf '0x%04x' $(( (($1 & 0xff) << 8) | (($1 >> 8) & 0xff) )); }
st() { v=$(i2cget -y -f 0 $1 0x01 w); printf "%d" $(( (0x${v#0x} >> 8) & 0xf )); }
on() {  # $1 = addr, $2 = value for 0x15
	i2cset -y -f 0 $1 0x13 $(sw 0x0381) w
	i2cget -y -f 0 $1 0x08 w >/dev/null
	for pair in "0x09 0xffff" "0x14 0xa3c8" "0x15 $2" "0x16 0x101b" "0x12 0x9d60" "0x13 0x0384" "0x17 0x0418"; do
		set -- $1 $pair
		i2cset -y -f 0 $1 $2 $(sw $3) w
	done
}
python3 - <<'PY'
import math, struct, wave
w=wave.open("/tmp/sweep.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
f=[int(30000*math.sin(2*math.pi*440*i/48000)) for i in range(48000*60)]
w.writeframes(b"".join(struct.pack("<hh",s,s) for s in f)); w.close()
PY
chmod 644 /tmp/sweep.wav
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1
run pactl set-default-sink alsa_output.platform-sound.pro-output-0 2>/dev/null
run wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0 2>/dev/null
run wpctl set-mute @DEFAULT_AUDIO_SINK@ 0 2>/dev/null
run paplay /tmp/sweep.wav >/dev/null 2>&1 &
PP=$!
sleep 3
i=0
for pair in "0x0a0a 0x0b0b" "0x0808 0x0909" "0x0000 0x0101" "0x0202 0x0303" "0x0808 0x0808" "0x0000 0x0000"; do
	set -- $pair
	i=$((i+1))
	on 0x6c $1
	on 0x6d $2
	sleep 1
	echo "  step $i:  6c 0x15=$1 (state $(st 0x6c))   6d 0x15=$2 (state $(st 0x6d))"
	sleep 4
done
kill $PP 2>/dev/null
wait 2>/dev/null
echo "done -- which step, if any?"
