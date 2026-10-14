"""Downloads the pretrained MediaPipe gesture model (a few MB) into models/.

URL taken from the MediaPipe Gesture Recognizer overview page ("Models" section).
If the download fails, open that page, download gesture_recognizer.task by hand
and save it as models/gesture_recognizer.task.
"""

import urllib.request
from pathlib import Path

URL = ("https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
       "gesture_recognizer/float16/latest/gesture_recognizer.task")
TARGET = Path(__file__).resolve().parent / "models" / "gesture_recognizer.task"

if __name__ == "__main__":
    TARGET.parent.mkdir(exist_ok=True)
    print("Downloading", URL)
    urllib.request.urlretrieve(URL, TARGET)
    print(f"Saved {TARGET} ({TARGET.stat().st_size / 1e6:.1f} MB)")
