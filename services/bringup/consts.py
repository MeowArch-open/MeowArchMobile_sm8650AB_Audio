#!/usr/bin/env python3
import re, subprocess, sys

CHUNK = '/tmp/chunk.bin'
BASE = 0x610bc0
d = open(CHUNK, 'rb').read()


def dis(vaddr_off, n=0x180):
    s = vaddr_off - BASE
    hx = ','.join('0x%02x' % b for b in d[s:s + n])
    open('/tmp/_x.hex', 'w').write(hx)
    return subprocess.run(['llvm-mc', '--disassemble', '--triple=hexagon', '/tmp/_x.hex'],
                          capture_output=True, text=True).stdout


mods = [(0x0700100a, 'I2S_SINK', 0x61742c), (0x0700100b, 'I2S_SOURCE', 0x6176a8),
        (0x0700100c, 'cand-c', 0x61b924), (0x0700100d, 'cand-d', 0x61bbd4),
        (0x0700100e, 'cand-e', 0x61bc18), (0x0700100f, 'cand-f', 0x61bc28),
        (0x07001023, 'CODEC_DMA_SINK', 0x6118f8), (0x07001069, 'DP_SINK', 0x613f40)]
for mid, name, off in mods:
    txt = dis(off)
    vals = sorted({int(m) for m in re.findall(r'##(\d+)', txt)})
    ptrs = [v for v in vals if 0xb0000000 <= v <= 0xb1000000]
    fwk = [v for v in vals if 0x0a000000 <= v <= 0x0b000000]
    par = [v for v in vals if 0x08000000 <= v <= 0x09000000]
    other = [v for v in vals if v not in ptrs + fwk + par]
    print(f"{mid:#010x} {name:<15} @{off:#x}")
    print("   ptrs:", ' '.join(f"{v:#x}" for v in ptrs) or '-')
    print("   fwk :", ' '.join(f"{v:#x}" for v in fwk) or '-')
    print("   parm:", ' '.join(f"{v:#x}" for v in par) or '-')
    print("   misc:", ' '.join(str(v) for v in other[:10]) or '-')
