"""Stage 1 - camera only. Shows the picture and the frame rate. q or Esc to quit."""
import _path  # noqa: F401
import time

import cv2

from capture import Camera
from config import load_config

cam = Camera(load_config()["camera"])
count, t0 = 0, time.monotonic()
while True:
    frame = cam.read()
    if frame is None:
        print("No frame from camera")
        break
    count += 1
    fps = count / max(time.monotonic() - t0, 1e-6)
    cv2.putText(frame, f"{frame.shape[1]}x{frame.shape[0]}  {fps:.0f} fps", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.imshow("Camera test", frame)
    if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
        break
cam.release()
cv2.destroyAllWindows()
