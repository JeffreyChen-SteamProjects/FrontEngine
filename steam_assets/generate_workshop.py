r"""Generate simple Workshop artwork using the existing Steam asset style.

Run from the repository root:
    .venv\Scripts\python.exe steam_assets/generate_workshop.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QIcon, QImage, QPainter
from PySide6.QtWidgets import QApplication

from generate import AMBER, MUTED, TEXT, accent_rule, backdrop, draw_icon, fit_font

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "steam_assets" / "workshop"
TAGLINE = "Make your desktop yours."


def draw_label(painter: QPainter, text: str, rect: QRect, size: int,
               color, centered: bool = False, bold: bool = True) -> None:
    """Draw fitted text within a fixed rectangle."""
    label_font = fit_font(text, rect.width(), size, bold=bold)
    label_font.setFamily("Segoe UI")
    painter.setFont(label_font)
    painter.setPen(color)
    alignment = Qt.AlignmentFlag.AlignVCenter
    alignment |= (Qt.AlignmentFlag.AlignHCenter if centered
                  else Qt.AlignmentFlag.AlignLeft)
    painter.drawText(rect, alignment, text)


def compose(width: int, height: int, icon: QIcon) -> QImage:
    """Reuse the store's backdrop, app icon, typography and accent rule."""
    image = QImage(width, height, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    try:
        painter.setRenderHints(QPainter.RenderHint.Antialiasing
                               | QPainter.RenderHint.TextAntialiasing
                               | QPainter.RenderHint.SmoothPixmapTransform)
        backdrop(painter, width, height)
        if width == height:
            draw_icon(painter, icon, 204, 60, 104)
            draw_label(painter, "FrontEngine", QRect(44, 196, 424, 80),
                       64, TEXT, centered=True)
            draw_label(painter, "Workshop", QRect(44, 275, 424, 60),
                       42, AMBER, centered=True)
            accent_rule(painter, 202, 356, 108, 4)
            draw_label(painter, TAGLINE, QRect(44, 385, 424, 45),
                       25, MUTED, centered=True, bold=False)
        else:
            draw_icon(painter, icon, 50, 54, 108)
            draw_label(painter, "FrontEngine", QRect(50, 182, 820, 90),
                       82, TEXT)
            draw_label(painter, "Workshop", QRect(50, 267, 820, 50),
                       36, AMBER)
            accent_rule(painter, 50, 331, 120, 5)
            draw_label(painter, TAGLINE, QRect(50, 354, 820, 40),
                       27, MUTED, bold=False)
    finally:
        painter.end()
    return image


def save_assets(icon: QIcon) -> list[dict]:
    """Write PNG masters and lightweight JPEG variants."""
    metadata = []
    for stem, role, width, height in (
        ("workshop_brand_landscape", "landscape_brand", 920, 430),
        ("workshop_preview_square", "square_preview", 512, 512),
    ):
        image = compose(width, height, icon)
        for extension in ("png", "jpg"):
            path = OUTPUT / f"{stem}.{extension}"
            if not image.save(str(path), quality=90 if extension == "jpg" else -1):
                raise OSError(f"Could not save {path}")
            data = path.read_bytes()
            if len(data) >= 1_000_000:
                raise ValueError(f"Preview exceeds the project size limit: {path}")
            metadata.append({"file": path.name, "role": role, "width": width,
                             "height": height, "bytes": len(data),
                             "sha256": hashlib.sha256(data).hexdigest()})
            print(f"{path.name}: {width}x{height}, {len(data)} bytes")
    return metadata


def main() -> None:
    """Regenerate artwork and refresh the existing brand metadata."""
    application = QApplication.instance() or QApplication([])
    application.setApplicationName("FrontEngine Workshop assets")
    icon_path = ROOT / "exe" / "frontengine.ico"
    icon = QIcon(str(icon_path))
    if icon.isNull():
        raise FileNotFoundError(f"App icon unavailable: {icon_path}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    metadata_path = OUTPUT / "brand.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["images"] = save_assets(icon)
    metadata["artwork_method"] = "programmatic_qpainter"
    metadata["generator"] = "steam_assets/generate_workshop.py"
    metadata["reference"] = "steam_assets/header_capsule_920x430.png"
    metadata["icon_source"] = "exe/frontengine.ico"
    payload = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    metadata_path.write_bytes(payload.replace("\n", "\r\n").encode("utf-8"))


if __name__ == "__main__":
    main()
