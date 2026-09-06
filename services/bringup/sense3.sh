#!/bin/bash
U=xingguangcuican; UID_=1001
run() { sudo -u $U XDG_RUNTIME_DIR=/run/user/$UID_ "$@"; }
run systemctl --user stop pipewire.socket pipewire-pulse.socket wireplumber pipewire pipewire-pulse 2>/dev/null
sleep 2
try() {
	echo "=== $1 ==="
	amixer -c0 -q cset name='MultiMedia3 Mixer SECONDARY_MI2S_TX' $2
	amixer -c0 -q cset name='MultiMedia3 Mixer VA_CODEC_DMA_TX_0' $3
	amixer -c0 -q cset name='MultiMedia3 Mixer TX_CODEC_DMA_TX_3' $4
	timeout 6 arecord -D hw:0,2 -f S16_LE -r 48000 -c 2 -d 3 /tmp/r.wav 2>&1 | tail -1
	python3 - <<'PY'
import wave, struct, math
try:
    w=wave.open("/tmp/r.wav","rb"); n=w.getnframes(); d=w.readframes(n)
    s=struct.unpack("<%dh"%(len(d)//2), d) if d else ()
    if not s: print("   -> no samples")
    else:
        print("   -> frames=%d peak=%d rms=%.1f nonzero=%d/%d" % (n, max(abs(x) for x in s),
              math.sqrt(sum(x*x for x in s)/len(s)), sum(1 for x in s if x), len(s)))
except Exception as e:
    print("   -> unreadable:", e)
PY
	rm -f /tmp/r.wav
}
try "VA_CODEC_DMA_TX_0 (control: known to open)" 0 1 0
try "SECONDARY_MI2S_TX (the amps' sense)" 1 0 0
run systemctl --user start wireplumber pipewire pipewire-pulse 2>/dev/null
