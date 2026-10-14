"""Stage 4 - MQTT only. Connects with the .env settings and publishes one test message.
No camera needed. Have the phone app (or the broker's web client) subscribed first."""
import _path  # noqa: F401
import logging
import time

from config import load_broker_settings, load_config
from messaging import MqttPublisher, build_payload

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

cfg = load_config()
pub = MqttPublisher(cfg["mqtt"], load_broker_settings())

deadline = time.monotonic() + 15
while not pub.connected and time.monotonic() < deadline:
    time.sleep(0.2)

if not pub.connected:
    print(f"FAILED to connect within 15 s. Status: {pub.status}")
else:
    ok = pub.publish(build_payload("Thumb_Up", cfg))
    time.sleep(2)   # give the background thread time to deliver it
    print("Published test message to", cfg["mqtt"]["topic"] if ok else "FAILED to publish")
pub.close()
