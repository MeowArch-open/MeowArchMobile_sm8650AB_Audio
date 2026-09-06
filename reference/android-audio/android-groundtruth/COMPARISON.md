# Android (working) vs Linux (silent): the two SIA9187s side by side

Collected 2026-09-06 over adb with root, `Sipa Power = On`, `Sipa Mute = Off`,
media volume 1%. Linux column is `work/tmp/android-audio/sipa/linux-0-006*.txt`,
taken mid-`aplay` with both parts at state 5.

## Every register the vendor writes is already identical

    12: 9d60   13: 0384   14: a3c8   15: 0a0a (L) / 0b0b (R)   16: 101b   17: 0418
    18: 1ab3   19: 3e28   1a: 6c00   1b: 83ee   1c: 8b40   1d: ee80   1e: 8000
    20: 8122   23: 0288   24: 4800   25: 0800   26: 4000   27: 0004   28: 2408
    29: 6000   2a: 9664   2b: 910a (L) / 90f0 (R)   2c: 0014   2d: 12fc   2e: c4bf
    31: 000b   50..55 trim   72: 0008   74: ffff   75: 03e0   77: 100c

Byte for byte the same on both systems -- so the reversing of `sipa.bin` and the
power-on sequence is right, and `/odm/firmware/sipa.bin` md5 `8dac7639...` is the
same file we decoded.

## The whole difference is in the status registers 0x00-0x0a

| reg | Linux off | Linux on (silent) | **Android on (working)** |
|-----|-----------|-------------------|--------------------------|
| 0x00 | 0002 | 0182 | **0502** |
| 0x01 | 40a0 | 8605 | **8415** |
| 0x02 | 0074 | 007c | **006c** |
| 0x03 | 0000 | 0026 | **0000** |
| 0x04 | 0000 | 014e | **0000** |
| 0x05 | 0000 | 031d | **0000** |
| 0x08 | 0000 | 0080 | **0000** |
| 0x0a | 0080 | 0080 | **0000** |
| 0x13 | 0381 | 0384 | 0384 |

`0x01`'s low nibble is 5 on both, so "on" is reached either way. What differs:

* **`0x02` bit 4 (0x10) is set on ours and clear on Android.** The module's flag
  table names bits 0x04 PORI, 0x08 NOCLK, 0x20 OTPI, 0x40 UVPI, 0x80 OCPI and
  leaves 0x02 and 0x10 unnamed -- and the one remaining name in that table is
  **TDMERR**. A framing error is exactly what our symptoms are.
* **`0x08` and `0x0a` bit 7 set on ours, clear on Android.**
* **`0x03` / `0x04` / `0x05` non-zero on ours, zero on Android.**

**This reverses an earlier reading.** Those three registers coming alive was taken
as evidence the part was running; the working system has them at zero, so they are
diagnostics, not activity.

## And it gives an objective criterion at last

Target state, no ears required:

    02 == 006c   (bit 4 clear)      03 == 0000
    08 == 0000                      04 == 0000
    0a == 0000                      05 == 0000

## The vendor's link parameters, from its own driver's log

    sia91xx_hw_params: dai:sia91xx-aif-9-6c  i2s rate: 48000
    sia91xx_hw_params: i2s channel: 2
    sia91xx_hw_params: i2s width: 32
    sia91xx_hw_params: stream = 0, requested rate = 48000, sample size = 32,
                       physical size = 32, channel num = 2
    smartpa_dai_link_select dailink:TDM-LPAIF-RX-SECONDARY
                            codec_name: sipa.9-006c codec_dai: sia91xx-aif-9-6c

**Two channels at 32-bit, 48 kHz.** So the four-slot TDM theory was wrong: the
link Qualcomm calls TDM-SECONDARY runs a plain 64-bit stereo frame. That is a
shape AudioReach's I2S sink can produce -- `mi2s_width=32` on our side.

## GPIOs: ours already match

    gpio70  : out high    spksw (left amp only; sipa_property_init: spksw_gpio = 371)
    gpio85  : out low     right amp reset -- and UNCLAIMED by the vendor driver
    gpio111 : out low     left amp reset, claimed by sipa.9-006c

    pin 121 i2s1_sck   pin 122 i2s1_data0   pin 123 i2s1_ws   pin 124 i2s1_data1
    all owned by soc:spf_core_platform:sec_tdm_pinctrl

Identical to what our driver and DT do, including spksw high and both resets low.

## Next step

On Arch: `mi2s_width=32`, play, and read 0x02/0x03/0x04/0x05/0x08/0x0a. If they
go to the Android values the frame is right; if only some clear, the remaining
bits say what is still wrong. Either way it is measurable now.
