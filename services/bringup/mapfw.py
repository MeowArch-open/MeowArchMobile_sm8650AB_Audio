#!/usr/bin/env python3
"""Map ADSP virtual addresses to firmware file offsets.

adsp.mbn is the ELF header plus program headers; each PT_LOAD segment's bytes
live in adsp.bNN, numbered by segment index. That is enough to follow the
pointers in the module registry.
"""
import struct, glob, os, sys

FW = '/lib/firmware/qcom/sm8650'
mbn = open(f'{FW}/adsp.mbn', 'rb').read()
assert mbn[:4] == b'\x7fELF', 'not an ELF'
is64 = mbn[4] == 2
if is64:
    e_phoff, = struct.unpack_from('<Q', mbn, 0x20)
    e_phentsize, e_phnum = struct.unpack_from('<HH', mbn, 0x36)
else:
    e_phoff, = struct.unpack_from('<I', mbn, 0x1c)
    e_phentsize, e_phnum = struct.unpack_from('<HH', mbn, 0x2a)
print(f"elf{'64' if is64 else '32'} phoff={e_phoff:#x} phnum={e_phnum} phentsize={e_phentsize}")

segs = []
for i in range(e_phnum):
    o = e_phoff + i * e_phentsize
    if is64:
        p_type, p_flags = struct.unpack_from('<II', mbn, o)
        p_offset, p_vaddr, p_paddr, p_filesz, p_memsz = struct.unpack_from('<QQQQQ', mbn, o + 8)
    else:
        p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags = \
            struct.unpack_from('<IIIIIII', mbn, o)
    segs.append((i, p_type, p_vaddr, p_filesz, p_memsz))

files = {}
for f in glob.glob(f'{FW}/adsp.b*'):
    b = os.path.basename(f)
    if b.startswith('adsp.b') and b[6:].isdigit():
        files[int(b[6:])] = f


def resolve(vaddr):
    for i, p_type, p_vaddr, p_filesz, p_memsz in segs:
        if p_filesz and p_vaddr <= vaddr < p_vaddr + p_filesz and i in files:
            return files[i], vaddr - p_vaddr
    return None, None


if __name__ == '__main__':
    for v in [int(x, 16) for x in sys.argv[1:]] or [0xb071742c]:
        f, off = resolve(v)
        print(f"  {v:#x} -> {os.path.basename(f) if f else '??'}+{off:#x}" if f else f"  {v:#x} -> unmapped")
