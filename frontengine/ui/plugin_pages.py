"""API v1 plugin page lifecycle and namespaced preset contracts."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger


def attach_page(name: str, factory: type, control_center) -> QWidget:
    """Attach a trusted page's dynamic overlay list and reusable batch cleanup hook."""
    if not isinstance(factory, type) or not issubclass(factory, QWidget):
        raise ValueError('Plugin tabs must be QWidget subclasses')
    page = factory()
    if hasattr(page, 'overlay_widgets'):
        control_center.register_overlay_source(lambda: page.overlay_widgets)
    cleanup = getattr(page, 'release_overlay_resources', None)
    if callable(cleanup):
        control_center.register_cleanup(cleanup)
    return page


def preset_pages(ui) -> list[tuple[str, QWidget]]:
    """Only currently loaded trusted pages opt into JSON get_state/set_state."""
    return [(f'plugin:{name}', page) for name, page in getattr(ui, 'plugin_pages', {}).items()
            if callable(getattr(page, 'get_state', None)) and callable(getattr(page, 'set_state', None))]


def shutdown_pages(ui) -> None:
    """Dispose page-local jobs after registered overlays have closed; isolate plugin faults."""
    for name, page in getattr(ui, 'plugin_pages', {}).items():
        shutdown = getattr(page, 'shutdown', None)
        if callable(shutdown):
            try:
                shutdown()
            except Exception as error:
                front_engine_logger.warning(f'[plugins] page shutdown failed: {name}: {error}')
