#!/bin/bash
# Measured sweep. For each backend width, play digital silence then a full-scale
# square wave (maximum power into the load) and diff the amps' registers. A part
# that is actually driving a speaker cannot look identical under those two.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
REGS=$(for r in 0 1 2 3 4 5 8 10 $(seq 17 49) $(seq 80 87) $(seq 110 119); do printf '0x%02x ' $r; done)
dump() { for r in $REGS; do v=$(i2cget -y -f 0 $1 $r w 2>/dev/null) || continue
	printf "%s %04x\n" $r $(( ((0x${v#0x} & 0xff) << 8) | ((0x${v#0x} >> 8) & 0xff) )); done; }
st() { v=$(i2cget -y -f 0 $1 0x01 w); printf "%d" $(( (0x${v#0x} >> 8) & 0xf )); }

python3 - <<'PY'
import struct, wave
w=wave.open("/tmp/sq.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
q=[0]*(48000*5)
p=[(32767 if (i//50)%2==0 else -32768) for i in range(48000*6)]   # ~480 Hz square, full scale
w.writeframes(b"".join(struct.pack("<hh",s,s) for s in q+p)); w.close()
PY
run pactl set-card-profile alsa_card.platform-sound off 2>/dev/null
sleep 2
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1

for W in 16 32; do
	echo "$W" > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
	MARK=$(dmesg | wc -l)
	echo "################ mi2s_width = $W ################"
	aplay -D hw:0,0 /tmp/sq.wav >/dev/null 2>&1 &
	AP=$!
	sleep 2
	echo "  silence: 6c st=$(st 0x6c) 6d st=$(st 0x6d)"
	for a in 0x6c 0x6d; do dump $a > /tmp/q-$a-$W.txt; done
	sleep 5
	echo "  square:  6c st=$(st 0x6c) 6d st=$(st 0x6d)"
	for a in 0x6c 0x6d; do dump $a > /tmp/p-$a-$W.txt; done
	wait $AP 2>/dev/null
	dmesg | tail -n +$((MARK+1)) | grep -E "q6dma_dbg|fixup_dbg" | tail -4 | sed 's/^/  /'
	for a in 0x6c 0x6d; do
		echo "  --- $a silence -> full-scale square ---"
		join /tmp/q-$a-$W.txt /tmp/p-$a-$W.txt | awk '$2!=$3 {printf "     %s  %s -> %s\n",$1,$2,$3}'
	done
done
echo 16 > /sys/module/snd_soc_sc8280xp/parameters/mi2s_width
run pactl set-card-profile alsa_card.platform-sound pro-audio 2>/dev/null
