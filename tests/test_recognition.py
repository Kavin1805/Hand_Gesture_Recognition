"""Stage 2 - recognition only. Shows landmarks and the raw model label for every frame.
No debounce, no wave logic, no MQTT. q or Esc to quit."""
import _path  # noqa: F401
import time

import preview
from capture import Camera
from config import load_config
from recognition import GestureRecognizer

cfg = load_config()
cam = Camera(cfg["camera"])
rec = GestureRecognizer(cfg["model"])
start = last = time.monotonic()
fps, last_label = 0.0, None
while True:
    frame = cam.read()
    if frame is None:
        break
    now = time.monotonic()
    hand = rec.process(frame, (now - start) * 1000)
    fps = 0.9 * fps + 0.1 / max(now - last, 1e-6) if fps else 1 / max(now - last, 1e-6)
    last = now
    label = hand.label if hand else "no hand"
    if label != last_label:          # print only when the label changes
        print(label)
        last_label = label
    preview.draw(frame, hand, "", "not used in this test", False, fps, "")
    if not preview.show("Recognition test", frame):
        break
cam.release()
rec.close()
