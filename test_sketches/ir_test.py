import board
import pulseio
import adafruit_irremote
import time

COMMAND_MAP = [
    ('1', [31, 31, 223, 32]),
    ('2', [31, 31, 95, 160]),
    ('3', [31, 31, 159, 96]),
    ('4', [31, 31, 239, 16]),
    ('5',  [31, 31, 111, 144]),
    ('6',  [31, 31, 175, 80]),
    ('7',  [31, 31, 207, 48]),
    ('8',  [31, 31, 79, 176]),
    ('9',  [31, 31, 143, 112]),
    ('0',  [31, 31, 119, 136]),
    ('a', [31, 31, 201,  54]),
    ('b', [31, 31, 215,  40]),
    ('c', [31, 31,  87, 168]),
    ('d', [31, 31, 151, 104]),
    ## These cause TV to react >_<
    # ('social',  [31, 27, 217, 38]),
    # ('mts',  [31, 31, 255, 0]),
    # ('srs',  [31, 31, 137, 118]),
    # ('emanual',  [31, 31, 3, 252]),
    # ('psize',  [31, 31, 131, 124]),
    # ('cc',  [31, 31, 91, 164]),
    ## Maybe these too?
    ('rewind',  [31, 31, 93, 162]),
    ('pause',  [31, 31, 173, 82]),
    ('fastforward',  [31, 31, 237, 18]),
    ('record',  [31, 31, 109, 146]),
    ('play',  [31, 31, 29, 226]),
    ('stop',  [31, 31, 157, 98]),
]

def match_command(bits):
    for cmd, cmd_bits in COMMAND_MAP:
        if bits == cmd_bits:
            return cmd
    return None

class RemoteRx(object):
    def __init__(self, pin):
        self._pulses = pulseio.PulseIn(pin, maxlen=250, idle_state=True)
        self._decoder = adafruit_irremote.GenericDecode()

    def raw_receive(self):
        # self._pulses.pause()
        # self._pulses.clear()
        print('\n\nrawrx: pre-rx len:', len(self._pulses))
        # self._pulses.resume()
        self._pulses.clear()
        # print('rawrx: pre-rx post-res len:', len(self._pulses))
        result = self._decoder.read_pulses(self._pulses)
        # print('rawrx: decoded result, raw len:', len(result), len(self._pulses))
        # self._pulses.pause()
        return result

    # def raw_receive_clear(self):
    #     # self._pulses.pause()
    #     # self._pulses.clear()
    #     print('rawrx: pre-rx len:', len(self._pulses))
    #     self._pulses.clear()
    #     print('rawrx: pre-rx post-clear len:', len(self._pulses))
    #     self._pulses.resume()
    #     result = self._decoder.read_pulses(self._pulses)
    #     self._pulses.pause()
    #     print('rawrx: decoded result, raw len:', len(result), len(self._pulses))
    #     return result

    def decode_receive(self):
        raw = self.raw_receive()
        try:
            return rx._decoder.decode_bits(raw, debug=True)
        except adafruit_irremote.IRDecodeException as e:
            print('decode error, trying again:', e)
            return self.decode_receive()

    def get_command(self):
        return match_command(self.decode_receive())

# rx = RemoteRx(board.D2)
rx = pulseio.PulseIn(board.D2, maxlen=300, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

while True:
    # print('\n----------\ncmd:\n', rx.get_command())
    # print('\n--------\n', rx.decode_receive())

    # print('rx len:', len(rx))
    # print(','.join(str(rx[x]) for x in range(len(rx))))
    # rx.clear()
    # time.sleep(1)
    ### A: 
    # rx len: 68
    # 65535,4566,4467,573,1673,578,1667,574,1671,581,542,573,549,577,546,580,542,573,550,576,1670,581,1664,577,1669,573,550,576,546,579,544,582,541,574,549,577,545,581,542,574,1671,580,1666,576,547,578,1667,574,1671,581,542,574,1671,580,1666,575,547,579,544,582,1663,578,545,581,542,573,1672,580

    print('\n\nrx len:', len(rx))
    print(', '.join(str(rx[x]) for x in range(len(rx))))
    #rx.clear()
    read = decoder.read_pulses(rx)
    try:
        bits = decoder.decode_bits(read, debug=True)
    except adafruit_irremote.IRDecodeException as e:
        print('decode error, trying again:', e)
        bits = 'FAIL'
    print('\nread:', read)
    print('\ndecoded:', bits)
    print('now rx len:', len(rx))

    # print('\n----------------\nremoterx raw rec...')
    # result = rx.raw_receive_clear()
    # print('\n result:', result)
    
