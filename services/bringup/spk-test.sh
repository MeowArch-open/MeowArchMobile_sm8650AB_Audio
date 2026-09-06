#!/bin/bash
# SIA9187 speaker test: SECONDARY_MI2S_RX -> two sia91xx amps.
MARK=$(dmesg | wc -l)
say() { echo; echo "=== $* ==="; }

say "amps before"
for a in 0x6c 0x6d; do
	printf "  %s  01=%s 13=%s 15=%s\n" $a \
		"$(i2cget -y -f 0 $a 0x01 w 2>&1)" \
		"$(i2cget -y -f 0 $a 0x13 w 2>&1)" \
		"$(i2cget -y -f 0 $a 0x15 w 2>&1)"
done

say "route MultiMedia1 -> SECONDARY_MI2S_RX"
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1

python3 - <<'PY'
import math, struct, wave
w = wave.open("/tmp/tone.wav", "wb")
w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
f = [int(12000*math.sin(2*math.pi*440*i/48000)) for i in range(48000*5)]
w.writeframes(b"".join(struct.pack("<hh", s, s) for s in f))
w.close()
PY

say "playing 5 s of 440 Hz to hw:0,0"
( sleep 2
  echo "  -- amps while playing --"
  for a in 0x6c 0x6d; do
	printf "     %s  01=%s 13=%s 15=%s 12=%s 14=%s\n" $a \
		"$(i2cget -y -f 0 $a 0x01 w 2>&1)" \
		"$(i2cget -y -f 0 $a 0x13 w 2>&1)" \
		"$(i2cget -y -f 0 $a 0x15 w 2>&1)" \
		"$(i2cget -y -f 0 $a 0x12 w 2>&1)" \
		"$(i2cget -y -f 0 $a 0x14 w 2>&1)"
  done
  echo "  -- PA widget --"
  grep -H . /sys/kernel/debug/asoc/SM8650-MTP/sia91xx.0-006*/dapm/*PA 2>/dev/null | sed 's/^/     /'
) &
aplay -D hw:0,0 /tmp/tone.wav 2>&1 | tail -3
wait

say "amps after"
for a in 0x6c 0x6d; do
	printf "  %s  01=%s 13=%s\n" $a \
		"$(i2cget -y -f 0 $a 0x01 w 2>&1)" \
		"$(i2cget -y -f 0 $a 0x13 w 2>&1)"
done

say "dmesg since the test started"
dmesg | tail -n +$((MARK+1)) | tail -40
