"""The 3D editor shows where you are, and playing a scene is one button away."""
import ast
from pathlib import Path

import numpy as np
import pytest

from frontengine.show.scene.math3d import world_matrices
from frontengine.show.scene.view3d import GRID_CELLS, clip_segment, grid_lines
from frontengine.utils.scene_format.scene_3d_document import make_3d_scene

ROOT = Path(__file__).resolve().parents[2]


def _view_projection(position, target):
    forward = np.asarray(target, float) - np.asarray(position, float)
    forward /= np.linalg.norm(forward)
    side = np.cross(forward, [0, 1, 0])
    side /= np.linalg.norm(side)
    up = np.cross(side, forward)
    view = np.eye(4)
    view[0, :3], view[1, :3], view[2, :3] = side, up, -forward
    view[:3, 3] = -view[:3, :3] @ np.asarray(position, float)
    near, far, focal = .1, 100., 2.4
    projection = np.array([[focal, 0, 0, 0], [0, focal, 0, 0],
                           [0, 0, (far + near) / (near - far), 2 * far * near / (near - far)], [0, 0, -1, 0]])
    return projection @ view


@pytest.mark.parametrize("position, flat_axis", [
    ((0, 6, 6), 1),        # looking down: the floor
    ((0, 0, 8), 2),        # level, from the front: the wall facing the camera
    ((8, 0, .01), 0),      # level, from the side
])
def test_the_grid_lies_on_the_plane_the_camera_faces(position, flat_axis):
    lines = list(grid_lines(_view_projection(position, (0, 0, 0))))
    assert len(lines) == 2 * (2 * GRID_CELLS + 1)
    assert all(start[flat_axis] == end[flat_axis] == 0 for start, end, _axis in lines)
    assert sum(1 for *_ends, axis in lines if axis) == 2


def test_a_grid_line_behind_the_camera_is_cut_or_dropped():
    assert clip_segment(np.array([0, 0, 0, -1.]), np.array([1, 0, 0, -2.])) is None
    start, end = clip_segment(np.array([0, 0, 0, 1.]), np.array([0, 4, 0, -1.]))
    assert start == (0, 0) and np.isfinite(end).all()
    assert clip_segment(np.array([1, 1, 0, 2.]), np.array([4, 0, 0, 2.])) == ((.5, .5), (2, 0))


def test_a_new_3d_scene_has_nothing_to_draw_yet():
    scene = make_3d_scene({})
    assert {entry["type"] for entry in scene.entries.values()} == {"CAMERA", "LIGHT"}
    assert world_matrices(scene.entries)


def test_the_scene_page_offers_play_and_stop(make_main_window, monkeypatch):
    page = make_main_window().scene_setting_ui
    assert page.play_button.objectName() == "primaryAction"
    started, stopped = [], []
    monkeypatch.setattr(page.scene_manager_ui, "_parse_scene_json", lambda: started.append(True))
    monkeypatch.setattr(page.actions, "stop_playback", lambda *_args: stopped.append(True) or True)
    page.play_button.click()
    page.stop_button.click()
    assert started == [True] and stopped == [True]


def test_every_setting_page_outside_the_main_window_gets_its_lifetime():
    """The 3D verifier built the scene page without one, so it failed before checking the editor."""
    missing = []
    for path in (ROOT / "frontengine").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id.endswith("SettingUI") \
                    and not any(keyword.arg == "lifetime" for keyword in node.keywords):
                missing.append(f"{path.name}:{node.lineno} {node.func.id}")
    assert missing == []
