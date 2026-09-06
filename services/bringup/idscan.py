#!/usr/bin/env python3
import glob, struct, collections, os
target = 0x0700100A          # MODULE_ID_I2S_SINK, known good
found = []
for f in sorted(glob.glob('/lib/firmware/qcom/sm8650/adsp.b*')):
    try:
        d = open(f, 'rb').read()
    except Exception:
        continue
    for o in range(0, len(d) - 3, 4):
        if struct.unpack_from('<I', d, o)[0] == target:
            found.append((f, o, d))
print("I2S_SINK id occurrences:", len(found))
for f, o, d in found[:6]:
    ctx = [struct.unpack_from('<I', d, o + k * 4)[0] for k in range(-6, 10)]
    print(f"  {os.path.basename(f)}+{o:#x}: " + ' '.join(f"{v:08x}" for v in ctx))
