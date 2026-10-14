"""Live preview window: camera picture, hand landmarks, gesture name, MQTT status."""

import cv2
import mediapipe as mp

_draw = mp.tasks.vision.drawing_utils
_CONNECTIONS = mp.tasks.vision.HandLandmarksConnections.HAND_CONNECTIONS

_was_visible = False

GREEN, RED, WHITE, YELLOW = (0, 200, 0), (0, 0, 255), (255, 255, 255), (0, 220, 255)


def _text(frame, text, row, color=WHITE):
    pos = (10, 28 + 28 * row)
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)  # outline
    cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)


def draw(frame, hand, logic_status, mqtt_status, mqtt_connected, fps, last_sent):
    """Draw the overlay onto `frame` (changes the frame in place)."""
    if hand is not None:
        _draw.draw_landmarks(frame, hand.landmarks, _CONNECTIONS)
        _text(frame, f"Gesture: {hand.label} ({hand.score:.2f})  {logic_status}", 0)
    else:
        _text(frame, "Gesture: no hand", 0)
    _text(frame, f"MQTT: {mqtt_status}", 1, GREEN if mqtt_connected else RED)
    _text(frame, f"FPS: {fps:.0f}", 2)
    if last_sent:
        _text(frame, f"Last: {last_sent}", 3, YELLOW)


def show(window_name, frame):
    """Show the frame. Returns False when the user asks to quit (q, Esc, or closing the window)."""
    cv2.imshow(window_name, frame)
    key = cv2.waitKey(1) & 0xFF
    if key in (ord("q"), 27):
        return False
    # Window closed with the mouse -> the property drops below 1. Some window
    # backends never report it at all, so only trust a drop after it was 1 once.
    global _was_visible
    visible = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) >= 1
    if visible:
        _was_visible = True
        return True
    return not _was_visible
