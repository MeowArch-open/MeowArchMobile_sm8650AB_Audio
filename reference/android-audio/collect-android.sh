#!/system/bin/sh
# zorn audio ground-truth collection, to be run ON ANDROID as root.
#
# Run it WHILE SOUND IS PLAYING OUT OF THE LOUDSPEAKERS (any volume -- 1% is
# fine, the registers and logs are identical). Not headphones, not Bluetooth.
#
#   adb push collect-android.sh /data/local/tmp/
#   adb shell
#   su
#   sh /data/local/tmp/collect-android.sh
#
# Everything lands in /data/local/tmp/zorn-info/ and is tarred up at the end.

OUT=/data/local/tmp/zorn-info
rm -rf $OUT; mkdir -p $OUT
have() { command -v "$1" >/dev/null 2>&1; }
mount -t debugfs none /sys/kernel/debug 2>/dev/null

say() { echo "== $* =="; }

# ---------------------------------------------------------------- 1. the logs
# sia91xx_hw_params prints the link's rate / channels / width, and
# sia91xx_set_fmt prints the DAI format. This is the single most useful thing
# here: it says exactly what frame the vendor drives the amplifiers with.
say "1/8 kernel log (sipa)"
dmesg 2>/dev/null | grep -iE 'sipa|sia91|si_pa' > $OUT/dmesg-sipa.txt
cat /proc/kmsg 2>/dev/null | head -0
wc -l < $OUT/dmesg-sipa.txt
grep -iE 'i2s rate|i2s channel|i2s width|fmt = ' $OUT/dmesg-sipa.txt | tail -20

# ------------------------------------------------------------ 2. amp registers
say "2/8 amplifier registers (while playing)"
for d in /sys/kernel/debug/regmap/*006c /sys/kernel/debug/regmap/*006d; do
	[ -e "$d/registers" ] || continue
	n=$(basename "$d")
	cat "$d/registers" > $OUT/regmap-$n.txt 2>/dev/null
	echo "  $n: $(wc -l < $OUT/regmap-$n.txt) registers"
done
ls -d /sys/bus/i2c/devices/*006c /sys/bus/i2c/devices/*006d > $OUT/i2c-devices.txt 2>/dev/null

# ------------------------------------------------------------- 3. mixer state
say "3/8 mixer state"
if have tinymix; then
	tinymix > $OUT/tinymix-all.txt 2>/dev/null || tinymix contents > $OUT/tinymix-all.txt 2>/dev/null
	grep -iE 'sipa|spkr' $OUT/tinymix-all.txt
else
	echo "  no tinymix"
fi

# -------------------------------------------------------------- 4. gpio state
# si_pa_reset is tlmm 111 (left) / 85 (right); spksw-gpio is tlmm 70. Their
# levels while the speakers actually work settle what our driver should do.
say "4/8 gpio state"
cat /sys/kernel/debug/gpio > $OUT/gpio.txt 2>/dev/null
grep -nE 'gpio-(70|85|111)\b|\b(70|85|111)\b' $OUT/gpio.txt 2>/dev/null | head -20
cat /sys/kernel/debug/pinctrl/*/pinmux-pins > $OUT/pinmux-pins.txt 2>/dev/null
grep -E 'pin (70|85|111|121|122|123|124) ' $OUT/pinmux-pins.txt 2>/dev/null

# ------------------------------------------------------- 5. which link is live
say "5/8 pcm / backend in use"
cat /proc/asound/pcm > $OUT/asound-pcm.txt 2>/dev/null
for s in /proc/asound/card0/pcm*/sub0/status; do
	st=$(head -1 "$s" 2>/dev/null)
	[ "$st" = "closed" ] && continue
	echo "  $s: $st"
	cat "$s" >> $OUT/pcm-status.txt 2>/dev/null
	echo "--- $s" >> $OUT/pcm-status.txt
done
for h in /proc/asound/card0/pcm*/sub0/hw_params; do
	hp=$(head -1 "$h" 2>/dev/null)
	[ -z "$hp" ] || [ "$hp" = "closed" ] && continue
	echo "  $h"; cat "$h" | sed 's/^/     /'
	{ echo "--- $h"; cat "$h"; } >> $OUT/pcm-hwparams.txt 2>/dev/null
done

# ----------------------------------------------------------- 6. vendor configs
say "6/8 vendor mixer/platform configs present"
ls -l /vendor/etc/mixer_paths*.xml /vendor/etc/audio*.xml /vendor/etc/resourcemanager*.xml \
      /odm/etc/mixer_paths*.xml 2>/dev/null | tee $OUT/vendor-xml-list.txt
for f in /vendor/etc/mixer_paths*.xml /odm/etc/mixer_paths*.xml; do
	[ -f "$f" ] && cp "$f" $OUT/ 2>/dev/null
done
cp /vendor/etc/resourcemanager*.xml $OUT/ 2>/dev/null

# --------------------------------------------------------------- 7. the mic
# Same question for the microphone: which macro, which DMIC, what clock.
say "7/8 dmic / mic state"
if have tinymix; then
	grep -iE 'dmic|dec[0-7]|va |tx ' $OUT/tinymix-all.txt | head -40 > $OUT/tinymix-mic.txt
	head -20 $OUT/tinymix-mic.txt
fi
for n in /proc/device-tree/soc*/*/qcom,*dmic-sample-rate; do
	[ -e "$n" ] && { echo -n "  $n = "; od -An -tu4 --endian=big "$n" 2>/dev/null; }
done
cat /sys/kernel/debug/pinctrl/*lpi*/pinmux-pins > $OUT/lpi-pinmux.txt 2>/dev/null

# --------------------------------------------------------------- 8. wrap up
say "8/8 packing"
cp /proc/asound/cards $OUT/ 2>/dev/null
getprop | grep -iE 'audio|sipa|speaker' > $OUT/getprop-audio.txt 2>/dev/null
cd /data/local/tmp && tar czf zorn-info.tar.gz zorn-info 2>/dev/null
ls -l /data/local/tmp/zorn-info.tar.gz
echo
echo "done -- pull it with:"
echo "  adb pull /data/local/tmp/zorn-info.tar.gz"
