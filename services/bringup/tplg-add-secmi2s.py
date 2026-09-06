import re, sys, shutil
p = "/root/ar-tplg/SM8550-HDK.m4"
s = open(p).read()
if "SECONDARY_MI2S_RX" in s:
    print("already patched"); sys.exit(0)
shutil.copy(p, p + ".bak")

dev = """dnl
dnl Secondary MI2S Playback -- zorn: two SIA9187 amps on i2s1 (gpio121 sck /
dnl 123 ws / 124 data1 = SoC DOUT), so the sink drives SD1, not SD0.
DEVICE_SG_ADD(audioreach/subgraph-device-i2s-playback.m4, `Secondary', SECONDARY_MI2S_RX,
\t`S16_LE', 48000, 48000, 2, 2,
\tLPAIF_INTF_TYPE_LPAIF, I2S_INTF_TYPE_SECONDARY, SD_LINE_IDX_I2S_SD1, DATA_FORMAT_FIXED_POINT,
\t0x00004011, 0x00004011, 0x000060C0, `SECONDARY_MI2S_RX')
"""
anchor = "dnl\ndnl WCDRX Playback\n"
assert anchor in s
s = s.replace(anchor, dev + anchor, 1)

mx = "STREAM_DEVICE_PLAYBACK_MIXER(PRIMARY_MI2S_RX, ``PRIMARY_MI2S_RX'', ``MultiMedia1'', ``MultiMedia2'', ``MultiMedia5'')\n"
assert mx in s
s = s.replace(mx, mx + mx.replace("PRIMARY_MI2S_RX", "SECONDARY_MI2S_RX"), 1)

rt = "STREAM_DEVICE_PLAYBACK_ROUTE(PRIMARY_MI2S_RX, ``PRIMARY_MI2S_RX Audio Mixer''"
i = s.index(rt); j = s.index("\n", i) + 1
line = s[i:j]
s = s[:j] + line.replace("PRIMARY_MI2S_RX", "SECONDARY_MI2S_RX") + s[j:]
open(p, "w").write(s)
print("patched")
