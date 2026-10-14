"""MQTT publishing over TLS with automatic reconnect (paho-mqtt 2.x)."""

import json
import logging
from datetime import datetime

import paho.mqtt.client as mqtt

log = logging.getLogger("mqtt")


def build_payload(event, cfg):
    """Return the JSON text for one event, e.g.
    {"gesture": "thumbs_up", "message": "Okay", "timestamp": "2026-10-09T14:32:05+05:30"}
    """
    now = datetime.now().astimezone()   # local time, with UTC offset
    fmt = cfg["payload"]["time_format"]
    stamp = now.isoformat(timespec="seconds") if fmt == "iso" else now.strftime(fmt)
    return json.dumps({
        "gesture": cfg["payload_names"].get(event, event.lower()),
        "message": cfg["messages"][event],
        cfg["payload"]["time_key"]: stamp,
    })


class MqttPublisher:
    def __init__(self, mqtt_cfg, broker):
        self.topic = mqtt_cfg["topic"]
        self.qos = int(mqtt_cfg["qos"])
        self.status = "connecting"     # shown in the preview window
        self.connected = False

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=mqtt_cfg["client_id"],
        )
        self._client.username_pw_set(broker["username"], broker["password"])
        # ca_certs=None -> trust the operating system's certificate store.
        self._client.tls_set(ca_certs=broker["ca_file"])
        # After a drop, retry after 1 s, then 2 s, 4 s ... up to the maximum.
        self._client.reconnect_delay_set(
            min_delay=int(mqtt_cfg["reconnect_min_seconds"]),
            max_delay=int(mqtt_cfg["reconnect_max_seconds"]),
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_connect_fail = self._on_connect_fail
        self._client.enable_logger(log)   # paho's own warnings/errors go to the same log
        self._closing = False

        # connect_async + loop_start: the network runs in a background thread,
        # so a slow or missing internet connection never freezes the camera loop.
        # The thread also keeps retrying if the very first connection fails.
        self._client.connect_async(broker["host"], broker["port"],
                                   keepalive=int(mqtt_cfg["keepalive_seconds"]))
        self._client.loop_start()

    # Callback signatures are the paho-mqtt "VERSION2" ones.
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self.connected = False
            self.status = f"refused: {reason_code}"
            log.error("Broker refused the connection: %s", reason_code)
        else:
            self.connected = True
            self.status = "connected"
            log.info("Connected to broker")

    def _on_connect_fail(self, client, userdata):
        # Called when the broker could not be reached at all (no internet,
        # wrong hostname, TLS certificate rejected). paho keeps retrying.
        self.connected = False
        if self.status != "cannot reach broker - retrying":   # log once, not on every retry
            log.warning("Cannot reach broker (no internet, wrong MQTT_HOST, "
                        "or TLS certificate rejected); retrying")
        self.status = "cannot reach broker - retrying"

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.connected = False
        if self._closing:
            self.status = "closed"
            return
        self.status = "offline - reconnecting"
        log.warning("Disconnected (%s); reconnecting automatically", reason_code)

    def publish(self, payload):
        """Send one message. Returns True if it was handed to the broker connection.

        While offline the message is DROPPED on purpose (not queued): a "Stop"
        that arrives minutes late would be misleading.
        """
        if not self.connected:
            log.warning("Offline - dropped: %s", payload)
            return False
        info = self._client.publish(self.topic, payload, qos=self.qos, retain=False)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            log.warning("Publish failed (rc=%s): %s", info.rc, payload)
            return False
        log.info("Sent: %s", payload)
        return True

    def close(self):
        self._closing = True
        self._client.disconnect()
        self._client.loop_stop()
