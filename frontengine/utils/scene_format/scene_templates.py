"""Self-contained scene templates and bounded fitting/resource diagnostics."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from frontengine.utils.scene_format.scene_document import ASSET_FIELDS
from frontengine.utils.scene_format.scene_editor_document import validate_geometry


@dataclass(frozen=True)
class SceneTemplate:
    """A stable local identity and translated editable TEXT layer layout."""

    identifier: str
    title_key: str
    description_key: str
    layout: tuple[tuple[str, int, int, int, int, int], ...]

    def entries(self, translate: Callable[[str], str]) -> dict:
        """Generate independent layers at a 1280×720 logical-pixel base size."""
        return {key: {'type': 'TEXT', 'text': translate(key), 'x': x, 'y': y,
                      'width': width, 'height': height, 'font_size': font,
                      'opacity': 100, 'alignment': 'Center', 'z': index,
                      'visible': True, 'locked': False}
                for index, (key, x, y, width, height, font) in enumerate(self.layout)}


BUILTIN_TEMPLATES = (
    SceneTemplate('work', 'template_work', 'template_work_description', (
        ('template_work_title', 40, 32, 380, 80, 36),
        ('template_work_notes', 40, 124, 380, 220, 22),
        ('template_work_reference', 940, 40, 300, 220, 22))),
    SceneTemplate('teaching', 'template_teaching', 'template_teaching_description', (
        ('template_teaching_title', 40, 28, 880, 80, 38),
        ('template_teaching_steps', 40, 520, 850, 160, 24),
        ('template_teaching_reference', 940, 160, 300, 380, 22))),
    SceneTemplate('focus', 'template_focus', 'template_focus_description', (
        ('template_focus_title', 390, 210, 500, 100, 48),
        ('template_focus_task', 340, 340, 600, 100, 28),
        ('template_focus_break', 440, 550, 400, 80, 20))),
)


def fit_template(entries: dict, size: tuple[int, int]) -> dict:
    """Scale an independent template proportionally within the target logical screen."""
    if len(size) != 2 or any(type(value) is not int or not 320 <= value <= 32768 for value in size):
        raise ValueError('Template screen dimensions must be between 320 and 32768')
    result = deepcopy(validate_geometry(entries))
    scale = min(size[0] / 1280, size[1] / 720, 6)
    offset = ((size[0] - 1280 * scale) / 2, (size[1] - 720 * scale) / 2)
    for entry in result.values():
        entry['x'] = entry.get('x', 0) * scale + offset[0]
        entry['y'] = entry.get('y', 0) * scale + offset[1]
        entry['width'] = max(16, min(8192, entry.get('width', 320) * scale))
        entry['height'] = max(16, min(8192, entry.get('height', 180) * scale))
        if 'font_size' in entry:
            entry['font_size'] = max(6, min(200, round(entry['font_size'] * scale)))
    return validate_geometry(result)


def missing_template_assets(entries: dict) -> list[str]:
    """List layer/field/path failures before replacing editor or playback."""
    missing = []
    for key, entry in validate_geometry(entries).items():
        for field in ASSET_FIELDS:
            value = entry.get(field)
            if value and not Path(value).is_file():
                missing.append(f'{key} / {field}: {value}')
    return missing
