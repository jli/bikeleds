# Inputs:
# (dreaming)
# - knob to control speed (todo: figure out max speed first)
# - brightness control
# - knob to control predator breed/feed ?

import random
import time

# import analogio
# import board
# import digitalio
# import simpleio
# import neopixel

# behavior config
INIT_PREDATOR_FRAC = 0.10
PREDATOR_FEED_CYCLE = 2
PREDATOR_BREED_CYCLE = 10
PREDATOR_BREED_PROB = 1.0
INIT_PREY_FRAC = 0.20
PREY_MOVES = True
PREY_BREED_CYCLE = 1
PREY_BREED_PROB = 0.8

# world config
GRID_ROWS = 16
GRID_COLS = 16

# physical config
# NEOS_PIN = board.D12
# BOARD_LED = board.D13
BRIGHT_INIT = 0.05
BRIGHT_MIN = 0.05
BRIGHT_MAX = 1.0
BRIGHT_INC = (BRIGHT_MAX - BRIGHT_MIN ) / 10

# misc constants
CELL_EMPTY = 0
CELL_PREY = 1
CELL_PREDATOR = 2
NEIGHBOR_DIRS = [
  [-1, -1], [0, -1], [1, -1],
  [-1, 0], [0, 1],
  [-1, 1], [0, 1], [1, 1]
]

PREDATOR_HUE = 0
PREY_HUE = 120
RAND_HUE_STATE = 0
def rand_hue():
    global RAND_HUE_STATE
    RAND_HUE_STATE = (RAND_HUE_STATE + random.randint(80, 160)) % 360
    return RAND_HUE_STATE


FRAME_COUNT = 0



# class NeoGrid(object):
#     def __init__(self):
#         self.num_rows = GRID_ROWS
#         self.num_cols = GRID_COLS
#         self.num = self.num_rows * self.num_cols
#         self.neos = neopixel.NeoPixel(NEOS_PIN, self.num, auto_write=False)
#         self._brightness = BRIGHT_INIT
#
#     @property
#     def brightness(self):
#         return self._brightness
#
#     @brightness.setter
#     def brightness(self, val):
#         self.neos.brightness = max(BRIGHT_MIN, min(BRIGHT_MAX, val))
#         self._brightness = val
#
#     def set_colors(self, grid):
#         i = 0
#         for row in grid:
#             for cell in row:
#                 self.neos[i] = cell.color()
#                 i += 1
#         self.neos.show()


def map_(x, a1, b1, a2, b2, clip=False):
    p1 = (x - a1) / (b1 - a1)
    p2 = p1 * (b2 - a2) + a2
    if clip:
        p2 = max(a2, min(b2, p2))
    return p2


class Cell(object):
    def __init__(self, typ):
        self.type = typ
        self.birth = FRAME_COUNT
        self.last_update = 0
        self.last_breed = FRAME_COUNT
        self.last_feed = FRAME_COUNT  # predator-only

    def color(self):
        if self.type == CELL_EMPTY:
            return None
        elif self.type == CELL_PREDATOR:
            hunger = FRAME_COUNT - self.last_feed
            feed_mult = map_(hunger, 0, PREDATOR_FEED_CYCLE, 1, 0.3)
            return (PREDATOR_HUE, 100 * max(feed_mult, 0.7), 100 * feed_mult)
        else:
            age = FRAME_CONUT - self.birth
            age_mult = map_(age, 0, 50, 1, .3, True)
            return (PREY_HUE, 100 * max(age_mult, 0.7), 100 * age_mult)

    def char(self):
        if self.type == CELL_EMPTY: return ' '
        elif self.type == CELL_PREDATOR: return 'X'
        elif self.type == CELL_PREY: return '_'
        else: return '???'


class World(object):
    def __init__(self):
        self.num_rows = GRID_ROWS
        self.num_cols = GRID_COLS
        self.grid = []
        for r in range(self.num_rows):
            col = []
            for c in range(self.num_cols):
                if random.random() < INIT_PREY_FRAC: t = CELL_PREY
                elif random.random() < INIT_PREDATOR_FRAC: t = CELL_PREDATOR
                else: t = CELL_EMPTY
                col.append(Cell(t))
            self.grid.append(col)

    def print_ascii(self):
        print('\n', FRAME_COUNT)
        for row in self.grid:
            for cell in row:
                print(cell.char(), end='')
            print()
        time.sleep(.1)

    def find_cell(self, row, col, typ):
        random.shuffle(NEIGHBOR_DIRS)
        for (rd, cd) in NEIGHBOR_DIRS:
          r2 = rd + row
          c2 = cd + col
          # TODO: wraparound?
          if r2 < 0 or r2 >= GRID_ROWS or c2 < 0 or c2 >= GRID_COLS:
              continue
          if self.grid[r2][c2].type == typ:
              return (r2, c2)
        return None

    def step(self):
        changed = False
        for (r, row) in enumerate(self.grid):
            for (c, cell) in enumerate(row):
                if cell.last_update == FRAME_COUNT: continue
                elif cell.type == CELL_PREDATOR:
                    if self.predator_action(r, c, cell): changed = True
                elif cell.type == CELL_PREY:
                    if self.prey_action(r, c, cell): changed = True
                cell.last_update = FRAME_COUNT
        return changed

    def predator_action(self, r, c, pred):
        changed = False
        prey_pos = self.find_cell(r, c, CELL_PREY)
        if prey_pos:
            # move and eat prey
            self.grid[prey_pos[0]][prey_pos[1]] = pred
            self.grid[r][c] = Cell(CELL_EMPTY)
            pred.last_feed = FRAME_COUNT
            changed = True
        elif FRAME_COUNT - pred.last_feed > PREDATOR_FEED_CYCLE:
            # die
            self.grid[r][c] = Cell(CELL_EMPTY)
            changed = True
            return changed
        else:
            # move to random empty cell
            pos = self.find_cell(r, c, CELL_EMPTY)
            if pos:
                self.grid[pos[0]][pos[1]] = pred
                self.grid[r][c] = Cell(CELL_EMPTY)
                changed = True

        if (FRAME_COUNT - pred.last_breed > PREDATOR_BREED_CYCLE
            and random.random() < PREDATOR_BREED_PROB):
            # Prefer to spawn into empty space, but spawn over a prey cell if necessary.
            pos = self.find_cell(r, c, CELL_EMPTY)
            if not pos: pos = self.find_cell(r, c, CELL_PREY)
            if pos:
                self.grid[pos[0]][pos[1]] = Cell(CELL_PREDATOR)
                pred.last_breed = FRAME_COUNT
                changed = True
        return changed

    def prey_action(self, r, c, prey):
        # TODO: asexual breeding?
        # TODO: die if haven't bred recently?
        changed = False
        empty_pos = self.find_cell(r, c, CELL_EMPTY)
        if (FRAME_COUNT - prey.last_breed > PREY_BREED_CYCLE
            and empty_pos
            and random.random() < PREY_BREED_PROB):
            # breed
            self.grid[empty_pos[0]][empty_pos[1]] = Cell(CELL_PREY)
            self.last_breed = FRAME_COUNT
            changed = True
        elif empty_pos and PREY_MOVES:
            self.grid[empty_pos[0]][empty_pos[1]] = prey
            self.grid[r][c] = Cell(CELL_EMPTY)
            changed = True
        return changed


def init_world():
  PREDATOR_HUE = rand_hue()
  PREY_HUE = rand_hue()
  return World()


# board_led = simpleio.DigitalOut(BOARD_LED)
# board_led.value = True
# neos = NeoGrid()

world = init_world()

while True:
    # board_led.value = not board_led.value
    changed = world.step()

    # neos.set_colors(world.grid)
    world.print_ascii()
    FRAME_COUNT += 1

    if not changed:
        time.sleep(1)
        # wtf why does this break things
        #FRAME_COUNT = 0
        world = init_world()
