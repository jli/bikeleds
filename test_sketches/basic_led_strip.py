import board
import simpleio
# import pulseio
import time

import neopixel


NLEDS = 20
COLOR_STEP = 10

RAW_COLOR_ARRAY = [
  (255, 0, 0),
  (0, 255, 0),
  (0, 0, 255)
]


## setup LEDs and smoothed color array

# led = pulseio.PWMOut(board.D13, frequency=5000, duty_cycle=0)
board_led = simpleio.DigitalOut(board.D13)

# on-board metro neopixel
metro_neo = None
try:
    metro_neo = neopixel.NeoPixel(board.NEOPIXEL, 1)
except AttributeError:
    pass
if metro_neo:
    metro_neo.brightness = 0.01

neos = neopixel.NeoPixel(board.D2, NLEDS)
neos.brightness = .1

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


COLOR_ARRAY = call_n_times(smooth, RAW_COLOR_ARRAY, 7)
NCOLORS = len(COLOR_ARRAY)



board_led.value = True
print('ncolors:', NCOLORS)

i = 0
while True:
    i = (i + COLOR_STEP) % NCOLORS
    print('shift', i, NLEDS, NCOLORS)
    for j in range(NLEDS):
        #print('  led', j)
        index = i + j
        if index >= NCOLORS:
            index = 0
        (r, g, b) = COLOR_ARRAY[index]
        neos[j] = (r,g,b)
    if metro_neo:
        metro_neo[0] = COLOR_ARRAY[i]
    board_led.value = not board_led.value
