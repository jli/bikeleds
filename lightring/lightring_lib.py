import random

from adafruit_fancyled import adafruit_fancyled as fancy
import neopixel

BRIGHTNESS = 0.25
NLEDS = 30
NPARTICLES = 2

SPEED_DECAY = 0.995
SPEED_TO_GC = 0.4
TAIL_BRIGHT_DECAY = 0.8
TAIL_HUE_SHIFT = 0.03
HEAD_HUE_SHIFT = 0.005


def clip(x, a=0, b=NLEDS):
    if x < a: return (a+1, True)
    if x >= b: return (b-1, True)
    return (x, False)

RAND_HUE_STATE = 0
def rand_hue():
    global RAND_HUE_STATE
    RAND_HUE_STATE = (RAND_HUE_STATE + random.uniform(.15, .33)) % 1
    return RAND_HUE_STATE


class Particle(object):
    def __init__(self, pos=None, dir=None, speed=None):
        if pos is None:
            pos = random.random() * NLEDS
        if dir is None:
            dir = 1 if (random.random() > 0.5) else -1
        if speed is None:
            speed = max(0.4, random.random())
        self.pos = pos
        self.dir = dir
        self.speed = speed
        self.hue = rand_hue()

    def step(self):
        self.hue += HEAD_HUE_SHIFT
        self.pos, clipped = clip(self.pos + self.dir * self.speed)
        if clipped: self.dir *= -1
        # if random.random() < 0.02:
        #     self.speed += random.random() - 0.5
        # return self.speed > SPEED_TO_GC


class World(object):
    def __init__(self, neo_pin):
        if NPARTICLES == 2:
            self.particles = [
                Particle(pos=0, dir=1, speed=1),
                Particle(pos=NLEDS-1, dir=-1, speed=1),
            ]
        else:
            self.particles = [Particle() for _ in range(NPARTICLES)]
        self.pixels = [[0,0] for _ in range(NLEDS)]
        self.neos = neopixel.NeoPixel(neo_pin, NLEDS, brightness=BRIGHTNESS, auto_write=False)

    def step(self):
        for (i, p) in enumerate(self.particles):
            alive = p.step()
            # if not alive:
            #     self.particles[i] = Particle()

    def draw(self):
        for i in range(NLEDS):
            self.pixels[i][1] *= TAIL_BRIGHT_DECAY
            self.pixels[i][0] -= TAIL_HUE_SHIFT
        for p in self.particles:
            self.pixels[int(p.pos)] = [p.hue, 1.0]
        for (i, (hue, bright)) in enumerate(self.pixels):
            self.neos[i] = fancy.CHSV(hue, 1.0, bright).pack()
        self.neos.show()
