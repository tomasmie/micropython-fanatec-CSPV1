import board
import analogio
import usb_hid
import time
from adafruit_hid.gamepad import Gamepad

# Equivalent of Arduino's map() function.
def range_map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min

# Get normalised value
def get_baseline(analog_pin, count):
    max_val = 0
    for _ in range(count):
        new_val = analog_pin.value
        if max_val < new_val:
            max_val = new_val
    return max_val

# Smoothing function
class RunningAverage:
    def __init__(self, window_size):
        self.window_size = window_size
        self.values = []
        self.sum = 0

    def update(self, value):
        self.values.append(value)
        self.sum += value
        if len(self.values) > self.window_size:
            self.sum -= self.values.pop(0)  # remove the oldest value
        return self.sum / len(self.values)

# Init gamepad
gp = Gamepad(usb_hid.devices)

# Pins
PIN_THROTTLE = board.GP27
PIN_CLUTCH = board.GP26
PIN_BRAKE = board.GP28

# Start cal
maxThr = 0
maxClu = 0
maxBrk = 0

# Hardcoded calibration (Max value to 100%)
forceHardcodedCalibration = True # set false for auto calibration
hardcodedThr = 15000
hardcodedClu = 13000
hardcodedBrk = 5000

# Deadzones (Cutoff)
dzThr = 5
dzClu = 5
dzBrk = 10
dzTopThr = 100
dzTopClu = 100
dzTopBrk = 80

# Smoothing: A larger window size will result in more smoothing, but will also result in a longer delay
thr_avg = RunningAverage(10)
clu_avg = RunningAverage(2) # clutch response more important than precision
brk_avg = RunningAverage(40)

throttle = analogio.AnalogIn(PIN_THROTTLE)
clutch = analogio.AnalogIn(PIN_CLUTCH)
brake = analogio.AnalogIn(PIN_BRAKE)

# blThr = get_baseline(throttle, 50)
# blClu = get_baseline(clutch, 50)
# blBrk = get_baseline(brake, 50)
blThr = 21541 # temp hardcode
blClu = 22181
blBrk = 31927

debug = False

while True:    
    # Get normalised values
    actThrVal = abs(throttle.value - blThr)
    actCluVal = abs(clutch.value - blClu)
    actBrkVal = abs(brake.value - blBrk)
    
    # Smoothing
    if not debug:
        actThrVal = thr_avg.update(abs(throttle.value - blThr))
        actCluVal = clu_avg.update(abs(clutch.value - blClu))
        actBrkVal = brk_avg.update(abs(brake.value - blBrk))

    # Save max value for calibration
    if not forceHardcodedCalibration or (forceHardcodedCalibration and debug):
        if (maxThr < actThrVal):
            maxThr = actThrVal;
        if (maxClu < actCluVal):
            maxClu = actCluVal
        if (maxBrk < actBrkVal):
            maxBrk = actBrkVal;
        
    # Calculate percentage values
    if forceHardcodedCalibration:    
        throttlePercentage = min((actThrVal / hardcodedThr) * 100, 100)
        clutchPercentage = min((actCluVal / hardcodedClu) * 100, 100)
        brakePercentage = min((actBrkVal / hardcodedBrk) * 100, 100)
    else:
        throttlePercentage = min((actThrVal / maxThr) * 100, 100)
        clutchPercentage = min((actCluVal / maxClu) * 100, 100)
        brakePercentage = min((actBrkVal / maxBrk) * 100, 100)

    # Debug
    if(debug):
        print(f'Throttle: {throttle.value}, Baseline: {blThr}, Calibration: {maxThr}/{hardcodedThr}({maxThr-hardcodedThr}), Normalised: {actThrVal}, Percentage: {throttlePercentage}%')
        print(f'Clutch: {clutch.value}, Baseline: {blClu}, Calibration: {maxClu}/{hardcodedClu}({maxClu-hardcodedClu}), Normalised: {actCluVal}, Percentage: {clutchPercentage}%')
        print(f'Brake: {brake.value}, Baseline: {blBrk}, Calibration: {maxBrk}/{hardcodedBrk}({maxBrk-hardcodedBrk}), Normalised: {actBrkVal}, Percentage: {brakePercentage}%')
        print("- - - - - - -")
        time.sleep(0.2) # debug delay

    # Apply deadzones before joystick
    throttlePercentage = 0 if throttlePercentage <= dzThr else throttlePercentage
    clutchPercentage = 0 if clutchPercentage <= dzClu else clutchPercentage
    brakePercentage = 0 if brakePercentage <= dzBrk else brakePercentage
    throttlePercentage = 100 if throttlePercentage > dzTopThr else throttlePercentage
    clutchPercentage = 100 if clutchPercentage > dzTopClu else clutchPercentage
    brakePercentage = 100 if brakePercentage > dzTopBrk else brakePercentage

    # Move joysticks   
    gp.move_joysticks(
        x=range_map(int(throttlePercentage), 0, 100, -127, 127),
        z=range_map(int(brakePercentage), 0, 100, -127, 127),
        r_z=range_map(int(clutchPercentage), 0, 100, -127, 127)
    )

