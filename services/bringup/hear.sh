#!/bin/bash
# 12 s of tone through the KDE/PipeWire path, then the amps' state.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
rd() { v=$(i2cget -y -f 0 $1 $2 w 2>/dev/null) || { printf "----"; return; }
	printf "%04x" $(( ((0x${v#0x} & 0xff) << 8) | ((0x${v#0x} >> 8) & 0xff) )); }
python3 -c "
import math, struct, wave
w=wave.open('/tmp/hear.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
f=[]
for fr in (440,660,880,440): f += [int(26000*math.sin(2*math.pi*fr*i/48000)) for i in range(48000*3)]
w.writeframes(b''.join(struct.pack('<hh',x,x) for x in f)); w.close()"
chmod 644 /tmp/hear.wav
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1,1
run pactl set-card-profile alsa_card.platform-sound pro-audio 2>/dev/null
run pactl set-default-sink alsa_output.platform-sound.pro-output-0 2>/dev/null
run wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.6 2>/dev/null
run wpctl set-mute @DEFAULT_AUDIO_SINK@ 0 2>/dev/null
echo "  playing 12 s (440 / 660 / 880 / 440 Hz)"
run paplay /tmp/hear.wav >/dev/null 2>&1 &
PP=$!
sleep 3
printf "  6c  00:%s 01:%s 02:%s 03:%s 08:%s 0a:%s\n" "$(rd 0x6c 0x00)" "$(rd 0x6c 0x01)" \
	"$(rd 0x6c 0x02)" "$(rd 0x6c 0x03)" "$(rd 0x6c 0x08)" "$(rd 0x6c 0x0a)"
printf "  6d  00:%s 01:%s 02:%s 03:%s 08:%s 0a:%s\n" "$(rd 0x6d 0x00)" "$(rd 0x6d 0x01)" \
	"$(rd 0x6d 0x02)" "$(rd 0x6d 0x03)" "$(rd 0x6d 0x08)" "$(rd 0x6d 0x0a)"
echo "  (Android reference: 00:0502 01:8415 02:006c 03:0000 08:0000 0a:0000)"
wait $PP
