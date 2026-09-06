#!/usr/bin/env python3
import sys, pathlib
p = pathlib.Path('/run/media/xingguangcuican/Project/testa/linux/sound/soc/codecs/sia91xx.c')
s = p.read_text()
if 'spksw' in s:
    print('already patched'); sys.exit(0)

old = '''struct sia91xx {
	const struct sia91xx_setup *setup;
	struct regmap *regmap;
	struct gpio_desc *reset;
	struct device *dev;
	unsigned int chipid;
};'''
new = '''struct sia91xx {
	const struct sia91xx_setup *setup;
	struct regmap *regmap;
	struct gpio_desc *reset;
	struct gpio_desc *spksw;
	struct device *dev;
	unsigned int chipid;
};'''
assert old in s
s = s.replace(old, new, 1)

old_probe = '''	sia->reset = devm_gpiod_get_optional(sia->dev, "reset", GPIOD_OUT_LOW);
	if (IS_ERR(sia->reset))
		return dev_err_probe(sia->dev, PTR_ERR(sia->reset),
				     "cannot get the reset gpio\\n");
	usleep_range(1000, 2000);'''
new_probe = '''	sia->reset = devm_gpiod_get_optional(sia->dev, "reset", GPIOD_OUT_LOW);
	if (IS_ERR(sia->reset))
		return dev_err_probe(sia->dev, PTR_ERR(sia->reset),
				     "cannot get the reset gpio\\n");

	/*
	 * The vendor's spksw-gpio, which only the left-hand part has. Its driver
	 * never touches it -- it is exposed as the sia91xx_spk_sw_gpio_switch
	 * kcontrol and the HAL sets it -- and on a running Android it is asserted
	 * while the right-hand part, which has no such pin, reads 0. So assert it
	 * once here and leave it, which is what Android's value amounts to.
	 */
	sia->spksw = devm_gpiod_get_optional(sia->dev, "spksw", GPIOD_OUT_HIGH);
	if (IS_ERR(sia->spksw))
		return dev_err_probe(sia->dev, PTR_ERR(sia->spksw),
				     "cannot get the speaker-switch gpio\\n");

	usleep_range(1000, 2000);'''
assert old_probe in s
s = s.replace(old_probe, new_probe, 1)
p.write_text(s)
print('spksw added, %d lines' % len(s.splitlines()))
