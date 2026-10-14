#!/bin/bash
# Raspberry Pi: starts the program from the desktop session (used by the autostart entry).
cd "$(dirname "$0")"
sleep 10                      # give the desktop, camera and network time to come up
exec .venv/bin/python main.py >> gesture.log 2>&1
