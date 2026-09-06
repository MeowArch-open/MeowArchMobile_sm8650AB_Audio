#!/usr/bin/env python3
import re, sys, pathlib
p = pathlib.Path('/run/media/xingguangcuican/Project/testa/linux/sound/soc/codecs/sia91xx.c')
s = p.read_text()
if 'sia9187_defaults_ch0' in s:
    print('already patched'); sys.exit(0)
tables = pathlib.Path('/tmp/sia91xx_tables.h').read_text().rstrip('\n')

# --- 1. extend the file comment ---
old_tail = """ * The DAI description likewise comes from the vendor module's sia91xx_dai
 * (.rodata+0x2e28): "sia91xx-aif", S16/S24/S32, 11.025-64 kHz, 1-2 channels,
 * playback plus a capture side for the amplifier's I/V sense.
 */"""
new_tail = """ * The DAI description likewise comes from the vendor module's sia91xx_dai
 * (.rodata+0x2e28): "sia91xx-aif", S16/S24/S32, 11.025-64 kHz, 1-2 channels,
 * playback plus a capture side for the amplifier's I/V sense.
 *
 * The power-on sequence comes from the vendor's parameter file, /vendor/firmware/
 * sipa.bin (magic 32be86c7), whose layout the module's own accessors describe: a
 * 188-byte file header followed by one 1968-byte block per channel, each block
 * starting with the 192-byte chip config that sipa_param_read_chip_cfg() hands
 * out. Inside a config, the descriptor at +64 is {offset, count, entry_size} for
 * the register table sipa_regmap_defaults() writes (25 x 32 bytes:
 * { u32 reg; u32 mask; u32 val[6]; }, one value per audio scene) and the one at
 * +76 describes the list sipa_regmap_set_chip_on() runs (44 bytes:
 * { u32 reg; u32 mask; u32 op; u32 pad; u32 delay_us; u32 val[6]; }).
 *
 * The op field indexes a four-entry jump table at .rodata+0x4998:
 *
 *   0  read the register and fold the masked bits back into val[scene]
 *   1  write val[scene]; masked read-modify-write unless the mask covers the
 *      whole register
 *   2  read and verify (val[scene] ^ read) & mask == 0
 *   3  delay only
 *
 * The scene names are audio_scene[] at .rodata+0x3bf0: Playback, Voice, Voip,
 * Receiver, Factory, FM. This driver uses scene 0, and the tables below are
 * generated straight from zorn's sipa.bin, so they are the vendor's numbers
 * rather than an interpretation of them.
 *
 * Register 0x01's low nibble is the state field the vendor's lists check: 0 when
 * the part is idle, 5 once it is on, which is also how sipa_regmap_get_chip_en()
 * reads back an enabled sia9187. Register 0x13 carries the enable: 0x0384 on,
 * 0x0381 off. Register 0x15 is the only difference between the two channels'
 * power-on lists (0x0a0a against 0x0b0b), so it is where the part is told which
 * half of the I2S frame belongs to it.
 */"""
assert old_tail in s
s = s.replace(old_tail, new_tail, 1)
p.write_text(s)
print('comment updated')
