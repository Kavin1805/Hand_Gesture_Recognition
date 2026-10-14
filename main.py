"""Main loop: camera -> gesture model -> wave/debounce logic -> MQTT -> preview.

Run:   python main.py            (q or Esc in the preview window to quit)
       python main.py --no-mqtt  (everything except the network; prints instead of sending)
"""

import argparse
import logging
import time

import preview
from capture import Camera
from config import load_broker_settings, load_config
from debounce import GestureLogic
from messaging import MqttPublisher, build_payload
from recognition import GestureRecognizer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-mqtt", action="store_true", help="do not connect; print messages instead")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    log = logging.getLogger("main")

    cfg = load_config()
    camera = Camera(cfg["camera"])
    recognizer = GestureRecognizer(cfg["model"])
    logic = GestureLogic(cfg)
    publisher = None if args.no_mqtt else MqttPublisher(cfg["mqtt"], load_broker_settings())

    show_preview = bool(cfg["preview"]["show"])
    window = cfg["preview"]["window_name"]
    start = time.monotonic()
    fps, last_frame_time, last_sent = 0.0, start, ""
    failed_reads = 0

    try:
        while True:
            frame = camera.read()
            if frame is None:
                failed_reads += 1
                if failed_reads > 100:
                    raise RuntimeError("Camera stopped delivering frames.")
                time.sleep(0.05)
                continue
            failed_reads = 0

            now = time.monotonic()
            hand = recognizer.process(frame, (now - start) * 1000)

            if hand is None:
                event = logic.update(now, None, hand_visible=False)
            else:
                event = logic.update(now, hand.label, hand.center_x, hand.center_y, hand.size)

            if event:
                payload = build_payload(event, cfg)
                if publisher is None:
                    log.info("Would send: %s", payload)
                    last_sent = cfg["messages"][event]
                elif publisher.publish(payload):
                    last_sent = cfg["messages"][event]
                else:
                    last_sent = cfg["messages"][event] + " (NOT sent - offline)"

            # Smoothed frames-per-second for the overlay.
            dt = now - last_frame_time
            last_frame_time = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps else 1.0 / dt

            if show_preview:
                preview.draw(
                    frame, hand, logic.status,
                    "disabled (--no-mqtt)" if publisher is None else publisher.status,
                    publisher is not None and publisher.connected,
                    fps, last_sent,
                )
                if not preview.show(window, frame):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        camera.release()
        recognizer.close()
        if publisher is not None:
            publisher.close()
        if show_preview:
            import cv2
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
