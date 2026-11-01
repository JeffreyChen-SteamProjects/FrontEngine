"""Synthesise the pet home's ambient loops: day, night, rain and snow.

Run from the repository root (numpy only, deterministic)::

    py tools/ambient_sounds.py frontengine/show/pet_game/ambience

Each loop is 12 s of 22,050 Hz mono 16-bit PCM and joins its own start without a
click: the last second is cross-faded into the first. Everything is made from
seeded noise and sine partials, so no recorded material and no licence is involved.
Levels stay low (peaks around -12 dBFS) because these sit under whatever else is playing.
"""
from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

RATE = 22050
SECONDS = 12
FADE = RATE                        # one second cross-faded into the start
PEAK = 0.25


def _noise(rng: np.random.Generator, count: int) -> np.ndarray:
    return rng.standard_normal(count).astype(np.float64)


def _lowpass(signal: np.ndarray, strength: float) -> np.ndarray:
    """One-pole low-pass: strength near 1 keeps only the rumble."""
    out = np.empty_like(signal)
    value = 0.0
    for index, sample in enumerate(signal):
        value = strength * value + (1 - strength) * sample
        out[index] = value
    return out


def _envelope(count: int, attack: int, release: int) -> np.ndarray:
    shape = np.ones(count)
    shape[:attack] = np.linspace(0, 1, attack)
    shape[count - release:] = np.linspace(1, 0, release)
    return shape


def room_tone(rng: np.random.Generator, count: int) -> np.ndarray:
    tone = _lowpass(_noise(rng, count), 0.995)
    return tone / np.max(np.abs(tone)) * 0.15


def chirp(rng: np.random.Generator) -> np.ndarray:
    """A short two-note bird call: a rising sine with a fast vibrato."""
    length = int(RATE * rng.uniform(0.08, 0.16))
    time = np.arange(length) / RATE
    start, end = rng.uniform(2600, 3400), rng.uniform(3600, 4600)
    frequency = np.linspace(start, end, length) + 120 * np.sin(2 * np.pi * 38 * time)
    phase = 2 * np.pi * np.cumsum(frequency) / RATE
    return np.sin(phase) * _envelope(length, length // 5, length // 2) * 0.5


def cricket(rng: np.random.Generator) -> np.ndarray:
    """Three quick pulses of a 4.4 kHz tone."""
    pulse = int(RATE * 0.018)
    gap = int(RATE * 0.022)
    time = np.arange(pulse) / RATE
    one = np.sin(2 * np.pi * 4400 * time) * _envelope(pulse, pulse // 4, pulse // 3)
    sound = np.concatenate([np.concatenate([one, np.zeros(gap)]) for _ in range(3)])
    return sound * rng.uniform(0.18, 0.3)


def _scatter(rng: np.random.Generator, count: int, make, per_second: float) -> np.ndarray:
    out = np.zeros(count)
    for _ in range(int(per_second * count / RATE)):
        sound = make(rng)
        start = int(rng.integers(0, count - len(sound)))
        out[start:start + len(sound)] += sound
    return out


def day(rng: np.random.Generator, count: int) -> np.ndarray:
    return room_tone(rng, count) + _scatter(rng, count, chirp, 0.7)


def night(rng: np.random.Generator, count: int) -> np.ndarray:
    return room_tone(rng, count) * 0.7 + _scatter(rng, count, cricket, 2.5)


def rain(rng: np.random.Generator, count: int) -> np.ndarray:
    hiss = _noise(rng, count) - _lowpass(_noise(rng, count), 0.6)
    hiss = _lowpass(hiss, 0.55) * 0.12
    drops = _scatter(rng, count, lambda r: _noise(r, 160) * _envelope(160, 4, 150) * r.uniform(0.2, 0.5), 9)
    return hiss + _lowpass(drops, 0.3) + room_tone(rng, count) * 0.5


def snow(rng: np.random.Generator, count: int) -> np.ndarray:
    """Soft wind: slowly swelling low noise, quieter than rain."""
    wind = _lowpass(_noise(rng, count), 0.985)
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * np.arange(count) / count * 3)
    return wind / np.max(np.abs(wind)) * 0.22 * swell


LOOPS = {"day": (day, 11), "night": (night, 23), "rain": (rain, 37), "snow": (snow, 41)}


def seamless(make, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = make(rng, RATE * SECONDS + FADE)
    body = raw[:RATE * SECONDS].copy()
    tail = raw[RATE * SECONDS:]
    ramp = np.linspace(0, 1, FADE)
    body[:FADE] = body[:FADE] * ramp + tail * (1 - ramp)
    return body / np.max(np.abs(body)) * PEAK


def write(target: Path, samples: np.ndarray) -> None:
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    with wave.open(str(target), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(pcm.tobytes())


def main() -> None:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "ambience")
    output.mkdir(parents=True, exist_ok=True)
    for name, (make, seed) in LOOPS.items():
        write(output / f"{name}.wav", seamless(make, seed))
        print("wrote", output / f"{name}.wav")


if __name__ == "__main__":
    main()
