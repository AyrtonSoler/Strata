"""Ambient pad + soft pluck arpeggio in D, synthesized from scratch (no samples)."""
import sys, wave
import numpy as np
SR = 44100
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
n = int(SR * dur)
t = np.arange(n) / SR
f = lambda m: 440.0 * 2 ** ((m - 69) / 12)
CH = [[50, 57, 66, 73], [47, 54, 62, 69], [43, 50, 59, 66], [45, 52, 59, 64]]  # Dmaj7 Bm7 Gmaj7 Asus2
L = 3.75
out = np.zeros(n)
for k in range(int(dur / L) + 2):
    st, notes = k * L - 0.6, CH[k % 4]
    a, b = max(0, int(st * SR)), min(n, int((st + L + 1.6) * SR))
    if a >= b: continue
    tt = t[a:b] - st
    env = np.clip(tt / 1.2, 0, 1) * np.clip((L + 1.6 - tt) / 1.4, 0, 1)
    for m in notes:
        for det in (-0.12, 0.12):
            ph = 2 * np.pi * f(m) * (1 + det / 100) * tt
            out[a:b] += env * (np.sin(ph) + 0.18 * np.sin(2 * ph)) * 0.05
# pluck arpeggio, 8th notes at 96 bpm
step = 60 / 96 / 2
for i in range(int(dur / step)):
    st = i * step
    notes = CH[int(st // L) % 4]
    m = notes[[0, 2, 1, 3, 2, 3, 1, 2][i % 8]] + 12
    a = int(st * SR); b = min(n, a + int(1.2 * SR))
    tt = t[a:b] - st
    out[a:b] += np.exp(-tt * 5) * np.sin(2 * np.pi * f(m) * tt) * 0.035 * (1 if i % 2 == 0 else 0.6)
# cheap reverb: decaying noise impulse
ir_t = np.arange(int(1.8 * SR)) / SR
rng = np.random.default_rng(7)
ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.2)
wet = np.fft.irfft(np.fft.rfft(out, 2 * n) * np.fft.rfft(ir, 2 * n))[:n]
mix = 0.75 * out + 0.35 * wet / (np.abs(wet).max() + 1e-9) * np.abs(out).max()
fade = np.clip(t / 1.5, 0, 1) * np.clip((dur - t) / 2.5, 0, 1)
mix *= fade
mix = mix / (np.abs(mix).max() + 1e-9) * 0.8
pcm = (np.stack([mix, np.roll(mix, 300)], 1) * 32767).astype(np.int16)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("music", dur)
