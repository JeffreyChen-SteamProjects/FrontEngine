r"""
產生 Steam 商店與程式庫需要的全套素材。

跑法（從專案根目錄）::

    .venv\Scripts\python.exe steam_assets/generate.py

介面改過之後重跑一次，商店頁的截圖就不會跟實際程式脫節——這也是這支腳本進版控
的理由：圖可以重出，才不會變成沒人敢動的化石。


尺寸一律照 Steamworks 的規格寫死——差一兩個像素就會被退件，所以這裡不做「等比縮放
就好」那種偷懶。每種比例都是各自排版：橫式膠囊放得下一句副標，小膠囊只放得下名字
（它會被縮到 120×45，副標在那個尺寸只是雜訊）。

截圖是真的把程式渲染出來抓的，不是示意圖。寵物家園的截圖與膠囊背景用的是
trailer.py 同一套布景：暫存設定資料夾、四隻存好的寵物搬進新家、在電影時鐘上
過了半天——畫的是真正的家園，不是插圖。
The screenshots are rendered from the real application. The pet home pictures and
the capsule backdrops share trailer.py's staging: a temporary settings folder, four
saved pets moving into a new home, half a day on the film clock.
"""
import json
import os
import sys

# trailer.py sets up the 1920x1080 offscreen screen and the temporary settings folder on import,
# so it has to come before anything that touches Qt.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trailer  # noqa: E402

from PySide6.QtCore import QRect, QSize, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor, QFont, QIcon, QImage, QLinearGradient, QPainter, QRadialGradient,
)
from PySide6.QtWidgets import QApplication  # noqa: E402

# 相對於這個檔案定位，換一台機器 clone 下來一樣跑得動
# Located relative to this file, so a fresh clone on another machine still runs
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(REPO, "steam_assets")

NAME = "FrontEngine"
TAGLINE = "Put anything on top of your screen"
TAGLINE_LONG = "Overlays, a desktop pet with a home of its own, focus tools and presenting aids"

# 取自程式自己的 dark_amber 主題，商店頁和實際程式看起來才是同一個東西
AMBER = QColor("#ffd740")
DARK = QColor("#1b1d1f")
DARKER = QColor("#121415")
TEXT = QColor("#ffffff")
MUTED = QColor(255, 255, 255, 165)

# (檔名, 寬, 高) — 全部依 Steamworks 規格
CAPSULES = [
    ("header_capsule_920x430", 920, 430),
    ("small_capsule_462x174", 462, 174),
    ("main_capsule_1232x706", 1232, 706),
    ("vertical_capsule_748x896", 748, 896),
    ("library_capsule_600x900", 600, 900),
    ("library_hero_3840x1240", 3840, 1240),
    ("page_background_1438x810", 1438, 810),
]


def font(size, bold=True, letter_spacing=0.0):
    value = QFont()
    value.setPixelSize(int(size))
    value.setBold(bold)
    if letter_spacing:
        value.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100 + letter_spacing)
    return value


def fit_font(text, max_width, start_size, bold=True):
    """
    找出「這段字放得進 max_width」的最大字級。

    字級寫死會在最重要的那張圖上出事：小膠囊只有 462px 寬，名字一長就被截掉，
    而它正是會被縮到 120×45、只靠名字辨識的那一張。
    The largest pixel size at which the text still fits. Hard-coding it fails on
    the image that matters most: the small capsule is 462px wide, a long name is
    simply cut off, and that is the one shrunk to 120x45 where the name is all
    there is.
    """
    from PySide6.QtGui import QFontMetrics

    size = int(start_size)
    while size > 8:
        candidate = font(size, bold)
        if QFontMetrics(candidate).horizontalAdvance(text) <= max_width:
            return candidate
        size -= 1
    return font(8, bold)


def home_backdrop(painter, width, height, home, text_top=True):
    """
    家園近景墊底，文字那一側壓深色漸層。家園是角色和家具，清楚的比模糊的好看；
    模糊的設定頁截圖讀起來像破圖。
    The pet home close-up as the backdrop, darkened on the side the text sits. The home is
    characters and furniture, which read sharply; a blurred settings page reads as a fault.
    """
    scaled = home.scaled(QSize(width, height), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                         Qt.TransformationMode.SmoothTransformation)
    painter.drawImage((width - scaled.width()) // 2, height - scaled.height(), scaled)
    shade = QLinearGradient(0, 0, 0, height)
    if text_top:
        shade.setColorAt(0.0, QColor(18, 20, 21, 245))
        shade.setColorAt(0.42, QColor(18, 20, 21, 200))
        shade.setColorAt(0.66, QColor(18, 20, 21, 0))
    else:
        shade.setColorAt(0.0, QColor(18, 20, 21, 0))
        shade.setColorAt(1.0, QColor(18, 20, 21, 120))
    painter.fillRect(0, 0, width, height, shade)


def backdrop(painter, width, height, shot=None, scrim=0.82):
    """底：深色漸層，有截圖的話墊在後面再壓一層暗罩讓文字讀得出來。"""
    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, DARK)
    gradient.setColorAt(1.0, DARKER)
    painter.fillRect(0, 0, width, height, gradient)

    if shot is not None and not shot.isNull():
        # 先大幅縮小再放大 = 便宜的模糊。直接鋪原圖的話，裁切出來的是一塊看得出
        # 是滑桿和下拉選單、卻讀不出意思的碎片，看起來像破圖而不是底紋。
        # Shrink hard then grow back: a cheap blur. Laid in sharp, the crop is a
        # fragment of sliders and dropdowns - recognisable but meaningless, and it
        # reads as a rendering fault rather than as atmosphere.
        tiny = shot.scaled(QSize(max(1, width // 24), max(1, height // 24)),
                           Qt.AspectRatioMode.IgnoreAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
        scaled = tiny.scaled(QSize(width, height), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                             Qt.TransformationMode.SmoothTransformation)
        x = (width - scaled.width()) // 2
        y = (height - scaled.height()) // 2
        painter.drawImage(x, y, scaled)
        painter.fillRect(0, 0, width, height, QColor(18, 20, 21, int(255 * scrim)))

    # 底部再壓一道，文字落在深色上
    fade = QLinearGradient(0, height * 0.45, 0, height)
    fade.setColorAt(0.0, QColor(18, 20, 21, 0))
    fade.setColorAt(1.0, QColor(18, 20, 21, 235))
    painter.fillRect(0, int(height * 0.45), width, int(height * 0.55) + 1, fade)


def atmosphere(painter, width, height, icon, logo_safe=True):
    """
    寬幅背景：深色漸層 + 柔光 + 低透明度的巨大圖示。

    這兩張不能鋪截圖。收藏庫主調圖是 3.1:1，把 16:9 的截圖塞進去只會得到一塊糊
    掉的色斑，兩側大片空白——看起來像沒做完，而不像背景。頁面底圖同理。

    `logo_safe` 會把重點推到右側：收藏庫主調圖上面會疊 logo，中左區必須留空，
    否則 logo 會壓在圖示上，兩個都看不清楚。
    A wide backdrop: dark gradient, a soft glow, and the icon very large and very
    faint.

    Neither of these can take a screenshot. The library hero is 3.1:1, and a 16:9
    screenshot dropped into it is a blurred smear with empty space either side -
    it reads as unfinished rather than as a background. The page background has
    the same problem.

    `logo_safe` pushes the interest to the right: Steam lays the logo over the
    hero, so the centre-left has to stay clear or the two sit on top of each other
    and neither can be read.
    """
    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, QColor("#16181a"))
    gradient.setColorAt(0.55, QColor("#1d2023"))
    gradient.setColorAt(1.0, QColor("#0d0f10"))
    painter.fillRect(0, 0, width, height, gradient)

    # 柔光：放在右側三分之一，和 logo 的位置錯開
    glow_x = width * (0.74 if logo_safe else 0.5)
    glow = QRadialGradient(glow_x, height * 0.45, max(width, height) * 0.55)
    glow.setColorAt(0.0, QColor(255, 215, 64, 46))
    glow.setColorAt(0.45, QColor(255, 215, 64, 16))
    glow.setColorAt(1.0, QColor(255, 215, 64, 0))
    painter.fillRect(0, 0, width, height, glow)

    # 巨大但很淡的圖示當浮水印
    if icon is not None:
        mark = int(height * 0.92)
        pixmap = icon.pixmap(QSize(mark, mark))
        if not pixmap.isNull():
            painter.save()
            painter.setOpacity(0.13)
            painter.drawPixmap(int(glow_x - mark * 0.5), int((height - mark) / 2),
                               mark, mark, pixmap)
            painter.restore()

    # 底部壓一道，Steam 疊上去的文字才讀得出來
    fade = QLinearGradient(0, height * 0.55, 0, height)
    fade.setColorAt(0.0, QColor(13, 15, 16, 0))
    fade.setColorAt(1.0, QColor(13, 15, 16, 200))
    painter.fillRect(0, int(height * 0.55), width, int(height * 0.45) + 1, fade)


def draw_icon(painter, icon, x, y, size):
    if icon is None:
        return
    pixmap = icon.pixmap(QSize(size, size))
    if not pixmap.isNull():
        painter.drawPixmap(x, y, size, size, pixmap)


def accent_rule(painter, x, y, width, height=4):
    painter.fillRect(QRect(x, y, width, height), AMBER)


def compose(kind, width, height, icon, shot):
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    if kind == "small":
        # 會被縮到 120×45，所以只有名字，而且要大。副標在那個尺寸是雜訊。
        backdrop(painter, width, height, None)
        icon_size = int(height * 0.62)
        margin = int(height * 0.19)
        draw_icon(painter, icon, margin, margin, icon_size)
        text_left = margin * 2 + icon_size
        available = width - text_left - margin
        painter.setFont(fit_font(NAME, available, height * 0.40))
        painter.setPen(TEXT)
        painter.drawText(QRect(text_left, 0, available, height),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, NAME)

    elif kind in ("header", "main"):
        home_backdrop(painter, width, height, shot(width, height, 0.98))
        # 名字和圖示同一列放在上方，下面留給家園。
        # Icon and name share a row at the top; the lower part belongs to the home.
        margin = int(width * 0.055)
        icon_size = int(height * 0.20)
        top = int(height * 0.08)
        draw_icon(painter, icon, margin, top, icon_size)
        text_left = margin + icon_size + int(height * 0.05)
        painter.setFont(fit_font(NAME, width - text_left - margin, height * 0.17))
        painter.setPen(TEXT)
        painter.drawText(QRect(text_left, top, width - text_left - margin, icon_size),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, NAME)
        name_y = top + icon_size

        accent_rule(painter, margin, name_y + int(height * 0.04), int(width * 0.13),
                    max(3, int(height * 0.012)))

        painter.setFont(font(height * 0.062, bold=False))
        painter.setPen(MUTED)
        painter.drawText(QRect(margin, name_y + int(height * 0.08),
                               width - margin * 2, int(height * 0.2)),
                         Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
                         | Qt.TextFlag.TextWordWrap,
                         TAGLINE if kind == "header" else TAGLINE_LONG)

    elif kind in ("vertical", "library"):
        # 文字在上半，家園在下半：直式膠囊的下方剛好放得下一整排寵物和家具。
        # Text in the upper half, the home in the lower: a tall capsule has just the room
        # below for a row of pets and furniture.
        home_backdrop(painter, width, height, shot(width, height, 0.97))
        margin = int(width * 0.10)
        icon_size = int(width * 0.26)
        draw_icon(painter, icon, (width - icon_size) // 2, int(height * 0.08), icon_size)

        painter.setFont(fit_font(NAME, width - margin * 2, width * 0.145))
        painter.setPen(TEXT)
        painter.drawText(QRect(0, int(height * 0.32), width, int(height * 0.14)),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, NAME)

        # 底線要在文字下伸部之下，不然會切過「g」的尾巴。
        # Below the descenders, or the rule cuts through the tail of the "g".
        accent_rule(painter, (width - int(width * 0.22)) // 2, int(height * 0.475),
                    int(width * 0.22), max(3, int(height * 0.007)))

        painter.setFont(font(width * 0.052, bold=False))
        painter.setPen(MUTED)
        painter.drawText(QRect(margin, int(height * 0.51), width - margin * 2, int(height * 0.16)),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
                         | Qt.TextFlag.TextWordWrap, TAGLINE)

    elif kind == "hero":
        # Hero 上面會疊 logo，所以不放任何文字；家園的重點偏右，讓出中左給 logo。
        # Steam lays the logo over the hero, so no text here, and the home leans right of the logo.
        home_backdrop(painter, width, height, shot(width, height, 0.94, 0.68), text_top=False)

    elif kind == "background":
        atmosphere(painter, width, height, icon, logo_safe=False)

    painter.end()
    return image


def frame_shot(shot, width=1920, height=1080):
    """把視窗畫面擺在深色底板中央，四周留白。"""
    canvas = QImage(width, height, QImage.Format.Format_ARGB32)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, QColor("#202325"))
    gradient.setColorAt(1.0, QColor("#0e1011"))
    painter.fillRect(0, 0, width, height, gradient)

    margin = 70
    scaled = shot.scaled(QSize(width - margin * 2, height - margin * 2),
                         Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    x = (width - scaled.width()) // 2
    y = (height - scaled.height()) // 2
    # 一圈淡淡的外框，讓視窗和底板分得開
    painter.fillRect(x - 1, y - 1, scaled.width() + 2, scaled.height() + 2, QColor(0, 0, 0, 140))
    painter.drawImage(x, y, scaled)
    painter.end()
    return canvas


def library_logo(icon):
    """透明背景的識別標誌，Steam 會把它疊在 hero 上。"""
    width, height = 1280, 720
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    icon_size = 260
    draw_icon(painter, icon, (width - icon_size) // 2, 150, icon_size)
    painter.setFont(fit_font(NAME, width - 160, 150))
    painter.setPen(TEXT)
    painter.drawText(QRect(0, 440, width, 180),
                     Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, NAME)
    accent_rule(painter, (width - 220) // 2, 620, 220, 8)
    painter.end()
    return image


def screenshots(icon_path):
    """
    把程式真的渲染出來逐頁抓圖，再合成到 1920×1080 的底板上。

    兩件事必須先處理。**語言強制英文**：這台機器的 Steam 設定是繁體中文，程式的
    首次啟動語言功能會照做，而離屏環境沒有中文字型，抓出來整片都是豆腐方塊。
    **視窗不要開成 1920 寬**：重新設計之後控制項有最大寬度（對操作是對的），
    整個視窗拉到 1920 的話右邊三分之二是空的，當商店截圖很難看。

    Two things have to be handled first. **Force English**: this machine's Steam is
    set to Traditional Chinese and the first-launch language feature honours it,
    but the offscreen environment has no CJK font, so every label comes out as
    tofu boxes. **Do not open the window at 1920 wide**: since the redesign the
    controls have a maximum width - right for using it - which at 1920 leaves the
    right two thirds empty and makes a poor store screenshot.
    """
    from frontengine.ui.main_ui import FrontEngineMainUI
    from frontengine.ui.style.app_style import apply_app_style

    window = FrontEngineMainUI(show_system_tray_ray=False, redirect_output=False)
    apply_app_style(window, "dark", application=True)
    window.resize(1360, 900)
    window.show()
    application = QApplication.instance()
    application.processEvents()

    # The pet home first: staged like the trailer, then half a working day on the film clock.
    home = window.pet_home_ui
    trailer.stage_page(application, home)
    window.page_stack.setCurrentWidget(home)
    window.sidebar.select_page(window.page_stack.indexOf(home))
    home.create_home()
    trailer.wait_for_art(application, home)
    presets = home.layout_panel.presets
    presets.setCurrentIndex(presets.findData("cozy"))
    home.layout_panel.apply_layout()
    # Half a day or so, until a clear afternoon: rain streaks read as scratches on a capsule.
    from frontengine.utils.pet_game.environment import weather
    from frontengine.utils.pet_game.schedule import game_hour
    trailer.run_home(application, home, 600)
    for _ in range(200):
        world = home.service.world
        if weather(world.home, world.time_ms) == "clear" and 10 <= game_hour(world.time_ms) <= 16:
            break
        trailer.run_home(application, home, 60)
    application.processEvents()

    def save(name, image):
        path = os.path.join(OUT, "screenshots", f"{name}_1920x1080.png")
        image.save(path)
        print(f"  screenshot: {os.path.basename(path)}  {image.width()}x{image.height()}")

    save("01_pet_home", frame_shot(window.grab().toImage()))
    save("02_pet_home_close", trailer.close_up_image(home.view, 3.0, trailer.home_center(home)))
    save("03_pet_home_desktop", trailer.desktop_image(home))

    def home_shot(width, height, floor_at, center_at=0.5):
        """The home redrawn for one capsule size: the floor near the bottom, the pets in view."""
        view = home.view
        # Big enough that the pets read even on a 920x430 header, and never narrower than the picture.
        # The furniture and pets fill only the lower third of the home drawing; its sky may be cropped.
        scale = max(height * 1.25 / view.height(), width / view.width())
        # A tall picture has room for only a few pieces: it shows the pets, a wide one the whole home.
        middle = trailer.pets_center(home) if width < height else trailer.home_center(home)
        center = middle + (0.5 - center_at) * width / scale
        return trailer.close_up_image(view, scale, center, width, height, floor_at)

    pages = [
        ("04_video", window.video_setting_ui),
        ("05_pet", window.pet_setting_ui),
        ("06_tools", window.tools_setting_ui),
        ("07_presenting", window.presentation_setting_ui),
        ("08_eye_care", window.screen_care_setting_ui),
        ("09_widgets", window.widgets_setting_ui),
        ("10_wallpaper", window.wallpaper_setting_ui),
        ("11_control_center", window.control_center_ui),
    ]
    shots = []
    for name, page in pages:
        window.page_stack.setCurrentWidget(page)
        window.sidebar.select_page(window.page_stack.indexOf(page))
        QApplication.processEvents()
        framed = frame_shot(window.grab().toImage())
        path = os.path.join(OUT, "screenshots", f"{name}_1920x1080.png")
        framed.save(path)
        shots.append(framed)
        print(f"  screenshot: {os.path.basename(path)}  {framed.width()}x{framed.height()}")
    return home_shot


def main():
    # 一定要留著參考：QApplication 被回收的話，後面所有繪圖都會失敗。
    # 用 setApplicationName 而不是 assert 來持有它——assert 在 -O 編譯時會整行
    # 消失，那時候持有的理由也跟著消失了。
    # Keep the reference: garbage-collecting QApplication takes every later paint
    # call with it. Held through setApplicationName rather than an assert, because
    # -O strips asserts entirely and would take the reason for holding it too.
    # English on purpose: the store's default language, and the page is read by everyone.
    with open("user_setting.json", "w", encoding="utf-8") as handle:
        json.dump({"language": "English"}, handle)
    application = QApplication([])
    application.setApplicationName(NAME)
    trailer._use_film_clock()
    os.makedirs(os.path.join(OUT, "screenshots"), exist_ok=True)
    icon_path = os.path.join(REPO, "exe", "frontengine.ico")
    icon = QIcon(icon_path) if os.path.exists(icon_path) else None

    print("=== screenshots (rendered from the real application) ===")
    hero_shot = screenshots(icon_path)

    print("=== capsules ===")
    kinds = {
        "header_capsule_920x430": "header",
        "small_capsule_462x174": "small",
        "main_capsule_1232x706": "main",
        "vertical_capsule_748x896": "vertical",
        "library_capsule_600x900": "library",
        "library_hero_3840x1240": "hero",
        "page_background_1438x810": "background",
    }
    for name, width, height in CAPSULES:
        image = compose(kinds[name], width, height, icon, hero_shot)
        path = os.path.join(OUT, f"{name}.png")
        image.save(path)
        print(f"  {name}.png  {image.width()}x{image.height()}")

    logo = library_logo(icon)
    logo.save(os.path.join(OUT, "library_logo_1280x720.png"))
    print(f"  library_logo_1280x720.png  {logo.width()}x{logo.height()}  (transparent)")

    if icon is not None:
        for size in (32, 184):
            pixmap = icon.pixmap(QSize(size, size))
            pixmap.save(os.path.join(OUT, f"community_icon_{size}x{size}.png"))
            print(f"  community_icon_{size}x{size}.png")

    print(f"\nall assets written to: {OUT}")


if __name__ == "__main__":
    main()
