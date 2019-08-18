import board
import simpleio

import lightring_lib


board_led = simpleio.DigitalOut(board.D13)
board_led.value = True
world = lightring_lib.World(board.D0)

while True:
    board_led.value = not board_led.value
    world.draw()
    world.step()
