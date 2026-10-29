from frontengine.show.pet.desktop_pet import DesktopPetWidget
from frontengine.show.wallpaper.wallpaper_widget import WallpaperWidget


class AudioProvider:
    def __init__(self):
        self.closed = 0
    def __call__(self):
        return 0.5
    def close(self):
        self.closed += 1


def test_pet_closes_native_provider_on_replace_and_close(tmp_path):
    pet = DesktopPetWidget(str(tmp_path / 'missing.png'))
    first, second = AudioProvider(), AudioProvider()
    pet.set_audio_level_provider(first)
    pet.set_audio_level_provider(second)
    assert first.closed == 1
    pet.close()
    assert second.closed == 1


def test_wallpaper_closes_provider_when_reaction_disabled(tmp_path):
    wallpaper = WallpaperWidget(str(tmp_path))
    provider = AudioProvider()
    wallpaper.set_audio_level_provider(provider)
    wallpaper.set_audio_react(True)
    wallpaper.set_audio_react(False)
    assert provider.closed == 1
    wallpaper.close()


def test_macos_screen_audio_provider_has_overlay_owned_lifecycle(monkeypatch):
    from types import SimpleNamespace
    from frontengine.utils.audio_meter import screen_audio
    from frontengine.utils.macos.audio import MacAudioLevelProvider
    monkeypatch.setattr(screen_audio, 'sys', SimpleNamespace(platform='darwin'), raising=False)
    first = screen_audio.audio_level_provider_for_screen(None)
    second = screen_audio.audio_level_provider_for_screen(None)
    assert isinstance(first, MacAudioLevelProvider)
    assert first is not second
    first.close()
    second.close()
