#!/usr/bin/env python3
import sys, pathlib
p = pathlib.Path('/run/media/xingguangcuican/Project/testa/linux/sound/soc/codecs/sia91xx.c')
s = p.read_text()
if 'sia9187_defaults_ch0' in s:
    print('already patched'); sys.exit(0)
tables = pathlib.Path('/tmp/sia91xx_tables.h').read_text().rstrip('\n')

old = """#define SIA91XX_REG_CHIPID	0x06

/* From reg_map_info_table entry 0x13. */
#define SIA9187_ID_FIRST	0x5d80
#define SIA9187_ID_LAST		0x5d90

struct sia91xx {
	struct regmap *regmap;
	struct gpio_desc *reset;
	struct device *dev;
	unsigned int chipid;
};
"""
new = """#define SIA91XX_REG_STATE	0x01
#define SIA91XX_REG_CHIPID	0x06
#define SIA91XX_REG_ENABLE	0x13

/* Register 0x01's low nibble, as the vendor's own verify steps read it. */
#define SIA91XX_STATE		GENMASK(3, 0)
#define SIA91XX_STATE_IDLE	0x0
#define SIA91XX_STATE_ON	0x5

#define SIA9187_DISABLE		0x0381

/* From reg_map_info_table entry 0x13. */
#define SIA9187_ID_FIRST	0x5d80
#define SIA9187_ID_LAST		0x5d90

struct sia91xx_reg {
	u8 reg;
	u16 val;
};

struct sia91xx_setup {
	const struct sia91xx_reg *defaults;
	unsigned int num_defaults;
	const struct sia91xx_reg *power_on;
	unsigned int num_power_on;
};

struct sia91xx {
	const struct sia91xx_setup *setup;
	struct regmap *regmap;
	struct gpio_desc *reset;
	struct device *dev;
	unsigned int chipid;
};

__TABLES__

#define SIA9187_CHANNEL(n) {						\\
	.defaults	= sia9187_defaults_##n,				\\
	.num_defaults	= ARRAY_SIZE(sia9187_defaults_##n),		\\
	.power_on	= sia9187_power_on_##n,				\\
	.num_power_on	= ARRAY_SIZE(sia9187_power_on_##n),		\\
}

/*
 * One entry per channel, in the order sipa.bin stores them, which is the order
 * the vendor's channel_num indexes. zorn wires channel 0 to 0x6c and channel 1
 * to 0x6d, and the only register that differs is 0x15 -- the I2S slot -- so
 * getting this backwards would swap the speakers rather than break them.
 */
static const struct sia91xx_setup sia9187_setup[] = {
	SIA9187_CHANNEL(ch0),
	SIA9187_CHANNEL(ch1),
};
"""
assert old in s
s = s.replace(old, new.replace('__TABLES__', tables), 1)
p.write_text(s)
print('tables inserted, now %d lines' % len(s.splitlines()))
