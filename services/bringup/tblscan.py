#!/usr/bin/env python3
"""Walk the ADSP module registry table found at adsp.b39+0x74ef3c.

Entries look like 16 bytes: { u32 type, u32 module_id, u32 ptr, u32 ptr }.
I2S_SINK/SOURCE (0x0700100a/b) carry type 0x0b, so type 0x0b is the hardware
endpoint class -- which is where a TDM endpoint would live.
"""
import struct

d = open('/lib/firmware/qcom/sm8650/adsp.b39', 'rb').read()
anchor = 0x74ef3c            # offset of the 0x0700100a word
base = anchor - 4            # start of that entry (type field)
# walk backwards to the table start, then forwards, collecting plausible entries
def ent(o):
    return struct.unpack_from('<IIII', d, o)

start = base
while start - 16 >= 0:
    t, mid, p1, p2 = ent(start - 16)
    if not (0x07000000 <= mid <= 0x0700ffff and t < 0x40):
        break
    start -= 16
end = base
while end + 16 <= len(d) - 16:
    t, mid, p1, p2 = ent(end + 16)
    if not (0x07000000 <= mid <= 0x0700ffff and t < 0x40):
        break
    end += 16
n = (end - start) // 16 + 1
print(f"table at adsp.b39+{start:#x}, {n} entries")
hw = []
for k in range(n):
    t, mid, p1, p2 = ent(start + k * 16)
    if t == 0x0b:
        hw.append(mid)
    print(f"  [{k:3d}] type={t:#04x} module_id={mid:#010x}")
print()
print("type 0x0b (hardware endpoints):", ' '.join(f"{m:#x}" for m in sorted(hw)))
