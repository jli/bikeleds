"""Test program to measure current consumption of LEDs.

Button switches between various color & brightness configurations.

Data:
https://docs.google.com/spreadsheets/d/1evpuS2nY_CQLP2FsEA-JiHZUygXih2IOLr_ESvv3rWQ/edit

Turning down saturation (scaling the RGB values down) seems effectively the same
as scaling down the brightness.
"""

import analogio
import board
from digitalio import DigitalInOut, Direction, Pull
import simpleio
import time

import neopixel

NLEDS = 10

color_sw = DigitalInOut(board.D7)
bright_sw = DigitalInOut(board.D8)
sat_sw = DigitalInOut(board.D9)
board_led = simpleio.DigitalOut(board.D13)
neos = neopixel.NeoPixel(board.D2, NLEDS)
neos.brightness = 0.1

DELAY = 0.3

class Option(object):
    def __init__(self, options, initial_index=None):
        if initial_index is None:
            initial_index = len(options) - 1
        self._options = options
        self._last_index = len(options) - 1
        self._index = initial_index
        self._inc = True

    def get(self):
        return self._options[self._index]

    def click(self):
        if self._inc:
            if self._index == self._last_index:
                self._inc = False
                self._index -= 1
            else:
                self._index += 1
        else:
            if self._index == 0:
                self._inc = True
                self._index += 1
            else:
                self._index -= 1

    def __str__(self):
        return '{} ({}/{}, {})'.format(
            self.get(), self._index, self._last_index, self._inc)


bright_opt = Option([x/10 for x in range(0, 11)])
sat_opt = Option([x/10 for x in range(0, 11)])


COLOR_OPTIONS = [
    # one color
    (255,   0,   0),
    (  0, 255,   0),
    (  0,   0, 255),
    # two colors
    (255, 255,   0),
    (  0, 255, 255),
    (255,   0, 255),
    # white
    (255, 255, 255),
]

color_opt = Option(COLOR_OPTIONS, 0)

def color_scale(rgb, scale):
    r, g, b = rgb
    return (int(r * scale), int(g * scale), int(b * scale))

def set_neo_colors():
    neos.brightness = bright_opt.get()
    for i in range(NLEDS):
        rgb = color_scale(color_opt.get(), sat_opt.get())
        neos[i] = rgb

for s in [color_sw, bright_sw, sat_sw]:
    s.direction = Direction.INPUT
    s.pull = Pull.UP

init = False
while True:
    changed = False
    if not color_sw.value:
        color_opt.click()
        changed = True
    if not bright_sw.value:
        bright_opt.click()
        changed = True
    if not sat_sw.value:
        sat_opt.click()
        changed = True

    set_neo_colors()

    if changed or not init:
        init = True
        board_led.value = not board_led.value
        print('\n\ncolor:\t', color_opt, '\nbright:\t', bright_opt, '\nsatur:\t',
              sat_opt)
        time.sleep(DELAY)
