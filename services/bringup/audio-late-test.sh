#!/bin/bash
# Run after a boot with /etc/modprobe.d/zorn-audio-late.conf in place.
# Loads the AudioReach stack by hand, long after pd-mapper is up, and reports
# whether the APM answers.
set -u

echo "=== pd-mapper ==="
systemctl is-active zorn-pd-mapper
journalctl -b -o short-monotonic -u zorn-pd-mapper --no-pager 2>/dev/null | head -2

echo "=== before: no q6apm ==="
lsmod | grep -c snd_q6apm
cat /proc/asound/cards

echo "=== loading snd_q6apm ($(date +%T)) ==="
dmesg -C
modprobe snd_q6apm
sleep 8
modprobe snd_q6apm_dai 2>/dev/null || true
modprobe q6apm_lpass_dais 2>/dev/null || true
sleep 6

echo "=== dmesg ==="
dmesg | grep -iE "apm|gpr|tplg|sndcard|instantiate|graph|spf" | head -25

echo "=== did the timeout happen? ==="
if dmesg | grep -q "CMD timeout"; then
	echo "STILL TIMING OUT -- pd-mapper ordering is not the cause"
	dmesg | grep "CMD timeout" | head -3
else
	echo "NO TIMEOUT -- the boot race was the cause"
fi

echo "=== card ==="
cat /proc/asound/cards
