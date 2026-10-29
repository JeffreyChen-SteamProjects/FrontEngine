"""Bounded per-layer position/opacity keyframes preserved in scene v1."""
from __future__ import annotations

from copy import deepcopy
import math

CHANNELS = ('x', 'y', 'opacity')
MAX_KEYFRAMES = 128
MAX_ANIMATION_SECONDS = 3600


def validate_animation(value: object) -> list[dict]:
    """Reject ambiguous times, unknown channels and nonfinite external values."""
    if not isinstance(value, list) or len(value) > MAX_KEYFRAMES:
        raise ValueError('Animation must contain at most 128 keyframes')
    previous = -1
    for frame in value:
        if not isinstance(frame, dict) or set(frame) - {'time', 'easing', *CHANNELS}:
            raise ValueError('Animation keyframe has unsupported fields')
        if not any(channel in frame for channel in CHANNELS):
            raise ValueError('Animation keyframe needs a position or opacity')
        stamp = frame.get('time')
        if type(stamp) not in (int, float) or not math.isfinite(stamp) or not 0 <= stamp <= MAX_ANIMATION_SECONDS:
            raise ValueError('Animation time must be finite and within 0–3600 seconds')
        if stamp <= previous:
            raise ValueError('Animation times must be unique and increasing')
        previous = stamp
        if frame.get('easing', 'linear') not in ('linear', 'smooth'):
            raise ValueError('Animation easing must be linear or smooth')
        for channel in CHANNELS:
            if channel not in frame:
                continue
            number = frame[channel]
            if type(number) not in (int, float) or not math.isfinite(number):
                raise ValueError('Animation values must be finite numbers')
            low, high = (0, 100) if channel == 'opacity' else (-100000, 100000)
            if not low <= number <= high:
                raise ValueError(f'Animation {channel} is outside its supported range')
    return deepcopy(value)


def base_values(entry: dict) -> dict:
    """Match legacy playback defaults for nonanimated geometry."""
    return {'x': entry.get('x', 0), 'y': entry.get('y', 0),
            'opacity': entry.get('opacity', 100 if entry.get('type') == 'PUPPET' else 20)}


def sample_animation(entry: dict, seconds: float | None) -> dict:
    """Interpolate independent channels, holding the last specified value."""
    values = base_values(entry)
    if seconds is None:
        return values
    for channel in CHANNELS:
        points = [(0, values[channel], 'linear')]
        for frame in entry.get('animation', []):
            if channel in frame:
                point = (frame['time'], frame[channel], frame.get('easing', 'linear'))
                if point[0] == 0:
                    points[0] = point
                else:
                    points.append(point)
        values[channel] = points[-1][1]
        for left, right in zip(points, points[1:]):
            if seconds <= right[0]:
                ratio = max(0, min(1, (seconds - left[0]) / (right[0] - left[0])))
                if right[2] == 'smooth':
                    ratio = ratio * ratio * (3 - 2 * ratio)
                values[channel] = left[1] + (right[1] - left[1]) * ratio
                break
    return values


def animation_duration(entries: dict) -> float:
    """Return the longest validated track; old scenes have zero duration."""
    return max((entry['animation'][-1]['time'] for entry in entries.values()
                if entry.get('animation')), default=0)
