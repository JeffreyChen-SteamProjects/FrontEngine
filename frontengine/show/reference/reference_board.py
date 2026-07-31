"""
參考圖板：一塊畫布上放好幾張圖，各自可以搬動，整塊可以縮放平移。

和「圖片覆蓋層」的差別是數量與擺法：覆蓋層是把一張圖固定在某個位置當背景，圖板
是把一疊參考資料攤開來排在手邊——畫圖的、做設計的、對著規格寫程式的都在做這件事。

視圖行為（無邊框、置頂、透明、滾輪縮放、拖曳平移）沿用場景功能的
`ExtendGraphicView`，這裡只負責「放什麼進去、一開始怎麼排」。

A reference board: several images on one canvas, each movable, the whole thing
zoomable and pannable.

It differs from the image overlay in number and arrangement: the overlay fixes one
picture in place as a backdrop, while a board spreads a pile of references out
within reach - what illustrators, designers and anyone coding against a
specification actually do.

The view behaviour - frameless, on top, transparent, wheel zoom, drag to pan -
comes from the scene feature's `ExtendGraphicView`; this only decides what goes on
it and how it is laid out to begin with.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene

from frontengine.show.scene.extend_graphic_view import ExtendGraphicView
from frontengine.utils.logging.loggin_instance import front_engine_logger

BOARD_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
DEFAULT_COLUMNS = 3
DEFAULT_ITEM_SIZE = 320
ITEM_GAP = 24


def columns_for(count: int, preferred: int = DEFAULT_COLUMNS) -> int:
    """
    幾張圖排幾欄。張數比預設欄數少時就照張數排，免得三張圖被排成一欄兩列、
    右邊空一大塊。
    How many columns for this many images. Fewer images than the preferred column
    count simply use their own number, so three pictures are not laid out as a
    row of two with a gap beside them.
    """
    count = max(0, int(count))
    if count == 0:
        return 0
    return max(1, min(int(preferred), count))


def grid_positions(count: int, item_size: int = DEFAULT_ITEM_SIZE,
                   columns: int = DEFAULT_COLUMNS,
                   gap: int = ITEM_GAP) -> List[Tuple[int, int]]:
    """
    一開始把圖排成網格的座標。純算術，所以排版不必開視窗就能驗。

    先排好再讓使用者自己搬：全部疊在原點的話，開起來看到的是一張圖，其他幾張都
    藏在下面，使用者會以為只載入了一張。
    The initial grid coordinates. Pure arithmetic, so the layout can be checked
    without a window.

    They are arranged before the user rearranges them: stacked at the origin, the
    board would open showing one picture with the rest hidden underneath, and it
    would look as though only one had loaded.
    """
    count = max(0, int(count))
    if count == 0:
        return []
    column_count = columns_for(count, columns)
    step = max(1, int(item_size)) + max(0, int(gap))
    return [((index % column_count) * step, (index // column_count) * step)
            for index in range(count)]


def readable_images(paths: Sequence[str]) -> List[str]:
    """
    留下副檔名認得、而且真的讀得進來的圖。

    壞掉或不是圖片的檔案要在這裡就擋下來：讓 QPixmap 靜靜產生一張空圖的話，圖板
    上會出現一塊看不見的空白，使用者只會覺得「有一張圖不見了」。
    Keep the files whose suffix is known and that actually load.

    A broken or non-image file is dropped here: letting QPixmap quietly produce a
    null pixmap puts an invisible blank on the board, and all the user sees is
    that one of their pictures is missing.
    """
    kept = []
    for path in paths or ():
        try:
            candidate = Path(str(path))
            if candidate.suffix.lower() not in BOARD_EXTENSIONS:
                continue
            if not candidate.is_file():
                continue
        except OSError:  # pragma: no cover - filesystem boundary
            continue
        if QPixmap(str(candidate)).isNull():
            front_engine_logger.info(f"[ReferenceBoard] skipped unreadable image: {candidate}")
            continue
        kept.append(str(candidate))
    return kept


class ReferenceBoardWidget(ExtendGraphicView):
    """好幾張參考圖放在同一塊畫布上，各自可以搬動。"""

    def __init__(self, item_size: int = DEFAULT_ITEM_SIZE, columns: int = DEFAULT_COLUMNS):
        front_engine_logger.info("[ReferenceBoardWidget] Init")
        self.board_scene = QGraphicsScene()
        super().__init__(self.board_scene)
        self.item_size = max(64, int(item_size))
        self.columns = max(1, int(columns))
        self.items: List[QGraphicsPixmapItem] = []

    def add_images(self, paths: Sequence[str]) -> int:
        """把圖加進圖板並排好，回傳實際加進去的張數。"""
        usable = readable_images(paths)
        positions = grid_positions(len(usable), self.item_size, self.columns)
        for path, (x, y) in zip(usable, positions):
            pixmap = QPixmap(path).scaled(
                self.item_size, self.item_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            item = QGraphicsPixmapItem(pixmap)
            # 每張圖各自可以搬：圖板的用途就是把它們排成自己看得順的位置。
            # Each picture moves on its own: arranging them is the whole point.
            item.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, True)
            item.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable, True)
            item.setPos(x, y)
            self.board_scene.addItem(item)
            self.items.append(item)
        front_engine_logger.info(f"[ReferenceBoardWidget] added {len(usable)} of {len(paths or ())}")
        return len(usable)

    def remove_selected(self) -> int:
        """把選起來的圖從圖板上拿掉，回傳拿掉幾張。"""
        removed = 0
        for item in list(self.items):
            if item.isSelected():
                self.board_scene.removeItem(item)
                self.items.remove(item)
                removed += 1
        return removed

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.remove_selected()
            return
        super().keyPressEvent(event)
