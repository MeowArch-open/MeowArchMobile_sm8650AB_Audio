import struct, sys
p = sys.argv[1] if len(sys.argv) > 1 else "/tmp/va.wav"
d = open(p, "rb").read()
i = d.find(b"data")
pcm = d[i+8:]
n = len(pcm) // 2
v = struct.unpack("<%dh" % n, pcm[:n*2])
full = 2 ** 15
for nm, ch in (("L", v[0::2]), ("R", v[1::2])):
    pk = max(abs(x) for x in ch)
    rms = (sum(float(x)*x for x in ch) / len(ch)) ** 0.5
    print("%s: n=%d peak %.3f%% FS  rms %.4f%% FS  nonzero %d/%d"
          % (nm, len(ch), 100*pk/full, 100*rms/full, sum(1 for x in ch if x), len(ch)))
