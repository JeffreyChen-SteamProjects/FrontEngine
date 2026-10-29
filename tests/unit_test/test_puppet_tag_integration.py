"""Mixed sprite and puppet pets must not call unsupported tag methods."""
from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI


class Puppet:
    def center(self):
        return (0, 0)


class Sprite(Puppet):
    def __init__(self):
        self.roles = []

    def apply_tag_role(self, role):
        self.roles.append(role)


def test_turning_off_tag_with_mixed_pets_resets_only_supported_pets():
    page = PetSettingUI()
    sprite = Sprite()
    page.pet_list = [Puppet(), sprite]
    page._on_tag_toggled(False)
    assert sprite.roles == [None]
    page.close()


def test_tag_timer_requires_two_supported_pets():
    page = PetSettingUI()
    page.pet_list = [Puppet(), Sprite()]
    page.tag_checkbox.setChecked(True)
    page._start_tag_game()
    assert not page.tag_timer.isActive()
    page.close()
