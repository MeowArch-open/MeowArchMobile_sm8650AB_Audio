#!/usr/bin/env python3
"""Add a SECONDARY_MI2S_TX capture device: the amplifiers' own I/V sense.

This is a measurement, not a feature. The amps' sense output is what tells us
whether they are actually driving the speakers -- it is literally the voltage and
current at the terminals -- and it also proves the framing works in the other
direction on the same link. The vendor's pin names say the SoC's input is
gpio122 = i2s1_data0, so the source module takes SD0 while playback keeps SD1.
"""
import pathlib, sys
p = pathlib.Path('/root/ar-tplg/SM8550-HDK.m4')
s = p.read_text()
if 'SECONDARY_MI2S_TX' in s:
    print('already patched'); sys.exit(0)

dev = """dnl
dnl Secondary MI2S Capture -- the two SIA9187s' I/V sense, on data0 (gpio122)
DEVICE_SG_ADD(audioreach/subgraph-device-i2s-capture.m4, `Secondary', SECONDARY_MI2S_TX,
\t`S16_LE', 48000, 48000, 1, 2,
\tLPAIF_INTF_TYPE_LPAIF, I2S_INTF_TYPE_SECONDARY, SD_LINE_IDX_I2S_SD0, DATA_FORMAT_FIXED_POINT,
\t0x00004012, 0x00004012, 0x000060D0, `SECONDARY_MI2S_TX', `SECONDARY_MI2S_TX')
"""
anchor = "dnl\ndnl Display port0 Playback\n"
assert anchor in s
s = s.replace(anchor, dev + anchor, 1)

for mm in ('FRONTEND_DAI_MULTIMEDIA3', 'FRONTEND_DAI_MULTIMEDIA4'):
    old = "STREAM_DEVICE_CAPTURE_MIXER(%s, ``VA_CODEC_DMA_TX_0'',``TX_CODEC_DMA_TX_3'' )" % mm
    new = "STREAM_DEVICE_CAPTURE_MIXER(%s, ``VA_CODEC_DMA_TX_0'',``TX_CODEC_DMA_TX_3'',``SECONDARY_MI2S_TX'' )" % mm
    assert old in s, old
    s = s.replace(old, new, 1)

n = 'MultiMedia3'
for mm, nm in (('FRONTEND_DAI_MULTIMEDIA3', 'MultiMedia3'), ('FRONTEND_DAI_MULTIMEDIA4', 'MultiMedia4')):
    old = ("STREAM_DEVICE_CAPTURE_ROUTE(%s, ``%s Mixer'', "
           "``VA_CODEC_DMA_TX_0, device110.logger1'', ``TX_CODEC_DMA_TX_3, device120.logger1'')" % (mm, nm))
    new = ("STREAM_DEVICE_CAPTURE_ROUTE(%s, ``%s Mixer'', "
           "``VA_CODEC_DMA_TX_0, device110.logger1'', ``TX_CODEC_DMA_TX_3, device120.logger1'', "
           "``SECONDARY_MI2S_TX, device19.logger1'')" % (mm, nm))
    assert old in s, old
    s = s.replace(old, new, 1)

p.write_text(s)
print('patched')
