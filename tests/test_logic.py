"""Stage 0 - logic check with simulated hand data. No camera, model or network needed.
Run:  python tests/test_logic.py      (prints PASS/FAIL for each example behaviour)"""
import _path  # noqa: F401
import math

from config import load_config
from debounce import GestureLogic

FPS = 15
PALM = 80.0   # simulated palm length in pixels


def run(steps, cfg=None):
    """steps: list of (seconds, label, x_function). Returns [(time, event), ...]."""
    logic = GestureLogic(cfg or load_config())
    events, t = [], 0.0
    for duration, label, xf in steps:
        t_start = t
        for _ in range(int(duration * FPS)):
            if label == "NOHAND":
                e = logic.update(t, None, hand_visible=False)
            else:
                e = logic.update(t, label, xf(t - t_start) if xf else 320.0, 240.0, PALM)
            if e:
                events.append((round(t, 2), e))
            t += 1 / FPS
    return events


def wave_x(t):
    """Hand swinging left-right: 2 full swings per second, 1 palm length each way."""
    return 320.0 + PALM * math.sin(2 * math.pi * 2.0 * t)


def check(name, got, expect):
    names = [e for _, e in got]
    print(("PASS" if names == expect else "FAIL"), "-", name, "->", got)
    return names == expect


results = []
ev = run([(0.9, "Thumb_Up", None), (1.0, "NOHAND", None)])
results.append(check("thumbs up 0.9 s: nothing sent", ev, []))

ev = run([(1.3, "Thumb_Up", None)])
results.append(check("thumbs up 1 s: Okay", ev, ["Thumb_Up"]))
results.append(1.0 <= ev[0][0] <= 1.15)

ev = run([(4.5, "Thumb_Up", None)])
results.append(check("thumbs up held 4.5 s: no repeat inside 5 s", ev, ["Thumb_Up"]))

ev = run([(6.5, "Thumb_Up", None)])
results.append(check("thumbs up held 6.5 s: repeats after cooldown", ev, ["Thumb_Up", "Thumb_Up"]))

cfg = load_config()
cfg["timing"]["repeat_while_held"] = False
ev = run([(12, "Thumb_Up", None)], cfg)
results.append(check("repeat_while_held=false: sent once", ev, ["Thumb_Up"]))

ev = run([(1.3, "Thumb_Up", None), (0.5, "NOHAND", None), (1.5, "Thumb_Up", None)])
results.append(check("release and show again inside 5 s: no resend", ev, ["Thumb_Up"]))

ev = run([(1.2, "Open_Palm", None)])
results.append(check("open palm still 1.2 s: nothing yet", ev, []))

ev = run([(2.0, "Open_Palm", None)])
results.append(check("open palm still 1.5 s: Stop", ev, ["Open_Palm"]))
results.append(1.5 <= ev[0][0] <= 1.65)

ev = run([(4.0, "Open_Palm", wave_x)])
results.append(check("open palm waving 4 s: Hi and never Stop", ev, ["Wave"]))

ev = run([(3.0, "Open_Palm", wave_x), (4.0, "Open_Palm", None)])
results.append(check("wave, then palm held still: Hi then Stop", ev, ["Wave", "Open_Palm"]))

ev = run([(2.0, "Open_Palm", None), (3.0, "Open_Palm", wave_x)])
results.append(check("Stop, then start waving: Stop then Hi", ev, ["Open_Palm", "Wave"]))

ev = run([(1.3, "Closed_Fist", None)])
results.append(check("fist 1 s: SOS", ev, ["Closed_Fist"]))

ev = run([(3.0, "Victory", None), (3.0, "None", None), (3.0, "NOHAND", None)])
results.append(check("unknown gesture / no hand: nothing", ev, []))

ev = run([(3.0, "Open_Palm", lambda t: 100.0 + 150.0 * t)])
results.append(check("open palm sliding one way: no Hi, no Stop", ev, []))

ev = run([(3.0, "Open_Palm", lambda t: 320.0 + 4.0 * math.sin(40 * t))])
results.append(check("open palm with small tremble: Stop, not Hi", ev, ["Open_Palm"]))

ev = run([(0.6, "Thumb_Up", None), (0.13, "None", None), (0.6, "Thumb_Up", None)])
results.append(check("2-frame label dropout does not restart the hold", ev, ["Thumb_Up"]))

print("\nALL PASS" if all(results) else "\nSOME CHECKS FAILED")
