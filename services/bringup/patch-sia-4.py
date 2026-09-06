#!/usr/bin/env python3
import sys, pathlib
p = pathlib.Path('/run/media/xingguangcuican/Project/testa/linux/sound/soc/codecs/sia91xx.c')
s = p.read_text()

# widgets + routes: put a driver stage between the DAI and the output pin
old = '''static const struct snd_soc_dapm_widget sia91xx_widgets[] = {
	SND_SOC_DAPM_OUTPUT("OUT"),
	SND_SOC_DAPM_INPUT("IV"),
};

static const struct snd_soc_dapm_route sia91xx_routes[] = {
	{ "OUT", NULL, "AIF Playback" },
	{ "AIF Capture", NULL, "IV" },
};'''
new = '''static const struct snd_soc_dapm_widget sia91xx_widgets[] = {
	SND_SOC_DAPM_OUT_DRV_E("PA", SND_SOC_NOPM, 0, 0, NULL, 0,
			       sia91xx_pa_event,
			       SND_SOC_DAPM_POST_PMU | SND_SOC_DAPM_PRE_PMD),
	SND_SOC_DAPM_OUTPUT("OUT"),
	SND_SOC_DAPM_INPUT("IV"),
};

static const struct snd_soc_dapm_route sia91xx_routes[] = {
	{ "PA", NULL, "AIF Playback" },
	{ "OUT", NULL, "PA" },
	{ "AIF Capture", NULL, "IV" },
};'''
assert old in s
s = s.replace(old, new, 1)

# includes needed for GENMASK/FIELD_GET
old_inc = '#include <linux/delay.h>\n'
new_inc = '#include <linux/bitfield.h>\n#include <linux/bits.h>\n#include <linux/delay.h>\n'
assert old_inc in s
s = s.replace(old_inc, new_inc, 1)

# probe: pick the channel setup and leave the part idle
old_probe = '''	ret = sia91xx_read_chipid(sia);
	if (ret)
		return ret;

	return devm_snd_soc_register_component(sia->dev, &sia91xx_component,
					       &sia91xx_dai, 1);'''
new_probe = '''	ret = sia91xx_read_chipid(sia);
	if (ret)
		return ret;

	/*
	 * Which half of the I2S frame this part takes. The vendor carries it as
	 * si,channel_num in its own binding; on this board the two addresses are
	 * consecutive and in the same order as sipa.bin's blocks, so the address
	 * is enough and no new property has to be invented for it.
	 */
	channel = i2c->addr - SIA9187_FIRST_ADDR;
	if (channel >= ARRAY_SIZE(sia9187_setup))
		return dev_err_probe(sia->dev, -EINVAL,
				     "address %#x is not one of the two the sipa parameters describe\\n",
				     i2c->addr);
	sia->setup = &sia9187_setup[channel];

	return devm_snd_soc_register_component(sia->dev, &sia91xx_component,
					       &sia91xx_dai, 1);'''
assert old_probe in s
s = s.replace(old_probe, new_probe, 1)

old_decl = '''	struct sia91xx *sia;
	int ret;'''
new_decl = '''	unsigned int channel;
	struct sia91xx *sia;
	int ret;'''
assert old_decl in s
s = s.replace(old_decl, new_decl, 1)

old_id = '''#define SIA9187_ID_FIRST	0x5d80
#define SIA9187_ID_LAST		0x5d90'''
new_id = '''#define SIA9187_ID_FIRST	0x5d80
#define SIA9187_ID_LAST		0x5d90

/* zorn wires channel 0 to 0x6c and channel 1 to 0x6d. */
#define SIA9187_FIRST_ADDR	0x6c'''
assert old_id in s
s = s.replace(old_id, new_id, 1)

p.write_text(s)
print('wired up, now %d lines' % len(s.splitlines()))
