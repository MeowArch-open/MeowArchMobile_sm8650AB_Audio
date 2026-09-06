#!/bin/bash
# 8 s of tone through the KDE path. Optional arg: spksw value (0 or 1).
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
st() { v=$(i2cget -y -f 0 $1 0x01 w); printf "%d" $(( (0x${v#0x} >> 8) & 0xf )); }
[ -n "$1" ] && { run pactl set-card-profile alsa_card.platform-sound off 2>/dev/null
	sleep 1; echo "$1" > /sys/module/snd_soc_sia91xx/parameters/spksw
	run pactl set-card-profile alsa_card.platform-sound pro-audio 2>/dev/null; sleep 2; }
[ -f /tmp/ab2.wav ] || python3 - <<'PY'
import math, struct, wave
w=wave.open("/tmp/ab2.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
f=[]
for n,fr in ((3,440),(3,880),(2,1320)): f += [int(30000*math.sin(2*math.pi*fr*i/48000)) for i in range(48000*n)]
w.writeframes(b"".join(struct.pack("<hh",s,s) for s in f)); w.close()
PY
chmod 644 /tmp/ab2.wav
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1
run pactl set-default-sink alsa_output.platform-sound.pro-output-0 2>/dev/null
run wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0 2>/dev/null
run wpctl set-mute @DEFAULT_AUDIO_SINK@ 0 2>/dev/null
T=$(md5sum /lib/firmware/qcom/sm8650/SM8650-MTP-tplg.bin | cut -c1-8)
case $T in b503b0fb) SD=SD0;; 825d6735) SD=SD1;; *) SD=$T;; esac
echo "topology=$SD  spksw=$(cat /sys/module/snd_soc_sia91xx/parameters/spksw)"
run paplay /tmp/ab2.wav >/dev/null 2>&1 &
PP=$!
sleep 3
echo "amps: 6c=$(st 0x6c) 6d=$(st 0x6d)  (5 = on)"
wait $PP
