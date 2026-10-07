"""Measure static and changing software composition with a trusted baseline module."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import random
import statistics
import sys
from pathlib import Path
from time import perf_counter_ns

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QColor, QTransform
from PySide6.QtWidgets import QApplication
from frontengine.show.compositor import Layer, CompositorWidget


def fixture() -> list[Layer]:
    """Seeded fixed twelve-layer 1280x720 scene shared by both implementations."""
    rng = random.Random(20261008)
    layers = []
    for index in range(12):
        image = QImage(320, 180, QImage.Format.Format_RGBA8888_Premultiplied)
        image.fill(QColor(rng.randrange(256), rng.randrange(256), rng.randrange(256), 210))
        layers.append(Layer(str(index), image, QTransform.fromTranslate((index % 4) * 250,
                                                                      (index // 4) * 200), index, .8))
    return layers


def measure(factory, changing: bool, iterations: int) -> dict:
    """Warm up before seven rounds; retain returned frames only for exact final equality."""
    widget, layers = factory(backend='software'), fixture()
    widget.resize(QSize(1280, 720))
    samples = []
    try:
        for index in range(20 + iterations * 7):
            if changing:
                layers[0].image.fill(QColor(index % 256, 80, 130, 210))
            start = perf_counter_ns()
            widget.set_layers(layers)
            frame = widget.output_frame()
            elapsed = perf_counter_ns() - start
            if index >= 20:
                samples.append(elapsed / 1_000_000)
        return {'median_ms': statistics.median(samples), 'p95_ms': sorted(samples)[int(len(samples) * .95)],
                'frames': len(samples), 'physical_size': [frame.width(), frame.height()],
                'sha256': hashlib.sha256(frame.constBits()).hexdigest()}
    finally:
        widget.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-file', type=Path, help='Trusted git-exported compositor/widget.py')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--iterations', type=int, default=80)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 1000:
        parser.error('iterations must be 1..1000')
    application = QApplication.instance() or QApplication([])
    factories = {'current': CompositorWidget}
    if args.baseline_file:
        spec = importlib.util.spec_from_file_location('frontengine.show.compositor._benchmark_baseline',
                                                     args.baseline_file.resolve())
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        factories['baseline'] = module.CompositorWidget
    result = {'python': sys.version.split()[0], 'os': platform.platform(), 'qt_platform': application.platformName(),
              'screen_dpr': application.primaryScreen().devicePixelRatio(), 'logical_size': [1280, 720],
              'layer_count': 12, 'seed': 20261008, 'backend': 'software', 'measurements': {}}
    for mode in ('static', 'changing'):
        result['measurements'][mode] = {name: measure(factory, mode == 'changing', args.iterations)
                                        for name, factory in factories.items()}
        values = result['measurements'][mode]
        if 'baseline' in values:
            assert values['current']['sha256'] == values['baseline']['sha256'], 'Pixel outputs differ'
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
