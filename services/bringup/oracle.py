#!/usr/bin/env python3
"""Goertzel tone detector: how much energy is there at a given frequency?

The phone's own microphone is a few centimetres from its speakers, so if the
amplifiers make any sound at all this cannot miss it. Pure python, no numpy.
"""
import math, struct, sys, wave


def goertzel(samples, rate, freq):
    w = 2 * math.pi * freq / rate
    coeff = 2 * math.cos(w)
    s1 = s2 = 0.0
    for x in samples:
        s0 = x + coeff * s1 - s2
        s2, s1 = s1, s0
    power = s1 * s1 + s2 * s2 - coeff * s1 * s2
    return math.sqrt(max(power, 0.0)) / max(len(samples), 1)


def main():
    path, freq = sys.argv[1], float(sys.argv[2])
    w = wave.open(path, 'rb')
    rate, ch = w.getframerate(), w.getnchannels()
    d = w.readframes(w.getnframes())
    s = struct.unpack('<%dh' % (len(d) // 2), d)
    left = list(s[0::ch])
    if not left:
        print('no samples')
        return
    tone = goertzel(left, rate, freq)
    # a couple of off-target bins as a noise floor
    floor = sum(goertzel(left, rate, f) for f in (freq * 0.55, freq * 1.7, freq * 2.9)) / 3
    rms = math.sqrt(sum(float(x) * x for x in left) / len(left))
    ratio = tone / floor if floor > 1e-9 else float('inf')
    print('tone@%.0f=%.2f floor=%.2f ratio=%.1f rms=%.1f' % (freq, tone, floor, ratio, rms))


if __name__ == '__main__':
    main()
