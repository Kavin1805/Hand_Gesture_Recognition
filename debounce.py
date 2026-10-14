"""Decides WHEN a gesture becomes a message.

Rules (all times come from config.yaml):
- Thumb_Up / Thumb_Down / Closed_Fist: held for `hold_seconds` -> send.
- Open_Palm: waving -> "Wave" (Hi). Held still for `stop_hold_seconds` -> "Open_Palm" (Stop).
  While the hand is waving, Stop is never sent.
- The same event is not sent again within `cooldown_seconds`.

Like wave_detector.py, this module only sees numbers and labels, so it can be tested
without a camera (see tests/test_logic.py).
"""

from wave_detector import WaveDetector

OPEN_PALM = "Open_Palm"
WAVE = "Wave"


class GestureLogic:
    def __init__(self, cfg):
        t = cfg["timing"]
        self.hold = float(t["hold_seconds"])
        self.stop_hold = float(t["stop_hold_seconds"])
        self.cooldown = float(t["cooldown_seconds"])
        self.repeat = bool(t["repeat_while_held"])
        self.flicker = float(t["flicker_tolerance_seconds"])
        self.still_tol = float(cfg["wave"]["still_tolerance"])
        self.blur_tol = float(cfg["wave"]["blur_tolerance_seconds"])
        self.known = set(cfg["messages"].keys())
        self.wave = WaveDetector(cfg["wave"])

        self.current = None       # label being held right now (None = nothing useful)
        self.since = 0.0          # when `current` started (or when the palm last became still)
        self.last_seen = 0.0      # last frame in which `current` was seen
        self.fired = False        # already sent during this hold (used when repeat_while_held is false)
        self.wave_fired = False
        self.anchor = None        # (x, y) in palm lengths where the open palm came to rest
        self.last_sent = {}       # event -> time it was last sent
        self.status = ""          # short text for the preview window

    # ------------------------------------------------------------------
    def update(self, now, label, x=0.0, y=0.0, palm=1.0, hand_visible=True):
        """Feed one frame.

        label        : model label, or None when no hand is visible
        x, y, palm   : hand centre and palm length in pixels (ignored if no hand)
        hand_visible : False when no hand was found in the frame

        Returns the event to send ("Thumb_Up", "Open_Palm", "Wave", ...) or None.
        """
        if label not in self.known or label == WAVE:
            label = None   # unknown gestures ("Victory", "None", ...) are ignored

        # --- which gesture is being held? ---------------------------------
        if label == self.current:
            self.last_seen = now
        elif (self.current == OPEN_PALM and label is None and hand_visible
              and now - self.last_seen <= self.blur_tol):
            # A fast-moving open hand is blurred, so the model often answers
            # "None" for a few frames while still tracking the hand. Keep
            # treating it as an open palm so a wave is not interrupted.
            pass
        elif now - self.last_seen > self.flicker or self.current is None:
            self._start(label, now)
        # else: brief dropout - keep treating `current` as held

        if self.current is None:
            self.status = ""
            return None

        if self.current == OPEN_PALM:
            return self._update_open_palm(now, hand_visible, x, y, palm)

        held = now - self.since
        self.status = f"hold {min(held, self.hold):.1f}/{self.hold:.1f}s"
        if held >= self.hold and not self.fired:
            return self._try_send(self.current, now)
        return None

    # ------------------------------------------------------------------
    def _start(self, label, now):
        self.current = label
        self.since = now
        self.last_seen = now
        self.fired = False
        self.wave_fired = False
        self.anchor = None
        self.wave.reset()

    def _update_open_palm(self, now, hand_visible, x, y, palm):
        if hand_visible:
            waving = self.wave.update(now, x, palm)
            # Stillness: remember where the palm rested. If it drifts further
            # than the tolerance, restart the "held still" timer from here.
            px, py = x / palm, y / palm
            if self.anchor is None:
                self.anchor = (px, py)
            elif abs(px - self.anchor[0]) > self.still_tol or abs(py - self.anchor[1]) > self.still_tol:
                self.anchor = (px, py)
                self.since = now
                self.fired = False      # a new still period may send Stop again
        else:
            waving = self.wave.is_waving(now)   # dropout frame: no new position

        if waving:
            self.status = "waving"      # Stop is never sent while waving
            if not self.wave_fired:
                return self._try_send(WAVE, now, wave=True)
            return None

        self.wave_fired = False         # wave ended; the next wave may send again
        still = now - self.since
        self.status = f"still {min(still, self.stop_hold):.1f}/{self.stop_hold:.1f}s"
        if still >= self.stop_hold and not self.fired:
            return self._try_send(OPEN_PALM, now)
        return None

    def _try_send(self, event, now, wave=False):
        last = self.last_sent.get(event)
        if last is not None and now - last < self.cooldown:
            self.status += " (cooldown)"
            return None
        self.last_sent[event] = now
        if not self.repeat:
            # Send once per hold / per wave; wait for a release before sending again.
            if wave:
                self.wave_fired = True
            else:
                self.fired = True
        return event
