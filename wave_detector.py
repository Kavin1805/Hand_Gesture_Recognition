"""Wave detection from hand position across frames.

Method
------
A wave is side-to-side motion, so only the horizontal position (x) of the
hand centre is used.

1. Follow the hand in its current direction and remember the furthest point
   reached (the "extreme").
2. When the hand comes back from that extreme by more than `min_swing`
   palm lengths, that is a direction change. Record the time, and start
   following the new direction.
3. If at least `min_direction_changes` direction changes happened within the
   last `window_seconds`, the hand is waving.

Step 2 is what rejects jitter: small trembling never travels `min_swing`
back from the extreme, so it never counts. A hand that simply moves across
the frame once produces zero direction changes, so it is not a wave either.

Distances are divided by the palm length, so the same thresholds work with
the hand near or far from the camera.

This module has no camera or MediaPipe dependency: it only sees numbers.
"""

from collections import deque


class WaveDetector:
    def __init__(self, wave_cfg):
        self.window = float(wave_cfg["window_seconds"])
        self.min_changes = int(wave_cfg["min_direction_changes"])
        self.min_swing = float(wave_cfg["min_swing"])
        self.reset()

    def reset(self):
        self._direction = 0        # +1 moving right, -1 moving left, 0 not known yet
        self._extreme = None       # furthest x reached in the current direction (palm lengths)
        self._changes = deque()    # times of recent direction changes

    def update(self, now, x_pixels, palm_pixels):
        """Feed one hand position. Returns True while the hand is waving."""
        x = x_pixels / palm_pixels   # position measured in palm lengths

        if self._extreme is None:
            self._extreme = x
        elif self._direction == 0:
            # No direction yet: wait for the first clear movement.
            if abs(x - self._extreme) >= self.min_swing:
                self._direction = 1 if x > self._extreme else -1
                self._extreme = x
        elif (x - self._extreme) * self._direction > 0:
            # Still going the same way: push the extreme further out.
            self._extreme = x
        elif abs(x - self._extreme) >= self.min_swing:
            # Came back far enough: this is a direction change.
            self._direction = -self._direction
            self._extreme = x
            self._changes.append(now)

        return self.is_waving(now)

    def is_waving(self, now):
        while self._changes and now - self._changes[0] > self.window:
            self._changes.popleft()
        return len(self._changes) >= self.min_changes
