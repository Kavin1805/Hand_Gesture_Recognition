"""Loads config.yaml (settings) and .env (broker secrets)."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent


def load_config(path=None):
    """Return the settings from config.yaml as a nested dict."""
    path = Path(path) if path else BASE_DIR / "config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # Make the model path absolute so the program works from any folder
    # (this matters when it is started automatically at boot).
    model_path = Path(cfg["model"]["path"])
    if not model_path.is_absolute():
        cfg["model"]["path"] = str(BASE_DIR / model_path)
    return cfg


def load_broker_settings():
    """Return broker host/port/credentials from the .env file.

    Raises SystemExit with a readable message if something is missing.
    """
    load_dotenv(BASE_DIR / ".env")
    missing = [k for k in ("MQTT_HOST", "MQTT_USERNAME", "MQTT_PASSWORD") if not os.getenv(k)]
    if missing:
        raise SystemExit(
            "Missing in .env: " + ", ".join(missing)
            + "\nCopy .env.example to .env and fill in your broker details."
        )
    ca_file = os.getenv("MQTT_CA_FILE", "").strip()
    if ca_file and not Path(ca_file).is_absolute():
        ca_file = str(BASE_DIR / ca_file)
    return {
        "host": os.environ["MQTT_HOST"].strip(),
        "port": int(os.getenv("MQTT_PORT", "8883")),
        "username": os.environ["MQTT_USERNAME"],
        "password": os.environ["MQTT_PASSWORD"],
        "ca_file": ca_file or None,
    }
