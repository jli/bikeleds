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

NLEDS = 45
MIN_BRIGHT = 0.05
MAX_BRIGHT = 0.3

DEBUG = 1

# TODO: lower this when pot is properly wired in.
# when brightness pot is below this level, accelerometer movement quotient is
# used to determine brightness.
ACCEL_BRIGHTNESS_THRESH = 0.9

# try to cycle between full color palette in this many seconds
TARGET_PALETTE_CYCLE_SEC = 7

# TODO: gah, this can't be right...
LED_UPDATE_SEC = (
    0.027 if NLEDS >= 100 else
    (0.015 if NLEDS >= 50 else
     (0.013 if NLEDS >= 25 else
      (0.0075 if NLEDS >= 10 else
       0.0055))))
FULL_UPDATE_SEC = LED_UPDATE_SEC * NLEDS

def timestamp():
    return time.monotonic()

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
        if DEBUG >= 2:
            print('but: {}\t[ cur:{}\t prev:{} ]'.format(ret, cur_pressed, prev_pressed))
        return ret

class Pot(object):
    def __init__(self, pin):
        self._pot = analogio.AnalogIn(pin)

    def read(self):
        return self._pot.value / 65536


class Accel(object):
    EWMA_WEIGHT = 0.8  # for new points
    SIZABLE_MOVE_THRESH = 0.01
    IDLE_DELAY = 3

    def __init__(self, pin_x, pin_y, pin_z):
        self._x = analogio.AnalogIn(pin_x)
        self._y = analogio.AnalogIn(pin_y)
        self._z = analogio.AnalogIn(pin_z)
        self._prev_read = (0, 0, 0)
        self._prev_time = 0
        self._last_sizable_move_time = timestamp()
        self._mq_ewma = 0

    def _read(self):
        def cook(axis):
            # TODO: itsy-bitsy has 12-bit ADCs - is this right?
            val = axis.value / 65536
            val -= 0.5  # Shift values to true center (0.5).
            return val * 3.0  # Convert to gravities.
        return cook(self._x), cook(self._y), cook(self._z)

    def is_moving(self):
        def sq_dist(a, b):
            (x1,y1,z1), (x2,y2,z2) = a, b
            return (x2 - x1) ** 2 + (y2-y1) ** 2 + (z2-z1) ** 2
        pread, ptime = self._prev_read, self._prev_time
        nread, ntime = self._read(), timestamp()
        daccel = sq_dist(pread, nread)
        dtime = (ntime - ptime)
        accel_change =  daccel / dtime
        self._mq_ewma = (self.EWMA_WEIGHT * accel_change
                         + (1-self.EWMA_WEIGHT) * self._mq_ewma)
        self._prev_read = nread
        self._prev_time = ntime
        if self._mq_ewma > self.SIZABLE_MOVE_THRESH:
            if DEBUG >= 2: print('sizable move!!') 
            self._last_sizable_move_time = ntime
        idle_time = ntime - self._last_sizable_move_time
        moving = idle_time < self.IDLE_DELAY
        if DEBUG >= 2:
            print('acc: {}\t[ ({:.2f},{:.2f},{:.2f})\t da/dt:{:.4f}/{:.1f}\t cng:{:.4f}\t ewma:{:.3f}\t idle:{:.1f} ]'.format(
                moving, nread[0], nread[1], nread[2], daccel, dtime,
                accel_change, self._mq_ewma, idle_time))
        return moving


class Neos(object):
    def __init__(self, pin, num_leds):
        self._num = num_leds
        self._neos = neopixel.NeoPixel(pin, num_leds)
        self._initialization_colors()

    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, val):
        self._neos.brightness = val
        self._brightness = val

    def set_colors(self, colors):
        for i in range(self._num):
            i = self._num - 1 - i
            self._neos[i] = colors[i % len(colors)]

    def _initialization_colors(self):
        self.brightness = 0.1
        self.set_colors(smoothify(5, [(200, 0, 0), (0, 0, 200)]))
        self.brightness = 0.15
        self.set_colors(smoothify(5, [(0, 0, 200), (200, 0, 200)]))
        self.brightness = 0.1
        self.set_colors([(0,0,0)])


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


def shift_array(xs, n):
    n %= len(xs)
    return xs[n:] + xs[:n]


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

IDLE = smoothify(3, [(0, 0, 0),
                     (180, 0, 90),
                     (100, 0, 125),
                     (180, 0, 90),
                     (0, 0, 0)])



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

board_neo = try_get_board_neo()

neos = Neos(board.D12, NLEDS)

## accel
accel = Accel(board.A0, board.A1, board.A2)

## brightness pot
bright_pot = Pot(board.A4)

## palette button
palette_but = Button(board.D11)

MIN_NEW_PALETTE_TIME = 3
last_palette_change_time = 0

i = 0
while True:
    now = timestamp()
    if DEBUG >= 2: print()
    board_led.value = not board_led.value

    ## Brightness pot
    pot_val = bright_pot.read()
    bright = simpleio.map_range(pot_val, 0, 1, MIN_BRIGHT, MAX_BRIGHT)
    if DEBUG >= 2:
        print('pot: {:.2f}\t[ potval:{:.2f} ]'.format(bright, pot_val))
    neos.brightness = bright

    ## Accel
    is_moving = accel.is_moving()

    ## Palette button
    if palette_but.get_press():
        neos.set_colors([(0,0,0), (0,0,0), (180, 0, 180)])
        PALETTE_INDEX = (PALETTE_INDEX + 1) % len(PALETTES)
        last_palette_change_time = now

    if (not is_moving
        and now - last_palette_change_time > MIN_NEW_PALETTE_TIME):
        palette = IDLE
    else:
        palette = PALETTES[PALETTE_INDEX]

    ## Iterate palette

    raw_step = len(palette) * FULL_UPDATE_SEC / TARGET_PALETTE_CYCLE_SEC
    # mq_step = raw_step * simpleio.map_range(mq, 0, 1, 0.5, 10)
    step = min(max(int(round(raw_step)), 1), int(len(palette) / 2) )

    i = (i + step) % len(palette)
    if DEBUG >= 2:
        print('stp:', step, '\t[ raw:', raw_step, ' ]')

    if DEBUG >= 1:
        print('mv:{} \tbr:{:.1f}\tstp:{}'.format(is_moving, bright, step))

    neos.set_colors(shift_array(palette, i))
    if board_neo:
        board_neo[0] = palette[i]
