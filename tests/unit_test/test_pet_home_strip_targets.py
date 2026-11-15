"""A pet's right-click actions on the desktop strip open the home on that pet, not on whoever was selected."""
from frontengine.ui.page.pet_game.home_page import PetHomePage
from frontengine.ui.page.pet_game.home_panels import ROLE_ID


def test_work_for_this_pet_picks_that_pets_job(lifetime_factory):
    page = PetHomePage(lifetime=lifetime_factory())
    page.create_home()
    page.service.pause('test')
    try:
        page.residents.new_pet()
        page.residents.new_pet()
        first, second, idle = sorted(page.service.world.residents)
        jobs = {}
        for resident in (first, second):
            status, jobs[resident] = page.service.world.create_task('letter', resident)
            assert status == 'accepted'
        page.select_resident(first)
        page.strip_action('work', second)
        assert page.selected_resident == second
        assert page.work.tasks.currentItem().data(ROLE_ID) == jobs[second]
        assert page.work.cancel_button.isEnabled()
        page.strip_action('work', idle)
        assert page.work.tasks.selectedItems() == []
        assert not page.work.cancel_button.isEnabled()
    finally:
        assert page.shutdown()
        page.close()
