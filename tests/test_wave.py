"""Stage 3 - wave and debounce logic with the camera, but no MQTT.
Prints every event the logic would send. q or Esc to quit."""
import _path  # noqa: F401
import time

import preview
from capture import Camera
from config import load_config
from debounce import GestureLogic
from recognition import GestureRecognizer

cfg = load_config()
cam = Camera(cfg["camera"])
rec = GestureRecognizer(cfg["model"])
logic = GestureLogic(cfg)
start = time.monotonic()
last_sent = ""
while True:
    frame = cam.read()
    if frame is None:
        break
    now = time.monotonic()
    hand = rec.process(frame, (now - start) * 1000)
    if hand is None:
        event = logic.update(now, None, hand_visible=False)
    else:
        event = logic.update(now, hand.label, hand.center_x, hand.center_y, hand.size)
    if event:
        last_sent = cfg["messages"][event]
        print(f"{time.strftime('%H:%M:%S')}  {event} -> {last_sent}")
    preview.draw(frame, hand, logic.status, "not used in this test", False, 0, last_sent)
    if not preview.show("Wave / debounce test", frame):
        break
cam.release()
rec.close()
