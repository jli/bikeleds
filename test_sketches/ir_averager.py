import board
import pulseio
import adafruit_irremote


def add_pulse(p1, p2):
    if len(p1) != len(p2):
        print('lengths not the same:', len(p1), len(p2))
        return None
    return [x + y for (x, y) in zip(p1, p2)]

def div_pulse(pulse, div):
    return [int(p / div) for  p in pulse]

class RemoteRx(object):
    def __init__(self, pin):
        self._pulses = pulseio.PulseIn(pin, maxlen=200, idle_state=True)
        self._decoder = adafruit_irremote.GenericDecode()

    def raw_receive(self):
        print('rawrec clearing..', len(self._pulses))
        self._pulses.pause()
        self._pulses.clear()
        self._pulses.resume()
        print('rawrec receiving..')
        res = self._decoder.read_pulses(self._pulses)
        print('rawrec got result:', len(res))
        return res

rx = RemoteRx(board.D2)

count = 0
avg_pulse = None

print('dropping first:', rx.raw_receive())


while True:
    pulse = rx.raw_receive()

    print('\n{} received: {}\n'.format(count, pulse))
    if avg_pulse is None:
        avg_pulse = pulse
    else:
        summed = add_pulse(avg_pulse, pulse)
        if summed is not None:
            avg_pulse = summed
            count += 1
            print('average pulse:\n', div_pulse(avg_pulse, count))
