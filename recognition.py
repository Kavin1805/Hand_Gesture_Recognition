"""Static gesture recognition with the pretrained MediaPipe Gesture Recognizer.

One model call per frame gives both the gesture label and the 21 hand
landmarks, so the wave detector reuses the same landmarks at no extra cost.

Written against mediapipe 1.1.0 (the "tasks" API). Older tutorials that use
"mp.solutions" do not apply: that module is not present in this version.
"""

import math
import os
from dataclasses import dataclass

import cv2
import mediapipe as mp

# Landmark indices (MediaPipe hand model): 0 = wrist, 9 = middle finger knuckle.
WRIST = 0
MIDDLE_MCP = 9


@dataclass
class Hand:
    label: str          # e.g. "Thumb_Up", "Open_Palm", "None"
    score: float        # confidence 0.0 - 1.0
    landmarks: list     # 21 landmarks, each with .x .y in 0..1 of the frame
    center_x: float     # hand centre, in pixels
    center_y: float
    size: float         # palm length (wrist -> middle knuckle), in pixels


class GestureRecognizer:
    def __init__(self, model_cfg):
        model_path = model_cfg["path"]
        if not os.path.isfile(model_path):
            raise FileNotFoundError(
                f"Model file not found: {model_path}\nRun:  python download_model.py"
            )
        options = mp.tasks.vision.GestureRecognizerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=1,   # one hand only: the first one detected
        )
        self._recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)
        self._min_score = float(model_cfg.get("min_gesture_score", 0.5))
        self._last_ts = -1

    def process(self, frame_bgr, timestamp_ms):
        """Run the model on one frame. Returns a Hand, or None if no hand is visible."""
        # VIDEO mode requires timestamps that always increase.
        timestamp_ms = max(int(timestamp_ms), self._last_ts + 1)
        self._last_ts = timestamp_ms

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._recognizer.recognize_for_video(image, timestamp_ms)

        if not result.hand_landmarks:
            return None

        landmarks = result.hand_landmarks[0]
        label, score = "None", 0.0
        if result.gestures and result.gestures[0]:
            top = result.gestures[0][0]
            label, score = top.category_name or "None", float(top.score or 0.0)
        if score < self._min_score:
            label = "None"

        h, w = frame_bgr.shape[:2]
        # Hand centre = average of all 21 points. It moves whether the person
        # waves from the wrist or from the elbow.
        cx = sum(p.x for p in landmarks) / len(landmarks) * w
        cy = sum(p.y for p in landmarks) / len(landmarks) * h
        # Palm length in pixels: used to make motion thresholds independent of
        # how far the hand is from the camera.
        size = math.hypot(
            (landmarks[MIDDLE_MCP].x - landmarks[WRIST].x) * w,
            (landmarks[MIDDLE_MCP].y - landmarks[WRIST].y) * h,
        )
        return Hand(label, score, landmarks, cx, cy, max(size, 1.0))

    def close(self):
        self._recognizer.close()
