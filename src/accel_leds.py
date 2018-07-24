import analogio
import board
import digitalio
import simpleio
import time

import neopixel

NLEDS = 40
MIN_BRIGHT = 0.1
MAX_BRIGHT = 0.3
COLOR_STEP_MULT = 1.0

class Button(object):
    def __init__(self, pin):
        self._but = digitalio.DigitalInOut(pin)
        self._but.direction = digitalio.Direction.INPUT
        self._but.pull = digitalio.Pull.UP
        self._prev_is_pressed = self._is_pressed()

    def _is_pressed(self):
        # TODO: why does this need inverting?
        return not self._but.value

    # This only returns true if button is pressed and wasn't pressed the last
    # time get_press was called.
    def get_press(self):
        prev_pressed = self._prev_is_pressed
        cur_pressed = self._is_pressed()
        self._prev_is_pressed = cur_pressed
        return cur_pressed and not prev_pressed

def intavg(x, y):
    return int((x + y) / 2)

def avgrgb(rgb1, rgb2):
    (r1,g1,b1), (r2,g2,b2) = (rgb1, rgb2)
    return (intavg(r1, r2),
            intavg(g1, g2),
            intavg(b1, b2))

def smooth(xs):
    ys = []
    for i in range(len(xs)):
        ys.append(xs[i])
        if i != len(xs) - 1:
            ys.append(avgrgb(xs[i], xs[i+1]))
        else:
            ys.append(avgrgb(xs[i], xs[0]))
    return ys

def call_n_times(f, x, n):
    if n == 0:
        return x
    return call_n_times(f, f(x), n-1)

def smoothify(n, xs):
    return call_n_times(smooth, xs, n)

def accel_value(axis):
    val = axis.value / 65535
    val -= 0.5  # Shift values to true center (0.5).
    return val * 3.0  # Convert to gravities.

RGB = smoothify(7, [(255, 0, 0),
                    (0, 255, 0),
                    (0, 0, 255)])
GREEN_BLUE = smoothify(5, [(0, 130, 60),
                           (0, 50, 100)])
VIOLET = smoothify(4, [(100, 0, 125),
                       (50, 0, 90),
                       (90, 0, 50)])
ORANGE_PURPLE = smoothify(5, [(150, 50, 0),
                              (125, 0, 125)])
PALETTES = [RGB, GREEN_BLUE, VIOLET, ORANGE_PURPLE]
PALETTE_INDEX = 0

LAST_ACCEL_VAL = (0, 0, 0)
AVG_ACCEL_CHG = 0
EWMA_WEIGHT = 0.05  # for new points

palette_but = Button(board.D11)

## setup LEDs and smoothed color array

board_led = simpleio.DigitalOut(board.D13)

# on-board metro neopixel
metro_neo = None
try:
    metro_neo = neopixel.NeoPixel(board.NEOPIXEL, 1)
except AttributeError:
    pass
if metro_neo:
    metro_neo.brightness = 0.01

neos = neopixel.NeoPixel(board.D12, NLEDS)
neos.brightness = .1

## setup accelerometer

x_axis = analogio.AnalogIn(board.A0)
y_axis = analogio.AnalogIn(board.A1)
z_axis = analogio.AnalogIn(board.A2)

def get_new_accel_point():
    return accel_value(x_axis), accel_value(y_axis), accel_value(z_axis)

def squared_dist(p1, p2):
    (x1, y1, z1), (x2, y2, z2) = p1, p2
    return (x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2

def get_accel_change():
    global LAST_ACCEL_VAL, AVG_ACCEL_CHG
    last = LAST_ACCEL_VAL
    cur = get_new_accel_point()
    # Increase by 30x, limit to 5.0
    raw = squared_dist(last, cur)
    move = min(raw * 30, 5)
    AVG_ACCEL_CHG = EWMA_WEIGHT * move + (1-EWMA_WEIGHT) * AVG_ACCEL_CHG
    LAST_ACCEL_VAL = cur
    return raw, move, AVG_ACCEL_CHG


board_led.value = True

i = 0
while True:
    if palette_but.get_press():
        PALETTE_INDEX = (PALETTE_INDEX + 1) % len(PALETTES)
    palette = PALETTES[PALETTE_INDEX]

    raw, cooked, baked = get_accel_change()
    scaled = min(MAX_BRIGHT, max(MIN_BRIGHT, baked))
    print('({:.3f}, {:.3f}, {:.3f}, {:.3f})'.format(raw, cooked, baked, scaled))

    neos.brightness = scaled

    # TODO: hm, does it make sense?
    step = max(2, int(len(palette) / NLEDS * 0.1 * COLOR_STEP_MULT))
    # TODO: tweak.
    step *= int(baked * 20)

    i = (i + step) % len(palette)
    for j in range(NLEDS):
        neos[j] = palette[(i + j) % len(palette)]
    if metro_neo:
        metro_neo[0] = COLOR_ARRAY[i]
    board_led.value = not board_led.value
