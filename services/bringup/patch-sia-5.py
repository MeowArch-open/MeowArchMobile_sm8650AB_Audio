#!/usr/bin/env python3
import sys, pathlib
p = pathlib.Path('/run/media/xingguangcuican/Project/testa/linux/sound/soc/codecs/sia91xx.c')
s = p.read_text()
if 'sia91xx_dai_prepare' in s:
    print('already patched'); sys.exit(0)

# --- power_on becomes idempotent and retries, because the part only latches
#     "on" when the I2S clock is already running.
old = '''static int sia91xx_power_on(struct sia91xx *sia)
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
}'''
new = '''/* One pass of the vendor's chip-on list, then wait for the part to latch. */
static int sia91xx_try_on(struct sia91xx *sia)
{
	unsigned int state, discard;
	int ret, i;

	ret = sia91xx_state(sia, &state);
	if (ret)
		return ret;

	/*
	 * The list starts by verifying the part is idle. If it is anywhere else
	 * -- including stuck at 1, which is where it lands when the enable was
	 * written before the I2S clock was running -- put it back first.
	 */
	if (state != SIA91XX_STATE_IDLE) {
		ret = regmap_write(sia->regmap, SIA91XX_REG_ENABLE,
				   SIA9187_DISABLE);
		if (ret)
			return ret;
		usleep_range(1000, 2000);
	}

	ret = sia91xx_write_seq(sia, sia->setup->defaults,
				sia->setup->num_defaults);
	if (ret)
		return ret;

	usleep_range(1000, 2000);

	/* The vendor's list reads 0x08 here and throws the value away. */
	ret = regmap_read(sia->regmap, 0x08, &discard);
	if (ret)
		return ret;

	ret = sia91xx_write_seq(sia, sia->setup->power_on,
				sia->setup->num_power_on);
	if (ret)
		return ret;

	for (i = 0; i < 20; i++) {
		usleep_range(1000, 2000);

		ret = sia91xx_state(sia, &state);
		if (ret)
			return ret;

		if (state == SIA91XX_STATE_ON)
			return 0;
	}

	dev_dbg(sia->dev, "did not latch on: state %#x\\n", state);

	return -EAGAIN;
}

/*
 * sipa_resume(): the defaults for the scene, then the chip-on list.
 *
 * The part reaches its "on" state (0x01 low nibble 5) only if the I2S bit clock
 * is already running when the enable is written; without one it sits at 1 and
 * stays there, enabled but silent. Nothing in ASoC guarantees the ADSP has the
 * port up at DAPM time -- PipeWire holds the PCM open across suspends, so the
 * widget powers up once, long before the graph starts -- which is why this is
 * driven from the DAI's prepare and is idempotent and retried rather than done
 * once and trusted.
 */
static int sia91xx_power_on(struct sia91xx *sia)
{
	unsigned int state;
	int ret, attempt;

	ret = sia91xx_state(sia, &state);
	if (ret)
		return ret;

	if (state == SIA91XX_STATE_ON)
		return 0;

	ret = sia91xx_read_chipid(sia);
	if (ret)
		return ret;

	for (attempt = 0; attempt < 3; attempt++) {
		ret = sia91xx_try_on(sia);
		if (ret != -EAGAIN)
			return ret;
	}

	dev_err(sia->dev, "did not come on after %d attempts\\n", attempt);

	return -EIO;
}'''
assert old in s
s = s.replace(old, new, 1)
p.write_text(s)
print('power_on reworked, %d lines' % len(s.splitlines()))
