# Inputs:
# (dreaming)
# - knob to control predator breed/feed ?

import random
import time

import board
import simpleio
from adafruit_fancyled import adafruit_fancyled as fancy
import neopixel

# behavior config
INIT_PREDATOR_FRAC = 0.10
PREDATOR_FEED_CYCLE = 2
PREDATOR_BREED_CYCLE = 4
PREDATOR_BREED_PROB = 0.9
INIT_PREY_FRAC = 0.08
PREY_MOVES = True
PREY_BREED_CYCLE = 2
# PREY_BREED_PROB = 1.0
TOMB_CYCLE = 5  # steps that dead prey cells stay empty

# world config
WRAPAROUND = False
# SPAWN_OVER_PREY = False
GRID_ROWS = 16
GRID_COLS = GRID_ROWS
PHYS_ROWS = 16
PHYS_COLS = PHYS_ROWS
SKIP_TOP_ROWS = (PHYS_ROWS - GRID_ROWS) // 2
SKIP_LEFT_COLS = (PHYS_COLS - GRID_COLS) // 2
SKIP_RIGHT_COLS = PHYS_COLS - GRID_COLS - SKIP_LEFT_COLS

# physical config
BOARD_LED = board.D13
NEOS_PIN = board.D12
BRIGHT_MIN = 0.008
BRIGHT_MAX = 0.08

# misc constants
CELL_EMPTY = 0
CELL_PREY = 1
CELL_PREDATOR = 2
CELL_TOMB = 3
NEIGHBOR_DIRS = [
  [-1, -1], [0, -1], [1, -1],
  [-1, 0], [0, 1],
  [-1, 1], [0, 1], [1, 1],
]
DIRS_LEN = len(NEIGHBOR_DIRS)
FRAMES_AFTER_NO_CHANGE = 1

# state
FRAME_COUNT = 0
PREDATOR_HUE, PREY_HUE, RAND_HUE_STATE = None, None, random.random()
def rand_hue():
    global RAND_HUE_STATE
    RAND_HUE_STATE = (RAND_HUE_STATE + random.uniform(.3333, .6666)) % 1
    return RAND_HUE_STATE


def shuffle(xs):
    i = len(xs) - 1
    while i >= 1:
        j = random.randint(0, i)
        tmp = xs[i]
        xs[i] = xs[j]
        xs[j] = tmp
        i -= 1


def index_wrap(i, max_val):
  if i < 0: return i + max_val
  elif i >= max_val: return i - max_val
  return i


class NeoGrid(object):
    def __init__(self):
        self.neos = neopixel.NeoPixel(NEOS_PIN, PHYS_COLS * PHYS_ROWS, auto_write=False)

    def set_colors(self, grid):
        even_row = SKIP_TOP_ROWS % 2 == 0
        for r in range(0, GRID_ROWS):
            for c in range(0, GRID_COLS):
                i = (PHYS_COLS * (SKIP_TOP_ROWS + r)
                     + (SKIP_LEFT_COLS if even_row else SKIP_RIGHT_COLS)
                     + (c if even_row else GRID_COLS - 1 - c))
                self.neos[i] = grid[r][c].color().pack()
            even_row = not even_row
        self.neos.show()


def map_(x, a1, b1, a2, b2, clip=False):
    p1 = (x - a1) / (b1 - a1)
    p2 = p1 * (b2 - a2) + a2
    if clip:
        p2 = max(a2, min(b2, p2))
        # more correct, but saving a check by ensuring b2 always > a2.
        #if a2 < b2: p2 = max(a2, min(b2, p2))
        #else: p2 = max(b2, min(a2, p2))
    return p2


class Cell(object):
    def __init__(self, typ):
        self.type = typ
        self.birth = FRAME_COUNT
        self.last_update = -1
        self.last_breed = FRAME_COUNT
        self.last_feed = FRAME_COUNT  # predator-only

    def color(self):
        if self.type == CELL_PREDATOR:
            hunger = FRAME_COUNT - self.last_feed
            feed_bright = map_(hunger, PREDATOR_FEED_CYCLE-1, 0, BRIGHT_MIN, BRIGHT_MAX)
            feed_sat = map_(hunger, PREDATOR_FEED_CYCLE-1, 0, 0.80, 1.0)
            return fancy.CHSV(PREDATOR_HUE, feed_sat, feed_bright)
        elif self.type == CELL_PREY:
            age = FRAME_COUNT - self.birth
            age_bright = map_(age, 5, 0, BRIGHT_MIN, BRIGHT_MAX, clip=True)
            age_sat = map_(age, 10, 0, 0.80, 1.0, clip=True)
            return fancy.CHSV(PREY_HUE, age_sat, age_bright)
        else:
            # CELL_EMPTY and TOMB
            return fancy.CHSV(0,0,0)

    def char(self):
        if self.type == CELL_EMPTY: return ' '
        elif self.type == CELL_PREDATOR: return 'X'
        elif self.type == CELL_PREY: return '_'
        else: return '?'


class World(object):
    def __init__(self):
        self.neos = NeoGrid()
        self.grid = []
        self.reset_grid()

    def reset_grid(self):
        self.grid = []
        for r in range(GRID_ROWS):
            col = []
            for c in range(GRID_COLS):
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

    def draw(self):
        self.neos.set_colors(self.grid)

    def find_cell(self, row, col, typ):
        shuffle(NEIGHBOR_DIRS)
        for (rd, cd) in NEIGHBOR_DIRS:
            r2 = rd + row
            c2 = cd + col
            if WRAPAROUND:
                r2 = index_wrap(r2, GRID_ROWS)
                c2 = index_wrap(c2, GRID_COLS)
            if r2 < 0 or r2 >= GRID_ROWS or c2 < 0 or c2 >= GRID_COLS:
                continue
            if self.grid[r2][c2].type == typ:
                return (r2, c2)
        return None

    def find_cell_multi(self, row, col, types):
        shuffle(NEIGHBOR_DIRS)
        for (rd, cd) in NEIGHBOR_DIRS:
            r2 = rd + row
            c2 = cd + col
            if WRAPAROUND:
                r2 = index_wrap(r2, GRID_ROWS)
                c2 = index_wrap(c2, GRID_COLS)
            if r2 < 0 or r2 >= GRID_ROWS or c2 < 0 or c2 >= GRID_COLS:
                continue
            if self.grid[r2][c2].type in types:
                return (r2, c2)
        return None

    def step(self):
        changed = False
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                cell = self.grid[r][c]
                if cell.last_update == FRAME_COUNT: continue
                elif cell.type == CELL_PREDATOR:
                    if self.predator_action(r, c, cell): changed = True
                elif cell.type == CELL_PREY:
                    if self.prey_action(r, c, cell): changed = True
                elif cell.type == CELL_TOMB:
                    self.tomb_action(r, c, cell)
                cell.last_update = FRAME_COUNT
        return changed

    def tomb_action(self, r, c, tomb):
        if FRAME_COUNT - tomb.birth >= TOMB_CYCLE:
            self.grid[r][c] = Cell(CELL_EMPTY)
        return False  # don't count tomb->empty as a state change

    def predator_action(self, r, c, pred):
        changed = False
        prey_pos = self.find_cell(r, c, CELL_PREY)
        if prey_pos:
            # move and eat prey
            self.grid[prey_pos[0]][prey_pos[1]] = pred
            self.grid[r][c] = Cell(CELL_TOMB if (TOMB_CYCLE > 0) else CELL_EMPTY)
            pred.last_feed = FRAME_COUNT
            changed = True
        elif FRAME_COUNT - pred.last_feed >= PREDATOR_FEED_CYCLE:
            # die
            self.grid[r][c] = Cell(CELL_EMPTY)
            changed = True
            return changed
        else:
            # move to random empty cell
            pos = self.find_cell_multi(r, c, (CELL_EMPTY, CELL_TOMB))
            if pos:
                self.grid[pos[0]][pos[1]] = pred
                self.grid[r][c] = Cell(CELL_EMPTY)
                changed = True

        if (FRAME_COUNT - pred.last_breed >= PREDATOR_BREED_CYCLE
            and random.random() < PREDATOR_BREED_PROB):
            pos = self.find_cell_multi(r, c, (CELL_EMPTY, CELL_TOMB))
            # Prefer to spawn into empty space, but spawn over a prey cell if necessary.
            # if not pos and SPAWN_OVER_PREY:
            #     pos = self.find_cell(r, c, CELL_PREY)
            if pos:
                self.grid[pos[0]][pos[1]] = Cell(CELL_PREDATOR)
                pred.last_breed = FRAME_COUNT
                changed = True
        return changed

    def prey_action(self, r, c, prey):
        changed = False
        empty_pos = self.find_cell(r, c, CELL_EMPTY)
        if (FRAME_COUNT - prey.last_breed >= PREY_BREED_CYCLE
            and empty_pos):
            # and random.random() < PREY_BREED_PROB):
            # breed
            self.grid[empty_pos[0]][empty_pos[1]] = Cell(CELL_PREY)
            self.last_breed = FRAME_COUNT
            changed = True
        elif empty_pos and PREY_MOVES:
            self.grid[empty_pos[0]][empty_pos[1]] = prey
            self.grid[r][c] = Cell(CELL_EMPTY)
            changed = True
        return changed


def reset_world(world):
    global PREDATOR_HUE
    global PREY_HUE
    PREDATOR_HUE = rand_hue()
    PREY_HUE = rand_hue()
    world.reset_grid()


board_led = simpleio.DigitalOut(BOARD_LED)
board_led.value = True
world = World()
reset_world(world)

# start_secs = time.monotonic()
# start_frames = 0
while True:
    # print(FRAME_COUNT)
    board_led.value = not board_led.value
    changed = world.step()
    world.draw()
    FRAME_COUNT += 1

    # total_secs = time.monotonic() - start_secs
    # if total_secs > 10:
    #     print('fps:', (FRAME_COUNT - start_frames) / total_secs, '(', FRAME_COUNT-start_frames, '/', total_secs, ')')
    #     start_frames = FRAME_COUNT
    #     start_secs = time.monotonic()
    if not changed:
        # print('RESETTING. frames:', FRAME_COUNT)
        # for _ in range(FRAMES_AFTER_NO_CHANGE):
        #     _changed = world.step()
        #     world.draw()
        #     FRAME_COUNT += 1
        FRAME_COUNT = 0
        reset_world(world)
