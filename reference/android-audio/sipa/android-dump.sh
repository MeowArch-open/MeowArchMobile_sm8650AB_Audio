#!/system/bin/sh
# Run this ON ANDROID, as root, WITH SOUND PLAYING OUT OF THE LOUDSPEAKERS
# (not headphones, not Bluetooth). It dumps both SIA9187s' full register state.
mount -t debugfs none /sys/kernel/debug 2>/dev/null
echo "=== which bus ==="
ls -d /sys/bus/i2c/devices/*-006c /sys/bus/i2c/devices/*-006d 2>/dev/null
echo "=== sipa mixer state ==="
tinymix 2>/dev/null | grep -i sipa
echo "=== regmap dumps ==="
for d in /sys/kernel/debug/regmap/*-006c /sys/kernel/debug/regmap/*-006d; do
	[ -e "$d/registers" ] || continue
	echo "--- $d"
	cat "$d/registers"
done
