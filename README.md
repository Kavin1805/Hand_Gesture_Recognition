# Hand gestures to phone over MQTT

A webcam watches one hand. A pretrained MediaPipe model recognises the gesture on the
computer itself, and a short JSON message goes over MQTT (TLS) to a cloud broker. An
Android phone on any other network subscribes and shows the message.

Stage 1 runs on a Windows laptop. Stage 2 moves the same folder to a Raspberry Pi 5.
The Python code is identical on both; only the install commands differ.

| Gesture | Message |
|---|---|
| Thumbs up, held 1 s | Okay |
| Thumbs down, held 1 s | Not Okay |
| Open palm, held still 1.5 s | Stop |
| Closed fist, held 1 s | SOS |
| Open palm waving side to side | Hi |

## Read this first: what was and was not tested

I wrote and checked this in a Linux workspace with no camera, no Windows and no Pi.

**Tested here**

- `tests/test_logic.py`: 16 simulated scenarios for hold time, cooldown, Stop, wave and
  their combinations all pass.
- `messaging.py` against a throwaway local TLS broker: connect, publish at QoS 1, receive
  on a second client, drop while the broker is down, automatic reconnect, publish again.
- Every MediaPipe, OpenCV and paho-mqtt name used in the code exists in the installed
  versions (mediapipe 1.1.0, opencv-contrib-python 5.0.0.93, paho-mqtt 2.1.0, Python 3.13).
- The overlay drawing, with made-up landmarks.

**Not tested: you are the first to run these**

- The gesture model on real camera frames. The model download was blocked in my
  workspace, so `recognition.py` has never processed an image. The API calls are
  verified to exist; the behaviour is not.
- Anything on Windows or on a Raspberry Pi, including the camera, the preview window,
  the frame rate and the run-at-boot steps.
- EMQX Cloud and the IoT MQTT Panel app. Those sections come from the vendors'
  documentation, not from my using them. Button names may differ from what you see.

Section 12 lists every assumption and every item to check in official documentation.

## 1. One change from your brief: the broker

Your brief named the HiveMQ Cloud free Serverless plan. HiveMQ's documentation now says
that plan is retired on 2026-12-31 and that new Serverless clusters can no longer be
created. You chose EMQX Cloud Serverless instead, so this guide uses it. Nothing in the
code is specific to EMQX: host, port, username and password are in `.env`, so any broker
that offers MQTT over TLS with a username and password will work.

## 2. Architecture

```
 Laptop or Raspberry Pi 5 (everything in this box runs locally)
+--------------------------------------------------------------------+
|  USB webcam                                                        |
|      |  frames (640x480)                                           |
|      v                                                             |
|  capture.py                                                        |
|      v                                                             |
|  recognition.py  MediaPipe Gesture Recognizer (pretrained)         |
|      |  gesture label + 21 hand landmarks                          |
|      v                                                             |
|  debounce.py  hold 1 s / still 1.5 s / cooldown 5 s                |
|      ^-- wave_detector.py  direction changes of the hand centre    |
|      |  event: Thumb_Up, Open_Palm, Wave ...                       |
|      v                                                             |
|  messaging.py  JSON payload, QoS 1 ----------.     preview.py      |
|                                              |     window on the   |
+----------------------------------------------|---- monitor --------+
                                               |
                          MQTT over TLS, port 8883 (internet)
                                               v
                                  EMQX Cloud Serverless broker
                                               |
                          MQTT over TLS, port 8883 (internet)
                                               v
                          Android phone, IoT MQTT Panel app
                          subscribed to gestures/pi5/events
```

Both devices make outgoing connections to the broker, so no port forwarding or public
address is needed on either network.

Files:

| File | Job |
|---|---|
| `config.yaml` | Gesture mapping, thresholds, MQTT topic and QoS |
| `.env` | Broker address, username, password (you create it from `.env.example`) |
| `config.py` | Loads the two files above |
| `capture.py` | Opens the camera, returns frames |
| `recognition.py` | Runs the pretrained model, returns label and landmarks |
| `wave_detector.py` | Detects side-to-side motion |
| `debounce.py` | Hold time, stillness, cooldown, Stop versus Hi |
| `messaging.py` | MQTT connection, reconnect, publish |
| `preview.py` | Live window |
| `main.py` | The loop that ties it together |
| `tests/` | One script per test stage |

The wave module is called `wave_detector.py`, not `wave.py`, on purpose: Python has a
built-in module named `wave`, and a file with that name would hide it.

## 3. Bill of materials

Stage 1, laptop:

- Your Windows laptop (i7, 16 GB) with its built-in webcam, or a USB webcam
- Android phone with internet access
- Internet access for the laptop

Stage 2, Raspberry Pi:

- Raspberry Pi 5, 8 GB
- Official 27 W USB-C power supply
- microSD card, 32 GB suggested, with Raspberry Pi OS (64-bit) with desktop
- USB webcam (a standard UVC webcam)
- Monitor, micro-HDMI to HDMI cable, keyboard and mouse
- Active cooler or a case with a fan. This is my suggestion because the program keeps
  the CPU busy continuously; I have not measured temperatures.

Software and services, all free: Python 3, MediaPipe, OpenCV, paho-mqtt, python-dotenv,
PyYAML, EMQX Cloud Serverless (free monthly quota), IoT MQTT Panel (free version).

## 4. Install on the Windows laptop

1. Install 64-bit Python from python.org if you do not have it. MediaPipe 1.1.0 lists
   Python 3.9 to 3.14 as supported. Tick "Add python.exe to PATH" in the installer.
2. Unzip the project, for example to `C:\Users\<you>\gesture_mqtt`.
3. Open PowerShell in that folder and run:

```powershell
python --version
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python download_model.py
copy .env.example .env
```

If PowerShell refuses to run `Activate.ps1` because scripts are disabled, either run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first in that same window,
or use Command Prompt and run `.venv\Scripts\activate.bat` instead.

Do not `pip install opencv-python` as well. MediaPipe installs `opencv-contrib-python`
itself, and two OpenCV packages in one environment conflict.

4. Check the logic before touching any hardware:

```powershell
python tests\test_logic.py
```

It should end with `ALL PASS`.

## 5. Create the EMQX Cloud broker and credentials

These steps follow the EMQX Cloud documentation as of 2026-10-09. I have not clicked
through them myself.

1. Go to the EMQX Cloud site and sign up. An EMQX blog post from 2023 says no credit
   card is required; confirm that on the sign-up page.
2. Log in to the console. If asked, create a project.
3. Click **New Deployment**. In **Choose Plan** select **Serverless**.
4. Leave **Spend Limit** at `0`. The pricing page says a limit of 0 means the deployment
   can only use the free quota, so it cannot run up a bill.
5. Enter a **Deployment Name**, accept the usage terms, click **Deploy** and wait until
   it is running.
6. Open the deployment. On **Overview**, the **Connection Information** section shows
   the **Address** (this is your hostname), the **Ports** (8883 for MQTT over TLS) and a
   **CA Certificate** download.
7. In the left menu open **Access Control**, then **Authentication**. Click **+ Add**,
   enter a username and a password, click **Confirm**. Create two: one for the
   publisher, for example `gesture-pi`, and one for the phone, for example `phone`.
8. Edit `.env` in the project folder:

```
MQTT_HOST=<the Address from step 6>
MQTT_PORT=8883
MQTT_USERNAME=gesture-pi
MQTT_PASSWORD=<its password>
MQTT_CA_FILE=
```

Things I could not confirm, so check them in the console:

- Whether a new deployment lets every authenticated user publish and subscribe to every
  topic by default. If the test in section 9 connects but the phone receives nothing,
  look at **Access Control**, then **Authorization**.
- Whether the server certificate chains to a public certificate authority. Start with
  `MQTT_CA_FILE` empty. If the connection fails, download the CA certificate from step 6,
  save it as `certs\emqxsl-ca.crt` in the project, and set
  `MQTT_CA_FILE=certs/emqxsl-ca.crt`.

Free quota, from the EMQX pricing page: 1 million session minutes and 1 GB of traffic
per month. Two clients connected all day, every day, use about 89,000 session minutes in
a 31-day month, and each message is roughly 100 bytes, so this project stays far inside
it. The documentation also says a deployment with no client connections for 30 days in a
row is stopped and can be re-enabled in the console.

## 6. MQTT details

- **Topic:** `gestures/pi5/events`
- **Payload:** JSON text, for example
  `{"gesture": "thumbs_up", "message": "Okay", "timestamp": "2026-10-09T14:32:05+05:30"}`
- **QoS 1** (at least once). QoS 0 can lose a message with no retry, and a lost gesture
  is the failure that matters here. QoS 2 adds a second round trip to prevent duplicates,
  and a rare duplicate "Okay" on the phone does no harm. Subscribe on the phone with
  QoS 1 too, because the broker delivers at the lower of the two levels.
- **Retain:** off. A retained message would show an old gesture each time the phone
  connects.

Your brief used `timestamp` in instruction 9 and `time` with `14:32:05` in the example.
I followed instruction 9. To match the example instead, set in `config.yaml`:

```yaml
payload:
  time_key: time
  time_format: "%H:%M:%S"
```

## 7. How the logic works

**Static gestures.** The model gives one label per frame. A label must stay the same for
`hold_seconds` (1.0) before a message is sent. A dropout shorter than
`flicker_tolerance_seconds` (0.25) does not restart the timer, because the model
sometimes loses a label for a frame or two.

**Cooldown.** The same gesture is not sent again within `cooldown_seconds` (5.0), even if
you release it and show it again. Different gestures do not block each other.

**Wave.** Only the horizontal position of the hand centre (the average of the 21
landmarks) is used.

1. Follow the hand in its current direction and remember the furthest point reached.
2. When the hand comes back from that point by more than `min_swing` palm lengths, count
   one direction change and start following the new direction.
3. Two direction changes (`min_direction_changes`) inside `window_seconds` (1.5) is a wave.

Small trembling never travels `min_swing` back, so it is ignored. A hand moving across
the frame once has no direction change, so it is not a wave. Distances are measured in
palm lengths (wrist to middle knuckle), so the thresholds do not depend on how far the
hand is from the camera.

**Stop versus Hi.** While the open palm is waving, Stop is never sent. Stop needs the
palm to stay within `still_tolerance` palm lengths of where it came to rest for
`stop_hold_seconds` (1.5). Any larger movement restarts that timer.

**Motion blur.** A fast-moving hand is blurred and the model may answer "None" while
still tracking the hand. For up to `blur_tolerance_seconds` (0.5) this is still treated
as an open palm, so the wave is not interrupted. This is my addition; it was not in your
brief.

**Three choices I made because they were still open.** Each is one line in `config.yaml`.

| Question | What the code does | To change it |
|---|---|---|
| Gesture held longer than 5 s | Resends every 5 s while held | `repeat_while_held: false` sends once per hold |
| Wave, then palm held still | Sends Hi, then Stop about 1.5 s after the hand stops | not configurable |
| Stop sent, then waving starts | Sends Hi as soon as the wave is detected | not configurable |

**Offline.** `messaging.py` runs the network in a background thread, so the camera loop
never waits for the internet. After a drop it retries after 1 s, then with growing
delays up to 30 s, with no limit on attempts. A gesture detected while offline is
**dropped, not queued**: the preview shows "NOT sent - offline" and the log records it.
I chose this because a "Stop" delivered minutes late would be misleading. One edge
case I am not certain about: a message handed to the connection at the instant the link
fails may still be delivered by paho-mqtt after reconnecting.

## 8. Phone setup: IoT MQTT Panel

I could not open the app's own user guide, so the field names below come from a
third-party walkthrough and from what I recall of the app. Treat the names as
approximate and tell me if a screen looks different.

1. Install **IoT MQTT Panel** (developer Rahul Kundu) from the Play Store. There is a
   free version and a paid "Pro" version; the free one is enough.
2. Open it and tap **Setup a Connection**.
3. Fill in:
   - **Connection name:** anything, for example `Gestures`
   - **Client ID:** `phone-1`. It must differ from the publisher's `gesture-publisher`.
     Two clients with the same ID keep disconnecting each other.
   - **Broker address:** the EMQX Address, with no `mqtts://` in front
   - **Port:** `8883`
   - **Network protocol:** the TCP option with SSL (shown as TCP-SSL in the walkthrough)
4. Add a dashboard when the form asks for one, for example `Main`.
5. Open **Additional options** and enter the phone's **Username** and **Password** from
   section 5.
6. Tap **Create**, then tap the connection to connect.
7. On the dashboard tap **+** and choose the **Text Log** panel.
   - **Panel name:** `Gestures`
   - **Topic:** `gestures/pi5/events`
   - **QoS:** 1
   - Leave any JSON option off to see the whole payload. If the panel offers a JSON path
     field and you want only the text, try `$.message`. I am not certain of that
     field's exact name or syntax in the current app version.
8. Save. Messages appear while the app is open and connected.

**Must a CA certificate be supplied in the app?** I cannot confirm this. If the broker's
certificate chains to a public authority that Android already trusts, an app normally
needs none. EMQX offers a CA certificate download for clients that need it. Try without
one first; if the app will not connect on 8883 while the laptop does, look in the app's
SSL settings for a place to load the CA file from section 5.

## 9. Test procedure

Run each stage only after the one before it passes. Activate the environment first
(`.venv\Scripts\Activate.ps1` on Windows, `source .venv/bin/activate` on the Pi). On the
Pi use `/` in the paths.

| Stage | Command | Pass when |
|---|---|---|
| 0. Logic | `python tests\test_logic.py` | Ends with `ALL PASS` |
| 1. Camera | `python tests\test_camera.py` | Window shows the picture, size and fps. `q` quits |
| 2. Recognition | `python tests\test_recognition.py` | Skeleton drawn on your hand; label changes between Thumb_Up, Thumb_Down, Open_Palm, Closed_Fist |
| 3. Wave and debounce | `python tests\test_wave.py` | Console prints each event once, following the rules in section 7 |
| 4. MQTT | `python tests\test_mqtt.py` | Prints `Published test message`, and the phone shows it |
| 5. End to end | `python main.py` | Phone shows the right message for each gesture |

For stage 3, check these in order:

1. Thumbs up for under 1 s, then remove: nothing.
2. Thumbs up for 1 s: `Thumb_Up -> Okay`. Keep holding: nothing more for 5 s.
3. Fist for 1 s: `Closed_Fist -> SOS`.
4. Open palm held still: `Open_Palm -> Stop` after 1.5 s.
5. Open palm waving: `Wave -> Hi`, and no Stop.
6. A two-finger "victory" sign: nothing.

For stage 4, open the phone app first. If you do not have the phone ready, the EMQX
console has a browser-based test client (I believe it is labelled Online Test; check the
left menu) that can subscribe to the topic instead.

For stage 5, also pull the network cable or turn off Wi-Fi for 20 seconds: the preview
line should turn red, gestures should show "NOT sent - offline", and it should return to
"connected" on its own.

`python main.py --no-mqtt` runs everything except the network and prints what it would send.

## 10. Moving to the Raspberry Pi 5

Before you start, send me the output of these three commands from the Pi, so I can
confirm the steps below match your system:

```bash
cat /etc/os-release
python3 --version
echo $XDG_SESSION_TYPE
```

### Install

Copy the project folder to the Pi, for example to `/home/<user>/gesture_mqtt`, including
your `.env`. Then:

```bash
cd ~/gesture_mqtt
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python download_model.py
python tests/test_logic.py
```

Raspberry Pi OS only allows `pip install` inside a virtual environment, which is what
these commands use. MediaPipe 1.1.0 publishes a wheel for 64-bit ARM Linux
(`manylinux_2_28_aarch64`), so I expect it to install on the current Raspberry Pi OS,
which is based on Debian Trixie. I have not run it there.

In `config.yaml` you may set `backend: v4l2`. Then repeat the test stages in section 9.

### Frame rate

Your target is 10 fps. Google lists about 17 ms per frame for this model on a Pixel 6
phone CPU. I expect a Pi 5 to exceed 10 fps at 640x480, but I have not measured it. The
preview shows the real figure. If it is too low, set `width: 320` and `height: 240`.

### Run at boot with the preview on the monitor

The program must start inside the desktop session, otherwise it has no screen to draw
on. That is why this uses a desktop autostart entry and not a systemd system service.

1. Make the Pi log in to the desktop automatically: `sudo raspi-config`, then System
   Options, then the boot and auto-login entry, and choose the desktop with auto-login.
   Menu wording varies between releases.
2. Make the start script executable: `chmod +x ~/gesture_mqtt/start.sh`
3. Create the autostart entry:

```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/gesture-mqtt.desktop
```

Contents (replace `<user>`):

```ini
[Desktop Entry]
Type=Application
Name=Gesture MQTT
Exec=/home/<user>/gesture_mqtt/start.sh
```

4. Reboot. The window should appear about 10 seconds after the desktop. Output goes to
   `~/gesture_mqtt/gesture.log`.

I am fairly confident, but not certain, that the current Raspberry Pi desktop runs
entries in `~/.config/autostart`. If nothing starts, the alternative on the labwc
desktop is a file `~/.config/labwc/autostart` containing the line
`/home/<user>/gesture_mqtt/start.sh &`. Check the Raspberry Pi documentation for your
release before relying on either.

On the Windows laptop, the equivalent is: press Win+R, type `shell:startup`, and put a
shortcut to `start.bat` in the folder that opens.

## 11. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `Could not open camera index 0` | Another program is using the camera (Teams, Zoom, the Camera app). Close it. Try `index: 1`. On Windows try `backend: dshow`. Check Settings, Privacy, Camera allows desktop apps. |
| Camera takes many seconds to open on Windows | Set `backend: dshow`. |
| `Model file not found` | Run `python download_model.py`. If the download fails, get `gesture_recognizer.task` from the MediaPipe Gesture Recognizer page and put it in `models/`. |
| `module 'mediapipe' has no attribute 'solutions'` | You are following an older tutorial. That module is absent in MediaPipe 1.x; this project does not use it. |
| `DLL load failed` when importing mediapipe on Windows | I believe this usually means the Microsoft Visual C++ Redistributable is missing; install the current x64 one from Microsoft. Not verified for 1.1.0. |
| `No matching distribution found for mediapipe` | Python is 32-bit or outside the supported range. Check `python --version` and that it is 64-bit. |
| No window on the Pi, error mentioning Qt or "xcb" | Possibly the OpenCV window backend and Wayland. Try `QT_QPA_PLATFORM=xcb python main.py`. Unverified. |
| Preview says `cannot reach broker - retrying` | No internet, wrong `MQTT_HOST`, port 8883 blocked by the network (common on office or campus Wi-Fi; try a phone hotspot), or the TLS certificate was rejected (set `MQTT_CA_FILE`, section 5). Also check the computer's clock is correct: TLS fails with a wrong date. |
| Preview says `refused: ...` | Wrong username or password, or the credential was not created in this deployment. |
| Connected, then disconnects every few seconds | Two clients share a client ID. Give the phone and the publisher different IDs. |
| Publisher sends, phone shows nothing | Topic differs by a character or a leading `/`; phone not connected; or topic permissions on the broker (section 5). |
| Wave not detected | Wave wider and keep the palm facing the camera. Lower `min_swing` to 0.25. Raise `blur_tolerance_seconds` to 0.8. |
| Hi sent when you only moved your hand | Raise `min_swing` to 0.5 or `min_direction_changes` to 3. |
| Stop never sent | Hand is not steady enough: raise `still_tolerance` to 0.5. |
| Stop sent while waving slowly | Wave faster, or raise `window_seconds` to 2.0. |
| Wrong or flickering labels | Improve lighting, keep the hand 40 to 100 cm from the camera, avoid a bright window behind you. Lower `min_gesture_score` to 0.4 if labels are missed; raise it to 0.6 if wrong ones appear. |
| Low frame rate | Set 320x240 in `config.yaml`. On the Pi, check cooling. |
| Broker stopped working after weeks unused | EMQX stops a deployment with no connections for 30 days. Re-enable it in the console. |

## 12. Assumptions and items to verify

**Assumptions I made**

1. Broker is EMQX Cloud Serverless, as you chose after the HiveMQ plan turned out to be
   closed to new clusters.
2. Laptop runs 64-bit Windows 10 or 11 with a supported 64-bit Python. You did not give
   the Windows or Python version.
3. Capture is 640x480 and the preview is mirrored.
4. The payload time is key `timestamp`, local time in ISO 8601 with UTC offset.
5. A gesture held past the cooldown is sent again every 5 s.
6. For the open palm, the 1.5 s stillness rule replaces the 1 s hold; they do not add up.
7. Model labels other than the four in `config.yaml` are ignored.
8. `num_hands=1`, so the model reports one hand. Which hand it picks when two are
   visible is the model's choice.
9. Gestures detected while offline are dropped, not queued.
10. The cooldown is per gesture, not global.
11. The blur tolerance for waving (section 7) is my addition.

**Verify in official documentation or by testing**

1. **MediaPipe sends usage metrics to Google.** The privacy notice on the MediaPipe PyPI
   page says images are processed on the device and not sent to Google, but that the
   Tasks APIs send performance and utilisation metrics. Your constraint was that only
   MQTT traffic uses the internet. I do not know of a documented way to switch this off
   in Python, and I have not checked whether it happens in practice. Recognition itself
   works with no internet connection as far as I can tell from the design, but confirm
   by running `python main.py --no-mqtt` with the network disconnected.
2. The model download URL. It is the one on the MediaPipe overview page, but my
   workspace could not download from it.
3. Real recognition quality and frame rate, on the laptop and on the Pi.
4. EMQX: card requirement at sign-up, default topic permissions, whether the CA file is
   needed, current free quota, and exact console labels.
5. IoT MQTT Panel: field names, the JSON path option, and whether a CA certificate must
   be loaded.
6. Raspberry Pi OS: Python version shipped, that the MediaPipe wheel installs, the
   autostart method for your desktop, and the `raspi-config` menu wording.
7. The pinned versions in `requirements.txt` were current on 2026-10-09. Newer releases
   may rename things.

## Sources

- [MediaPipe on PyPI](https://pypi.org/project/mediapipe/) (version, Python support, wheels, privacy notice)
- [MediaPipe Gesture Recognizer guide for Python](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer/python)
- [MediaPipe Gesture Recognizer overview](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer) (model URL, latency)
- [HiveMQ Cloud quick start guide](https://docs.hivemq.com/hivemq-cloud/quick-start-guide.html) (Serverless retirement)
- [EMQX Cloud: create a Serverless deployment](https://docs.emqx.com/en/cloud/latest/create/serverless.html)
- [EMQX Cloud: default authentication](https://docs.emqx.com/en/cloud/latest/deployments/default_auth.html)
- [EMQX Cloud pricing](https://docs.emqx.com/en/cloud/latest/price/pricing.html)
- [EMQX blog: forever free serverless MQTT](https://www.emqx.com/en/blog/how-to-get-a-forever-free-serverless-mqtt-service) (2023; no credit card)
- [Bevywise: Android MQTT client setup with IoT MQTT Panel](https://bevywise.com/mqtt-broker/resources/android-mqtt-client.html)
- [Raspberry Pi OS documentation](https://www.raspberrypi.com/documentation/computers/os.html)