"""Puppet pets drawn as themselves in the home, behind the layered renderer's interface.

A Puppet pet brings a still portrait (its rig cannot run in the home). The home's actions are
made up from it the same way a layered pet's are played, so the home never needs to know which
kind it is drawing: an action without frames uses idle, and a single still frame bounces while
walking, hops while playing and settles down while sleeping.

Loading reads files and decodes images, so it runs on a worker thread; ``render`` only
paints already decoded frames.
"""
from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QImage, QImageReader, QPainter

MAX_FRAMES = 96                  # per action: long GIFs are cut, not refused
MAX_HEIGHT = 256                 # frames are scaled down to this; the home draws them about 70 px tall
DEFAULT_DELAY_MS = 100
HEADROOM = 1.15                  # room above the picture for a hop
# Home actions with no frames of their own borrow one of these, then idle.
BORROW = {"sit": "idle", "feed": "idle", "greet": "idle", "play": "walk", "write": "idle", "garden": "idle",
          "craft": "idle"}


def read_frames(path: Path) -> list[tuple[QImage, int]]:
    """Every frame (up to MAX_FRAMES) with its delay, scaled down to MAX_HEIGHT; [] when unreadable."""
    reader = QImageReader(str(path))
    frames: list[tuple[QImage, int]] = []
    while len(frames) < MAX_FRAMES:
        image = reader.read()
        if image.isNull():
            break
        if image.height() > MAX_HEIGHT:
            image = image.scaledToHeight(MAX_HEIGHT, Qt.TransformationMode.SmoothTransformation)
        delay = reader.nextImageDelay()
        frames.append((image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied),
                       delay if delay > 0 else DEFAULT_DELAY_MS))
        if not reader.supportsAnimation() or reader.imageCount() == 1:
            break
    return frames


def load_picture(kind: str, path: Path, identifier: str) -> PictureRenderer:
    """A renderer for a Puppet portrait; ValueError for any other kind or when nothing loads."""
    if kind != "portrait":
        raise ValueError(f"Not a pet look the home can draw: {kind}")
    actions = {"idle": read_frames(path)}
    actions = {state: frames for state, frames in actions.items() if frames}
    if not actions:
        raise ValueError(f"No readable picture for this pet: {path.name}")
    return PictureRenderer(actions, identifier)


class PictureRenderer:
    """Same calls as the layered renderer: ``character.canvas``, ``has_action`` and ``render``."""

    def __init__(self, actions: dict[str, list[tuple[QImage, int]]], identifier: str = "") -> None:
        self.actions = actions
        if "idle" not in self.actions:
            self.actions["idle"] = next(iter(actions.values()))
        width = max(image.width() for frames in actions.values() for image, _delay in frames)
        height = max(image.height() for frames in actions.values() for image, _delay in frames)
        self.character = SimpleNamespace(identifier=identifier, canvas=(width, round(height * HEADROOM)))

    def has_action(self, action: str) -> bool:
        return action in self.actions

    def _frames(self, action: str) -> list[tuple[QImage, int]]:
        if action in self.actions:
            return self.actions[action]
        return self.actions.get(BORROW.get(action, "idle"), self.actions["idle"])

    def render(self, action: str, elapsed_ms: int, *, mirrored: bool = False) -> QImage:
        frames = self._frames(action)
        total = sum(delay for _image, delay in frames)
        moment = elapsed_ms % total
        for image, delay in frames:
            if moment < delay:
                break
            moment -= delay
        width, height = self.character.canvas
        canvas = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if mirrored:
            painter.translate(width, 0)
            painter.scale(-1, 1)
        painter.drawImage(self._place(image, action, elapsed_ms, len(frames) == 1), image)
        painter.end()
        return canvas

    def _place(self, image: QImage, action: str, elapsed_ms: int, still: bool) -> QRectF:
        """Bottom-centred; a still picture is given simple motion so it never looks frozen."""
        width, height = self.character.canvas
        scale_y, lift = 1.0, 0.0
        if still and action == "walk":
            lift = abs(math.sin(elapsed_ms / 180 * math.pi)) * image.height() * 0.05
        elif still and action == "play":
            lift = abs(math.sin(elapsed_ms / 300 * math.pi)) * image.height() * 0.12
        elif still and action == "sleep":
            scale_y = 0.82 + 0.02 * math.sin(elapsed_ms / 1200 * math.pi)     # settled down, breathing
        drawn = QRectF(0, 0, image.width(), image.height() * scale_y)
        drawn.moveBottomLeft(QPointF((width - image.width()) / 2, height - lift))
        return drawn
