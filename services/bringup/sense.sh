#!/bin/bash
# Record the amplifiers' own I/V sense while playing. This is the measurement I
# have been missing: the sense stream is the voltage and current at the speaker
# terminals, so silence there with a tone playing means the parts are not driving.
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
python3 - <<'PY'
import math, struct, wave
for name, amp in (("/tmp/loud.wav", 30000), ("/tmp/quiet.wav", 0)):
    w=wave.open(name,"wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
    f=[int(amp*math.sin(2*math.pi*440*i/48000)) for i in range(48000*8)]
    w.writeframes(b"".join(struct.pack("<hh",s,s) for s in f)); w.close()
PY
amixer -c0 -q cset name='SECONDARY_MI2S_RX Audio Mixer MultiMedia1' 1
amixer -c0 -q cset name='MultiMedia3 Mixer SECONDARY_MI2S_TX' 1
amixer -c0 -q cset name='MultiMedia3 Mixer VA_CODEC_DMA_TX_0' 0
amixer -c0 -q cset name='MultiMedia3 Mixer TX_CODEC_DMA_TX_3' 0

for tag in quiet loud; do
	echo "=== playing $tag, recording the sense ==="
	aplay -D hw:0,0 /tmp/$tag.wav >/dev/null 2>&1 &
	AP=$!
	sleep 1
	timeout 5 arecord -D hw:0,2 -f S16_LE -r 48000 -c 2 -d 4 /tmp/sense-$tag.wav 2>&1 | tail -2
	v=$(i2cget -y -f 0 0x6c 0x01 w); echo "  amp 6c state=$(( (0x${v#0x} >> 8) & 0xf ))"
	kill $AP 2>/dev/null; wait 2>/dev/null
done

python3 - <<'PY'
import wave, struct, math
for tag in ("quiet","loud"):
    try:
        w = wave.open(f"/tmp/sense-{tag}.wav","rb")
    except Exception as e:
        print(f"  {tag}: cannot open ({e})"); continue
    n = w.getnframes(); d = w.readframes(n)
    s = struct.unpack("<%dh" % (len(d)//2), d)
    if not s:
        print(f"  {tag}: empty"); continue
    peak = max(abs(x) for x in s)
    rms = math.sqrt(sum(x*x for x in s)/len(s))
    nz = sum(1 for x in s if x)
    print(f"  {tag:5s}: frames={n} peak={peak} rms={rms:.1f} nonzero={nz}/{len(s)}")
PY
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
