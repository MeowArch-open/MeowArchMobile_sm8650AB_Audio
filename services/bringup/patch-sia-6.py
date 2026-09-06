#!/usr/bin/env python3
import sys, pathlib
p = pathlib.Path('/run/media/xingguangcuican/Project/testa/linux/sound/soc/codecs/sia91xx.c')
s = p.read_text()
if 'sia91xx_dai_prepare' in s:
    print('already patched'); sys.exit(0)

# 1. a DAI prepare that runs after the cpu DAI has started the ADSP graph
old_ev = '''static int sia91xx_pa_event(struct snd_soc_dapm_widget *w,'''
new_ev = '''/*
 * For a DPCM backend, snd_soc_pcm_dai_prepare() walks the cpu DAI before the
 * codec DAIs, so by the time this runs q6apm has already started the graph and
 * the LPASS port is clocking. That is the earliest point at which the enable
 * write can actually latch, and ALSA calls it again on every resume from
 * suspend, which is exactly when a PipeWire sink comes back.
 */
static int sia91xx_dai_prepare(struct snd_pcm_substream *substream,
			       struct snd_soc_dai *dai)
{
	struct sia91xx *sia = dev_get_drvdata(dai->dev);

	if (substream->stream != SNDRV_PCM_STREAM_PLAYBACK)
		return 0;

	return sia91xx_power_on(sia);
}

static const struct snd_soc_dai_ops sia91xx_dai_ops = {
	.prepare = sia91xx_dai_prepare,
};

static int sia91xx_pa_event(struct snd_soc_dapm_widget *w,'''
assert old_ev in s
s = s.replace(old_ev, new_ev, 1)

# 2. the PA widget stops powering on -- only the teardown stays there
old_pa = '''	switch (event) {
	case SND_SOC_DAPM_POST_PMU:
		return sia91xx_power_on(sia);
	case SND_SOC_DAPM_PRE_PMD:
		return sia91xx_power_off(sia);
	}'''
new_pa = '''	switch (event) {
	case SND_SOC_DAPM_POST_PMU:
		/*
		 * Try here too: on a plain aplay the clock is already up by now,
		 * so the part comes on before the first sample. If it does not,
		 * the DAI prepare above picks it up.
		 */
		sia91xx_power_on(sia);
		return 0;
	case SND_SOC_DAPM_PRE_PMD:
		return sia91xx_power_off(sia);
	}'''
assert old_pa in s
s = s.replace(old_pa, new_pa, 1)

# 3. hook the ops onto the DAI
old_dai = '''static struct snd_soc_dai_driver sia91xx_dai = {
	.name = "sia91xx-aif",
	.id = 1,'''
new_dai = '''static struct snd_soc_dai_driver sia91xx_dai = {
	.name = "sia91xx-aif",
	.id = 1,
	.ops = &sia91xx_dai_ops,'''
assert old_dai in s
s = s.replace(old_dai, new_dai, 1)
p.write_text(s)
print('dai prepare wired, %d lines' % len(s.splitlines()))
