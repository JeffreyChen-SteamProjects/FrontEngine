from typing import List, Tuple, Type

from frontengine.ui.page.scene_setting.scene_page.base_scene_page import BaseSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.gif import GIFSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.image import ImageSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.sound import SoundSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.text import TextSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.video import VideoSceneSettingUI
from frontengine.ui.page.scene_setting.scene_page.web import WebSceneSettingUI

SCENE_PAGE_REGISTRY: List[Tuple[Type[BaseSceneSettingUI], str]] = [
    (GIFSceneSettingUI, "tab_gif_text"),
    (ImageSceneSettingUI, "tab_image_text"),
    (SoundSceneSettingUI, "tab_sound_text"),
    (TextSceneSettingUI, "tab_text_text"),
    (VideoSceneSettingUI, "tab_video_text"),
    (WebSceneSettingUI, "tab_web_text"),
]
