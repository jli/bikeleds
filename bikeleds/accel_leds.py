# TODO:
# - make patterns follow geometry of bike. (refactor to usehorizontal position
#   instead of index?)
# - fancier patterns, apply differences in brightness, back and forth instead of
#   one directional cycle.
# - refactor events handling to be higher level? event streams, etc?

# Inputs:
# - one large button: cycles between patterns
# - two smaller buttons: up/down control for brightness. (maybe also control
#   speed somehow?)
# - accelerometer: when stopped, changes to different pattern.

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

NLEDS = 44
BRIGHT_MIN = 0.05
BRIGHT_MAX = 1.0
BRIGHT_INC = (BRIGHT_MAX - BRIGHT_MIN ) / 10
BRIGHT_INIT = 0.2

DEBUG = 1

# try to cycle between full color palette in this many seconds
TARGET_PALETTE_CYCLE_SEC = 6

# This is actually a function of NLEDS, but i dunno exactly how. this value is
# roughly right for 45 ¯\_(ツ)_/¯
FULL_UPDATE_SEC = 0.04

WHITE = (255,255,255)
BLACK = (0,0,0)
RED = (255,0,0)

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


class Accel(object):
    EWMA_WEIGHT = 0.2  # for new points
    SIZABLE_MOVE_THRESH = 0.08
    IDLE_DELAY = 5

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
            if DEBUG >= 2: print('sizable move!! {} > {}'.format(self._mq_ewma, self.SIZABLE_MOVE_THRESH))
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
        self._neos = neopixel.NeoPixel(pin, num_leds, auto_write=False)
        self.brightness = BRIGHT_INIT

    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, val):
        self._neos.brightness = max(BRIGHT_MIN, min(BRIGHT_MAX, val))
        self._brightness = val

    def set_colors(self, colors, shift=0, wave=False):
        if type(colors) is tuple:
            colors = [colors]
        for i in range(self._num):
            i = self._num - 1 - i
            self._neos[i] = colors[(i + shift) % len(colors)]
            if wave:
                self._neos.show()
        if not wave:
            self._neos.show()


    def inc_brightness(self):
        new_bright = self.brightness + BRIGHT_INC
        if new_bright >= BRIGHT_MAX:
            self.brightness = BRIGHT_MAX
            if DEBUG >= 1: print('inc_bright: hit max: ', self.brightness)
            self.set_colors(BLACK)
            for i in range(8):
                time.sleep(0.05)
                self.set_colors([BLACK, RED, RED, RED], i)
            time.sleep(0.1)
        else:
            self.brightness = new_bright
            if DEBUG >= 1: print('inc_bright: ', self.brightness)

    def dec_brightness(self):
        new_bright = self.brightness - BRIGHT_INC
        if new_bright <= BRIGHT_MIN:
            self.brightness = BRIGHT_MIN
            if DEBUG >= 1: print('dec_bright: hit min: ', self.brightness)
            self.set_colors(BLACK)
            for i in range(8):
                time.sleep(0.05)
                self.set_colors([BLACK, BLACK, BLACK, RED], i)
            time.sleep(0.1)
        else:
            self.brightness = new_bright
            if DEBUG >= 1: print('dec_bright: ', self.brightness)


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
GREEN_BLUE = smoothify(6, [(0, 130, 60),
                           (0, 50, 100)])
VIOLET = smoothify(5, [(100, 0, 125),
                       (50, 0, 90),
                       (90, 0, 50)])
ORANGE_PURPLE = smoothify(5, [(150, 50, 0),
                              (125, 0, 125)])
PALETTES = [RGB, GREEN_BLUE, VIOLET, ORANGE_PURPLE]
PALETTE_INDEX = 0

IDLE_PALETTE = smoothify(3, [(0, 0, 0),
                             (180, 0, 90),
                             (100, 0, 125),
                             (180, 0, 90)])
CHANGE_BUTTON_PALETTE = smoothify(2, [(0, 0, 0),
                                      (0, 0, 0),
                                      (180, 0, 180)])
CHANGE_SPEED_PALETTE = smoothify(2, [(0, 180, 0),
                                     (80, 150, 80),
                                     (0, 0, 0),
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
        board_neo.brightness = BRIGHT_INIT
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
accel = Accel(board.A3, board.A4, board.A5)

## palette button
palette_but = Button(board.D11)

## up/down brightness buttons
up_but = Button(board.D10)
down_but = Button(board.D9)

# won't go into idle pattern until this many seconds after last palette change.
MIN_NEW_PALETTE_TIME = 3
last_palette_change_time = 0

# TODO: push into neos?.
palette = PALETTES[PALETTE_INDEX]
SPEEDS = [0.5, 1, 4, 8]
SPEED_INDEX = 1

i = 0

while True:
    now = timestamp()
    if DEBUG >= 2: print()
    board_led.value = not board_led.value

    ## Brightness buttons
    up_press, down_press = up_but.get_press(), down_but.get_press()
    if up_press and down_press:
        # Special speed hack.
        SPEED_INDEX = (SPEED_INDEX + 1) % len(SPEEDS)
        print('speed change:', SPEED_INDEX)
        for i in range(10):
            neos.set_colors(CHANGE_SPEED_PALETTE, int(i * (SPEED_INDEX+1)))
            time.sleep(.1 / (SPEED_INDEX+1))
    elif up_press:
        neos.inc_brightness()
    elif down_press:
        neos.dec_brightness()

    ## Palette button
    if palette_but.get_press():
        for i in range(10):
            neos.set_colors(CHANGE_BUTTON_PALETTE, i)
        PALETTE_INDEX = (PALETTE_INDEX + 1) % len(PALETTES)
        palette = PALETTES[PALETTE_INDEX]
        last_palette_change_time = now

    ## Accel
    is_moving = accel.is_moving()

    if (not is_moving
        and now - last_palette_change_time > MIN_NEW_PALETTE_TIME
        and palette != IDLE_PALETTE):
        print('now idle..')
        palette = IDLE_PALETTE
        last_palette_change_time = now
        neos.set_colors(BLACK, wave=True)
        neos.set_colors(palette, wave=True)
    elif (is_moving
          and now - last_palette_change_time > MIN_NEW_PALETTE_TIME / 2  # less
          and palette == IDLE_PALETTE):
        print('now active..')
        palette = PALETTES[PALETTE_INDEX]
        last_palette_change_time = now
        neos.set_colors(BLACK, wave=True)
        neos.set_colors(palette, wave=True)

    ## Iterate palette

    raw_step = len(palette) * FULL_UPDATE_SEC / TARGET_PALETTE_CYCLE_SEC
    mult = raw_step * SPEEDS[SPEED_INDEX]
    step = min(max(int(round(mult)), 1),
               int(len(palette) / 2))

    i = (i + step) % len(palette)
    if DEBUG >= 2:
        print('i:', i, '\tstp:', step, '\t[ raw:', raw_step, ' ]')

    if DEBUG >= 2:
        print('mv:{} \t\tstp:{}'.format(is_moving, step))

    neos.set_colors(palette, shift=i)
    if board_neo:
        board_neo[0] = palette[i]
