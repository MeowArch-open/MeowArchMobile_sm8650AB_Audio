#!/usr/bin/env python3
import sys, pathlib
p = pathlib.Path('/run/media/xingguangcuican/Project/testa/linux/sound/soc/codecs/sia91xx.c')
s = p.read_text()
if 'module_param' in s:
    print('already patched'); sys.exit(0)

old = '''#define SIA91XX_REG_STATE	0x01'''
new = '''/*
 * What to drive on the vendor's spksw-gpio at power-on: 1 or 0, or -1 to claim
 * the pin and leave it alone. A running Android reads 1 on the part that has the
 * pin, but it reads that with the amplifiers off, so the value that belongs with
 * playback is not actually known -- hence a knob rather than a constant.
 */
static int sia91xx_spksw = 1;
module_param_named(spksw, sia91xx_spksw, int, 0644);
MODULE_PARM_DESC(spksw, "value driven on spksw-gpio at power-on (-1 leaves it)");

#define SIA91XX_REG_STATE	0x01'''
assert old in s
s = s.replace(old, new, 1)

# apply it at power-on
old_on = '''	ret = sia91xx_state(sia, &state);
	if (ret)
		return ret;

	if (state == SIA91XX_STATE_ON)
		return 0;

	for (attempt = 0; attempt < 3; attempt++) {'''
new_on = '''	ret = sia91xx_state(sia, &state);
	if (ret)
		return ret;

	if (state == SIA91XX_STATE_ON)
		return 0;

	if (sia->spksw && sia91xx_spksw >= 0)
		gpiod_set_value_cansleep(sia->spksw, !!sia91xx_spksw);

	for (attempt = 0; attempt < 3; attempt++) {'''
assert old_on in s
s = s.replace(old_on, new_on, 1)

# probe: honour the knob's initial value too
old_gp = '''	sia->spksw = devm_gpiod_get_optional(sia->dev, "spksw", GPIOD_OUT_HIGH);'''
new_gp = '''	sia->spksw = devm_gpiod_get_optional(sia->dev, "spksw",
					    sia91xx_spksw > 0 ? GPIOD_OUT_HIGH
							      : GPIOD_OUT_LOW);'''
assert old_gp in s
s = s.replace(old_gp, new_gp, 1)
p.write_text(s)
print('spksw knob added, %d lines' % len(s.splitlines()))
