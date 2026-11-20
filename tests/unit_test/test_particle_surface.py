"""A particle field that would black out the screen stops itself and says why."""
from frontengine.show.compositor.surface_check import NO_ALPHA
from frontengine.show.particle import particle_ui
from frontengine.utils.multi_language.retranslate import translate


def test_particles_stop_and_the_page_says_why_when_the_surface_cannot_be_see_through(
        lifetime_factory, monkeypatch):
    from frontengine.ui.page.particle.particle_setting_ui import ParticleSettingUI
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    from frontengine.utils.multi_language.retranslate import retranslator

    page = ParticleSettingUI(lifetime=lifetime_factory())
    page.image_path = ''
    widget = page._create_particle_widget(64, 48)
    reasons = []
    widget.failed.connect(reasons.append)
    monkeypatch.setattr(particle_ui, 'see_through_problem', lambda gl: NO_ALPHA)
    try:
        widget._check_surface()
        assert reasons == [NO_ALPHA]
        assert not widget.timer.isActive()                    # no longer animating behind a black screen
        assert page.ready_label.text() == translate('particle_gpu_unavailable')
        language_wrapper.reset_language('Traditional_Chinese')
        retranslator.apply()
        assert page.ready_label.text() == translate('particle_gpu_unavailable')
    finally:
        language_wrapper.reset_language('English')
        retranslator.apply()
        page.close()


def test_particles_keep_running_on_a_surface_that_can_be_see_through(lifetime_factory, monkeypatch):
    from frontengine.ui.page.particle.particle_setting_ui import ParticleSettingUI

    page = ParticleSettingUI(lifetime=lifetime_factory())
    page.image_path = ''
    widget = page._create_particle_widget(64, 48)
    reasons = []
    widget.failed.connect(reasons.append)
    monkeypatch.setattr(particle_ui, 'see_through_problem', lambda gl: '')
    try:
        widget._check_surface()
        assert reasons == []
        assert widget.timer.isActive()
    finally:
        widget.close()
        page.close()
