import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from frontengine.show.pet_game.home_view import HomeView
from frontengine.utils.pet_game.catalog import builtin_catalog
from frontengine.utils.pet_game.world import World


@pytest.fixture
def home_view():
    world = World(builtin_catalog(), "a" * 32)
    zone = world.add_zone("screen", 0, 0, 24)
    pet = "b" * 32
    world.add_resident({"id": pet, "name": "Recovery worker", "mood": 80,
                        "fullness": 80, "energy": 80, "affection": 0}, zone)
    view = HomeView()
    try:
        view.set_world(world, zone)
        view.resize(960, 170)
        yield view, world.residents[pet]
    finally:
        view.close()
        view.deleteLater()


@pytest.mark.parametrize("edge", ["left", "right"])
def test_visible_resident_caption_fits_within_home_edge(home_view, edge):
    view, resident = home_view
    resident.x_milli = 0 if edge == "left" else view.world.zones[view.zone].width_pixels * 1000
    assert QRectF(view.rect()).contains(view.caption_rect(resident))


@pytest.mark.parametrize("scroll", [-2000, 2000])
def test_offscreen_resident_caption_is_not_pulled_into_view(home_view, scroll):
    view, resident = home_view
    view.scroll_x = scroll
    assert not QRectF(view.rect()).intersects(view.resident_box(resident))
    assert not QRectF(view.rect()).intersects(view.caption_rect(resident))


@pytest.mark.parametrize("edge", ["left", "right"])
def test_long_name_and_desktop_plate_fit_caption(home_view, edge):
    view, resident = home_view
    resident.name = "A long resident name needing an ellipsis at the home edge"
    resident.x_milli = 0 if edge == "left" else view.world.zones[view.zone].width_pixels * 1000
    view.caption_backdrop = True
    image = QImage(view.size(), QImage.Format.Format_ARGB32)
    class Capture(QPainter):
        def drawText(self, rect, flags, text):
            self.text = text
            self.text_rect = QRectF(rect)
            super().drawText(rect, flags, text)

        def drawRoundedRect(self, rect, *args):
            self.plate = QRectF(rect)
            super().drawRoundedRect(rect, *args)

    painter = Capture(image)
    try:
        view._paint_resident(painter, resident)
        assert painter.text.endswith("…")
        assert painter.fontMetrics().horizontalAdvance(painter.text) <= painter.text_rect.width()
        assert QRectF(view.rect()).contains(painter.plate)
        assert painter.plate.contains(painter.text_rect.center())
    finally:
        painter.end()
