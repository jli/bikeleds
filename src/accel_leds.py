import analogio
import board
import simpleio
# import pulseio
import time

import neopixel


NLEDS = 90
COLOR_STEP = 10

RAW_COLOR_ARRAY = [
  (255, 0, 0),
  (0, 255, 0),
  (0, 0, 255)
]

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

def accel_value(axis):
    # Convert axis value to float within 0...1 range.
    val = axis.value / 65535
    # Shift values to true center (0.5).
    val -= 0.5
    # Convert to gravities.
    return val * 3.0

COLOR_ARRAY = call_n_times(smooth, RAW_COLOR_ARRAY, 7)
NCOLORS = len(COLOR_ARRAY)

ZERO_POINT = (0,0,0)
N_ACCEL_POINTS = 10
ACCEL_POINTS = [ZERO_POINT] * N_ACCEL_POINTS
ACCEL_POINTS_INDEX = 0

AVG_MOVEMENT = 0
EWMA_WEIGHT = 0.05  # for new points



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

## setup accelerometer

x_axis = analogio.AnalogIn(board.A2)
y_axis = analogio.AnalogIn(board.A1)
z_axis = analogio.AnalogIn(board.A0)

def get_new_accel_point():
    return accel_value(x_axis), accel_value(y_axis), accel_value(z_axis)

def squared_dist(p1, p2):
    (x1, y1, z1), (x2, y2, z2) = p1, p2
    return (x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2

def add_accel_point():
    global ACCEL_POINTS_INDEX, AVG_MOVEMENT
    prev = ACCEL_POINTS[ACCEL_POINTS_INDEX]
    ACCEL_POINTS_INDEX = (ACCEL_POINTS_INDEX + 1) % N_ACCEL_POINTS
    cur = get_new_accel_point()
    ACCEL_POINTS[ACCEL_POINTS_INDEX] = cur
    move = min(squared_dist(prev, cur) * 30, 5)
    AVG_MOVEMENT = EWMA_WEIGHT * move + (1-EWMA_WEIGHT) * AVG_MOVEMENT

def last_movement():
    prev = ACCEL_POINTS_INDEX - 1
    if prev < 0:
        prev = -1
    return squared_dist(ACCEL_POINTS[prev],
                        ACCEL_POINTS[ACCEL_POINTS_INDEX])

def movements():
    reordered = ACCEL_POINTS[ACCEL_POINTS_INDEX:] + ACCEL_POINTS[:ACCEL_POINTS_INDEX]
    return [squared_dist(p1, p2) for (p1, p2) in zip(reordered, reordered[1:])]


board_led.value = True
print('ncolors:', NCOLORS)


i = 0
while True:
    i = (i+COLOR_STEP) % NCOLORS
    #print('shift', i, NLEDS, NCOLORS)
    # add_accel_point()
    # scaled_move = min(1, max(0.05, AVG_MOVEMENT))
    #print(ACCEL_POINTS[ACCEL_POINTS_INDEX])
    #print ((AVG_MOVEMENT, scaled_move,))
    # neos.brightness = scaled_move

    for j in range(NLEDS):
        index = i + j
        if index >= NCOLORS:
            index = 0
        (r, g, b) = COLOR_ARRAY[index]
        neos[j] = (r,g,b)
    if metro_neo:
        metro_neo[0] = COLOR_ARRAY[i]
    board_led.value = not board_led.value
    #time.sleep(.1)

