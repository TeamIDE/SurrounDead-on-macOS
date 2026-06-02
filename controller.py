#!/usr/bin/env python3
"""PS4 DS4 → keyboard mapper via direct HID"""
import os, sys, time, threading
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

import hid
import Quartz
from pynput.keyboard import Controller, Key
from pynput.mouse import Button as MouseButton

VENDOR  = 0x054C
PRODUCT = 0x09CC  # DS4 v2 Bluetooth

keyboard = Controller()

# ── Quartz mouse helpers ──────────────────────────────────────────────────────
_display = Quartz.CGMainDisplayID()
screen_w = float(Quartz.CGDisplayPixelsWide(_display))
screen_h = float(Quartz.CGDisplayPixelsHigh(_display))
_cx = screen_w / 2
_cy = screen_h / 2

def _quartz_move(dx_int, dy_int):
    global _cx, _cy
    _cx = max(0.0, min(screen_w - 1, _cx + dx_int))
    _cy = max(0.0, min(screen_h - 1, _cy + dy_int))
    pos = Quartz.CGPoint(_cx, _cy)
    ev  = Quartz.CGEventCreateMouseEvent(
            None, Quartz.kCGEventMouseMoved, pos, Quartz.kCGMouseButtonLeft)
    Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventDeltaX, dx_int)
    Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventDeltaY, dy_int)
    Quartz.CGEventPost(Quartz.kCGSessionEventTap, ev)

def send(key, down):
    if key == MouseButton.left:
        etype = Quartz.kCGEventLeftMouseDown if down else Quartz.kCGEventLeftMouseUp
        ev = Quartz.CGEventCreateMouseEvent(
               None, etype, Quartz.CGPoint(_cx, _cy), Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGSessionEventTap, ev)
    elif key == MouseButton.right:
        etype = Quartz.kCGEventRightMouseDown if down else Quartz.kCGEventRightMouseUp
        ev = Quartz.CGEventCreateMouseEvent(
               None, etype, Quartz.CGPoint(_cx, _cy), Quartz.kCGMouseButtonRight)
        Quartz.CGEventPost(Quartz.kCGSessionEventTap, ev)
    else:
        if down: keyboard.press(key)
        else:    keyboard.release(key)

# ── Mouse thread: fixed 60 Hz, decoupled from HID read rate ──────────────────
MOUSE_SPEED  = 1200   # pixels / second at full deflection
DEADZONE     = 0.15
MOUSE_HZ     = 60
MOUSE_INTERVAL = 1.0 / MOUSE_HZ

_stick_mx  = 0.0
_stick_my  = 0.0
_stick_lock = threading.Lock()

def apply_deadzone(v):
    if abs(v) < DEADZONE:
        return 0.0
    sign = 1 if v > 0 else -1
    return sign * ((abs(v) - DEADZONE) / (1.0 - DEADZONE)) ** 1.5

def mouse_thread():
    acc_x = 0.0
    acc_y = 0.0
    while True:
        t0 = time.monotonic()

        with _stick_lock:
            mx = _stick_mx
            my = _stick_my

        if mx != 0.0 or my != 0.0:
            acc_x += mx * MOUSE_SPEED * MOUSE_INTERVAL
            acc_y += my * MOUSE_SPEED * MOUSE_INTERVAL
            dx = int(acc_x)
            dy = int(acc_y)
            acc_x -= dx
            acc_y -= dy
            if dx != 0 or dy != 0:
                _quartz_move(dx, dy)
        else:
            acc_x = 0.0
            acc_y = 0.0

        elapsed = time.monotonic() - t0
        sleep_t = MOUSE_INTERVAL - elapsed
        if sleep_t > 0:
            time.sleep(sleep_t)

threading.Thread(target=mouse_thread, daemon=True).start()

# ── Controller setup ──────────────────────────────────────────────────────────
print("Looking for PS4 controller...", flush=True)
try:
    dev = hid.Device(VENDOR, PRODUCT)
    dev.nonblocking = False
    print(f"Connected: {dev.product}", flush=True)
    print("Active — switch to game window.", flush=True)
except Exception as e:
    print(f"Could not open controller: {e}", flush=True)
    sys.exit(1)

DPAD = {0: 'up', 1: 'up_right', 2: 'right', 3: 'down_right',
        4: 'down', 5: 'down_left', 6: 'left', 7: 'up_left', 8: 'none'}

prev           = {}
axis_keys      = {'left': False, 'right': False, 'up': False, 'down': False}
AXIS_PRESS   = 50   # threshold to engage key
AXIS_RELEASE = 25   # threshold to release (hysteresis band)

l1_last_press        = 0.0
l1_double_tap_window = 0.35
l1_current_key       = None

# ── Main HID loop ─────────────────────────────────────────────────────────────
while True:
    data = dev.read(64, 8)
    if not data or len(data) < 10:
        continue

    # Left stick → WASD (hysteresis: harder to press than to release)
    lx, ly = data[1], data[2]
    stick_map = {'left': 'a', 'right': 'd', 'up': 'w', 'down': 's'}
    for d in ['left', 'right', 'up', 'down']:
        if d == 'left':  raw =  128 - lx
        elif d == 'right': raw = lx - 128
        elif d == 'up':    raw = 128 - ly
        else:              raw = ly - 128
        was = axis_keys[d]
        if not was and raw >  AXIS_PRESS:    axis_keys[d] = True
        elif was and raw < AXIS_RELEASE:     axis_keys[d] = False
        if axis_keys[d] != was:
            send(stick_map[d], axis_keys[d])
            if axis_keys[d]: print(f"Stick {d}", flush=True)

    # Right stick → update shared state (mouse thread does the moving)
    rx, ry = data[3], data[4]
    with _stick_lock:
        _stick_mx = apply_deadzone((rx - 128) / 128)
        _stick_my = apply_deadzone((ry - 128) / 128)

    # D-pad → WASD
    b5 = data[5]
    dpad_dir = DPAD.get(b5 & 0x0F, 'none')
    for d in ['up', 'down', 'left', 'right']:
        active = d in dpad_dir
        if active != prev.get(f'dpad_{d}', False):
            prev[f'dpad_{d}'] = active
            send({'up': 'w', 'down': 's', 'left': 'a', 'right': 'd'}[d], active)
            if active: print(f"DPad {d}", flush=True)

    # Face + shoulder buttons
    btn5 = {
        'square':   bool(b5 & 0x10),
        'cross':    bool(b5 & 0x20),
        'circle':   bool(b5 & 0x40),
        'triangle': bool(b5 & 0x80),
    }
    b6 = data[6]
    btn6 = {
        'L1': bool(b6 & 0x01), 'R1': bool(b6 & 0x02),
        'L2': bool(b6 & 0x04), 'R2': bool(b6 & 0x08),
        'share':   bool(b6 & 0x10), 'options': bool(b6 & 0x20),
        'L3':      bool(b6 & 0x40), 'R3':      bool(b6 & 0x80),
    }

    btn_key_map = {
        'cross':    'f',               'circle':  Key.space,
        'square':   'j',               'triangle': Key.tab,
        'L2':       'z',               'R2':       MouseButton.left,
        'options':  Key.esc,           'share':    Key.enter,
        'L3':       Key.ctrl_l,        'R3':       'v',
    }

    for name, state in {**btn5, **btn6}.items():
        if state != prev.get(name, False):
            prev[name] = state

            if name == 'L1':
                if state:
                    now = time.time()
                    if now - l1_last_press < l1_double_tap_window:
                        l1_current_key = Key.ctrl_l
                        print("L1 double-tap → Ctrl", flush=True)
                    else:
                        l1_current_key = Key.shift_l
                        print("L1 hold → Shift", flush=True)
                    l1_last_press = now
                    keyboard.press(l1_current_key)
                else:
                    if l1_current_key:
                        keyboard.release(l1_current_key)
                        l1_current_key = None
                continue

            if name == 'R1':
                send(MouseButton.right, state)
                if state: print("Button R1 → right-click", flush=True)
                continue

            if name in btn_key_map:
                send(btn_key_map[name], state)
                if state: print(f"Button {name} → {btn_key_map[name]}", flush=True)
