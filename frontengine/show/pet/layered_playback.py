"""Active-time playback driven by the pet's existing repaint loop."""
from time import monotonic


class LayeredPlayback:
    def __init__(self, clock=monotonic) -> None:
        self.clock = clock
        self.renderer = None
        self.action = 'idle'
        self._elapsed = 0.0
        self._started = None

    def set_renderer(self, renderer) -> None:
        if renderer is not self.renderer:
            self.renderer = renderer
            self._elapsed = 0.0
            if self._started is not None:
                self._started = self.clock()

    def set_action(self, action: str) -> None:
        if action != self.action:
            self.action = action
            self._elapsed = 0.0
            if self._started is not None:
                self._started = self.clock()

    def resume(self) -> None:
        if self._started is None:
            self._started = self.clock()

    def pause(self) -> None:
        if self._started is not None:
            self._elapsed += max(0.0, self.clock() - self._started)
            self._started = None

    def frame(self):
        if self.renderer is None:
            return None
        elapsed = self._elapsed
        if self._started is not None:
            elapsed += max(0.0, self.clock() - self._started)
        return self.renderer.render(self.action, int(elapsed * 1000))
