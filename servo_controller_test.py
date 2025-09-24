# servo_controller_test.py
import time
import sys
from servo_controller import ServoController

# Path to your JSON config
SERVO_MAP = "servo_map_dog.json"

# Define a realistic dog stance (bent knees, thighs angled)
# DOG_STANCE = {
#     "fl_hip": 90,   "fl_thigh": 120, "fl_knee": 100,
#     "fr_hip": 90,   "fr_thigh": 60,  "fr_knee": 100,
#     "bl_hip": 90,   "bl_thigh": 60,  "bl_knee": 100,
#     "br_hip": 90,   "br_thigh": 120, "br_knee": 100,
# }

def wait_keypress(msg="Press Enter to continue..."):
    try:
        input(msg)
    except KeyboardInterrupt:
        sys.exit(0)

def main():
    print("=== Robo Dog Servo Controller Test ===")
    ctrl = ServoController(SERVO_MAP)

if __name__ == "__main__":
    main()