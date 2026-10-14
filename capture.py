"""Camera capture with OpenCV."""

import cv2

# config.yaml "backend" value -> OpenCV capture backend
_BACKENDS = {
    "auto": cv2.CAP_ANY,
    "dshow": cv2.CAP_DSHOW,   # Windows DirectShow
    "msmf": cv2.CAP_MSMF,     # Windows Media Foundation
    "v4l2": cv2.CAP_V4L2,     # Linux / Raspberry Pi
}


class Camera:
    def __init__(self, cam_cfg):
        backend = _BACKENDS.get(str(cam_cfg.get("backend", "auto")).lower(), cv2.CAP_ANY)
        self.mirror = bool(cam_cfg.get("mirror", True))
        self.cap = cv2.VideoCapture(int(cam_cfg["index"]), backend)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Could not open camera index {cam_cfg['index']}. "
                "Check it is plugged in and not used by another program."
            )
        # These are requests; a camera may pick the nearest size it supports.
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(cam_cfg["width"]))
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(cam_cfg["height"]))
        # Keep the driver's queue short so we always see a recent frame.
        # Not every backend honours this setting.
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def read(self):
        """Return one BGR frame (numpy array), or None if the read failed."""
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return None
        if self.mirror:
            frame = cv2.flip(frame, 1)
        return frame

    def release(self):
        self.cap.release()
