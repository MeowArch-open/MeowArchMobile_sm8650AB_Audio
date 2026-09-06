#!/usr/bin/env python3
import struct, sys
sys.path.insert(0, '/root')
from mapfw import resolve
import os

d = open('/lib/firmware/qcom/sm8650/adsp.b39', 'rb').read()
want = {0x0700100a: 'I2S_SINK', 0x0700100b: 'I2S_SOURCE',
        0x0700100c: '?', 0x0700100d: '?', 0x0700100e: '?', 0x0700100f: '?',
        0x07001023: 'CODEC_DMA_SINK', 0x07001069: 'DP_SINK'}
for o in range(0, len(d) - 15, 4):
    t, mid, p1, p2 = struct.unpack_from('<IIII', d, o)
    if mid in want and t == 0x0b:
        f1, o1 = resolve(p1)
        f2, o2 = resolve(p2)
        print(f"  {mid:#010x} {want[mid]:<15} ptr1={p1:#010x} -> "
              f"{os.path.basename(f1) if f1 else '??'}+{o1:#x}   "
              f"ptr2={p2:#010x} -> {os.path.basename(f2) if f2 else '??'}+{o2:#x}")
