import analogio
import board
import digitalio
import simpleio
import time

try:
    import adafruit_dotstar
except ImportError:
    print('note: failed to import adafruit_dotstar')

import neopixel

NLEDS = 40
MIN_BRIGHT = 0.05
MAX_BRIGHT = 0.8
COLOR_STEP_MULT = 1.0

# when brightness pot is below this level, accelerometer movement quotient is
# used to determine brightness.
ACCEL_BRIGHTNESS_THRESH = 0.1


class Button(object):
    def __init__(self, pin):
        self._but = digitalio.DigitalInOut(pin)
        self._but.direction = digitalio.Direction.INPUT
        self._but.pull = digitalio.Pull.UP
        self._prev_is_pressed = self._is_pressed()

    def _is_pressed(self):
        return not self._but.value

    # This only returns true if button is pressed and wasn't pressed the last
    # time get_press was called.
    def get_press(self):
        prev_pressed = self._prev_is_pressed
        cur_pressed = self._is_pressed()
        self._prev_is_pressed = cur_pressed
        ret =  cur_pressed and not prev_pressed
        print('get_press: {} ({} & !{})'.format(ret, cur_pressed, prev_pressed))
        return ret

class Pot(object):
    def __init__(self, pin):
        self._pot = analogio.AnalogIn(pin)

    def read(self):
        return self._pot.value / 65536


class Accel(object):
    EWMA_WEIGHT = 0.1  # for new points

    def __init__(self, pin_x, pin_y, pin_z):
        self._x = analogio.AnalogIn(pin_x)
        self._y = analogio.AnalogIn(pin_y)
        self._z = analogio.AnalogIn(pin_z)
        self._mq_ewma = 0

    def _read(self):
        def cook(axis):
            # TODO: itsy-bitsy has 12-bit ADCs - is this right?
            val = axis.value / 65536
            val -= 0.5  # Shift values to true center (0.5).
            return val * 3.0  # Convert to gravities.
        return cook(self._x), cook(self._y), cook(self._z)

    def get_movement_quotient(self):
        (x, y, z) = self._read()
        # Remove gravity. Z seems to be 0.30 and not 1. Dunno why.
        z -= 0.3
        mean_accel = (abs(x) + abs(y) + abs(z)) / 3
        # 0.3 mean accel seems high
        movement_quotient = simpleio.map_range(mean_accel, 0.05, 0.15, 0, 1.0)
        self._mq_ewma = (self.EWMA_WEIGHT * movement_quotient
                         + (1-self.EWMA_WEIGHT) * self._mq_ewma)
        return (x, y, z), mean_accel, movement_quotient, self._mq_ewma


def smoothify(n, xs):
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
            next_x = xs[0] if i == len(xs) - 1 else xs[i+1]
            ys.append(avgrgb(xs[i], next_x))
        return ys
    def call_n_times(f, x, n):
        if n == 0:
            return x
        return call_n_times(f, f(x), n-1)
    return call_n_times(smooth, xs, n)


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


## LEDs

def try_get_board_neo():
    try:
        board_neo = neopixel.NeoPixel(board.NEOPIXEL, 1)
    except AttributeError:
        pass
    try:
        board_neo = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
    except (AttributeError, NameError):
        pass

    if board_neo:
        board_neo.brightness = 0.2
        for _ in range(3):
            board_neo[0] = (255, 0, 0)
            time.sleep(.1)
            board_neo[0] = (0, 0, 255)
            time.sleep(.1)
            board_neo[0] = (0, 255, 0)
            time.sleep(.1)
        return board_neo
    return None


board_led = simpleio.DigitalOut(board.D13)
board_led.value = True

neos = neopixel.NeoPixel(board.D12, NLEDS)
neos.brightness = .1

board_neo = try_get_board_neo()

## accel
accel = Accel(board.A0, board.A1, board.A2)

## brightness pot
bright_pot = Pot(board.A4)

## palette button
palette_but = Button(board.D11)


i = 0
while True:
    print()
    if palette_but.get_press():
        for j in range(NLEDS):
            neos[j] = (180, 0, 180) if j % 4 == 0 else (0, 0, 0)
        PALETTE_INDEX = (PALETTE_INDEX + 1) % len(PALETTES)
    palette = PALETTES[PALETTE_INDEX]

    (x,y,z), mean_accel, mq, mq_ewma = accel.get_movement_quotient()
    print('accel: [ ({:.2f}, {:.2f}, {:.2f})\t mean:{:.2f}\t mq:{:.2f}\t mq_ewma:{:.2f} ])'.format(
        x, y, z, mean_accel, mq, mq_ewma))

    bright_val = bright_pot.read()
    bright_source = None
    if bright_val < ACCEL_BRIGHTNESS_THRESH:
        brightness = simpleio.map_range(mq_ewma, 0, 1, MIN_BRIGHT, MAX_BRIGHT)
        bright_source = 'accel'
    else:
        brightness = simpleio.map_range(bright_val, ACCEL_BRIGHTNESS_THRESH, 1,
                                        MIN_BRIGHT, MAX_BRIGHT)
        bright_source = 'pot'
    print('brightpot: [ {:.2f}\t brightness:{:.2f}\t src:{} ]'.format(
        bright_val, brightness, bright_source))
    neos.brightness = brightness

    # TODO: this doesn't make sense.
    step = max(2, int(len(palette) / NLEDS * 0.5 * COLOR_STEP_MULT))
    step *= int(mq_ewma * 10)

    i = (i + step) % len(palette)
    for j in range(NLEDS):
        neos[j] = palette[(i + j) % len(palette)]
    if board_neo:
        print('setting board neo to:', palette[i])
        board_neo[0] = palette[i]
    board_led.value = not board_led.value
