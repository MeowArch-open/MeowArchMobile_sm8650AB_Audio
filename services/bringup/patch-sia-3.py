#!/usr/bin/env python3
import sys, pathlib
p = pathlib.Path('/run/media/xingguangcuican/Project/testa/linux/sound/soc/codecs/sia91xx.c')
s = p.read_text()
if 'sia91xx_power_on' in s:
    print('already patched'); sys.exit(0)

anchor = """/*
 * Playback and capture both carry the amplifier's own numbers"""
assert anchor in s

power = '''static int sia91xx_write_seq(struct sia91xx *sia, const struct sia91xx_reg *seq,
			    unsigned int count)
{
	unsigned int i;
	int ret;

	for (i = 0; i < count; i++) {
		ret = regmap_write(sia->regmap, seq[i].reg, seq[i].val);
		if (ret) {
			dev_err(sia->dev, "cannot write %#04x = %#06x: %d\\n",
				seq[i].reg, seq[i].val, ret);
			return ret;
		}
	}

	return 0;
}

static int sia91xx_state(struct sia91xx *sia, unsigned int *state)
{
	unsigned int val;
	int ret;

	ret = regmap_read(sia->regmap, SIA91XX_REG_STATE, &val);
	if (ret) {
		dev_err(sia->dev, "cannot read the state register: %d\\n", ret);
		return ret;
	}

	*state = FIELD_GET(SIA91XX_STATE, val);

	return 0;
}

/*
 * sipa_resume(): the defaults for the scene, a re-read of the identity register,
 * then the chip-on list. The vendor checks the state field first and gives up if
 * the part is not idle, so this does too -- writing the enable to a part that is
 * already running is not something the sequence was ever asked to do.
 */
static int sia91xx_power_on(struct sia91xx *sia)
{
	unsigned int state, discard;
	int ret;

	ret = sia91xx_write_seq(sia, sia->setup->defaults,
				sia->setup->num_defaults);
	if (ret)
		return ret;

	usleep_range(1000, 2000);

	ret = sia91xx_read_chipid(sia);
	if (ret)
		return ret;

	ret = sia91xx_state(sia, &state);
	if (ret)
		return ret;

	if (state != SIA91XX_STATE_IDLE) {
		dev_err(sia->dev, "not idle before power-on: state %#x\\n", state);
		return -EBUSY;
	}

	/* The vendor's list reads 0x08 here and throws the value away. */
	ret = regmap_read(sia->regmap, 0x08, &discard);
	if (ret)
		return ret;

	ret = sia91xx_write_seq(sia, sia->setup->power_on,
				sia->setup->num_power_on);
	if (ret)
		return ret;

	ret = sia91xx_state(sia, &state);
	if (ret)
		return ret;

	if (state != SIA91XX_STATE_ON) {
		dev_err(sia->dev, "did not come on: state %#x\\n", state);
		return -EIO;
	}

	return 0;
}

/* sipa_suspend(): clear the enable bit, then the 1 ms the vendor list carries. */
static int sia91xx_power_off(struct sia91xx *sia)
{
	unsigned int state;
	int ret;

	ret = sia91xx_state(sia, &state);
	if (ret)
		return ret;

	if (state != SIA91XX_STATE_ON)
		dev_warn(sia->dev, "not on before power-off: state %#x\\n", state);

	ret = regmap_write(sia->regmap, SIA91XX_REG_ENABLE, SIA9187_DISABLE);
	if (ret) {
		dev_err(sia->dev, "cannot clear the enable: %d\\n", ret);
		return ret;
	}

	usleep_range(1000, 2000);

	return 0;
}

static int sia91xx_pa_event(struct snd_soc_dapm_widget *w,
			    struct snd_kcontrol *kcontrol, int event)
{
	struct snd_soc_component *component = snd_soc_dapm_to_component(w->dapm);
	struct sia91xx *sia = dev_get_drvdata(component->dev);

	switch (event) {
	case SND_SOC_DAPM_POST_PMU:
		return sia91xx_power_on(sia);
	case SND_SOC_DAPM_PRE_PMD:
		return sia91xx_power_off(sia);
	}

	return 0;
}

'''
s = s.replace(anchor, power + anchor, 1)
p.write_text(s)
print('power helpers inserted, now %d lines' % len(s.splitlines()))
