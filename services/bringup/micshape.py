#!/usr/bin/env python3
import struct, sys, wave
w = wave.open(sys.argv[1], 'rb')
ch = w.getnchannels()
d = w.readframes(w.getnframes())
s = struct.unpack('<%dh' % (len(d) // 2), d)
left = list(s[0::ch])
nz = [(i, v) for i, v in enumerate(left) if v]
print(f"frames={len(left)} nonzero={len(nz)}")
print("first 20 nonzero (index, value):")
print("  " + ' '.join(f"{i}:{v}" for i, v in nz[:20]))
if len(nz) > 3:
    gaps = [nz[k + 1][0] - nz[k][0] for k in range(min(len(nz) - 1, 40))]
    print("gaps between first 40:", gaps[:20])
    print("mean gap %.1f" % (sum(gaps) / len(gaps)))
