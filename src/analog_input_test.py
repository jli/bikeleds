import analogio
import board
import time

x = analogio.AnalogIn(board.A0)
y = analogio.AnalogIn(board.A1)
z = analogio.AnalogIn(board.A2)

def accel_value(axis):
    # Convert axis value to float within 0...1 range.
    val = axis.value / 65535
    # Shift values to true center (0.5).
    val -= 0.5
    # Convert to gravities.
    return val * 3.0

# When A3 is grounded, input reads 0. When A3 is connected to 3V, input reads 1.
while True:
    print('input:\t{:.3f}\t{:.3f}\t{:.3f}'.format(accel_value(x), accel_value(y), accel_value(z)))
    time.sleep(1)
