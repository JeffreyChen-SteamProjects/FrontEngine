"""Recognize deliberate back-and-forth strokes without rewarding pointer jitter."""


class PettingGesture:
    def __init__(self, distance: float):
        self.distance = max(4.0, float(distance))
        self.reset()

    def reset(self):
        self.origin = None
        self.direction = None
        self.segments = 0

    def move(self, x: float, y: float) -> bool:
        if self.origin is None:
            self.origin = (x, y)
            return False
        dx, dy = x - self.origin[0], y - self.origin[1]
        if max(abs(dx), abs(dy)) < self.distance:
            return False
        direction = ('x', 1 if dx > 0 else -1) if abs(dx) >= abs(dy) else ('y', 1 if dy > 0 else -1)
        self.origin = (x, y)
        if self.direction is None or direction == (self.direction[0], -self.direction[1]):
            self.segments += 1
        elif direction != self.direction:
            self.segments = 1
        self.direction = direction
        if self.segments >= 3:
            self.reset()
            return True
        return False
