"""Settings ownership layered on storage-free Qt work retirement."""
from frontengine.utils.work_lifetime import (
    WorkLifetime, CloseDisposition, RuntimeState, captured_lifetime,
    owned_callback, owned_action, OwnedWidgetList,
)
from frontengine.user_setting.storage_session import StorageClosed


class MainRuntimeInUse(RuntimeError):
    pass


_main_lifetime = None


class DefaultSettingsLifetime(WorkLifetime):
    def __init__(self, binding, main=False):
        super().__init__()
        self._binding = binding
        self.storage = binding.storage
        self._main = main

    @classmethod
    def open(cls, *, main=False):
        global _main_lifetime
        if main and _main_lifetime is not None and not _main_lifetime.closed:
            raise MainRuntimeInUse('A FrontEngine main window is already live or closing')
        from frontengine.user_setting.default_storage import acquire_default_binding
        lifetime = cls(acquire_default_binding(), main)
        if main:
            _main_lifetime = lifetime
        return lifetime

    def require_live(self):
        if not self.accepting:
            raise StorageClosed('The settings lifetime is not accepting new work')

    def _release(self):
        global _main_lifetime
        if not self._binding.close():
            return False
        if _main_lifetime is self:
            _main_lifetime = None
        return True

__all__ = ["DefaultSettingsLifetime", "CloseDisposition", "RuntimeState", "MainRuntimeInUse",
           "captured_lifetime", "owned_callback", "owned_action", "OwnedWidgetList"]
