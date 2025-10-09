# servo_controller.py
import json
import time
from collections import defaultdict

# If running on Raspberry Pi with adafruit-circuitpython-pca9685:
try:
    import busio
    import board
    from adafruit_pca9685 import PCA9685
    _HAS_HW = True
except Exception:
    # fallback to simulation/no-hardware mode
    _HAS_HW = False

class ServoConfigError(Exception):
    pass

class ServoController:
    def __init__(self, servo_map_path, i2c=None, freq=50, simulate_if_no_hw=True):
        """
        servo_map_path: path to JSON map
        i2c: optional busio.I2C instance; if None we'll create one when hw present
        freq: PWM frequency in Hz (default 50)
        simulate_if_no_hw: True -> allow running without hardware (logs only)
        """
        self.freq = freq
        self.simulate = simulate_if_no_hw and not _HAS_HW
        if(self.simulate):
            print("simulation mode")
    
        self._load_map(servo_map_path)
        # setup PCA devices (one per board address)
        self._pca_devices = {}
        if not self.simulate:
            if i2c is None:
                i2c = busio.I2C(board.SCL, board.SDA)
            # create PCA9685 objects for each address
            for addr in self._addresses:
                pca = PCA9685(i2c, address=int(addr, 16))
                pca.frequency = freq
                self._pca_devices[addr] = pca
        # runtime caches
        self._current_pose = {}
        for nm, cfg in self.servos.items():
            self._current_pose[nm] = cfg.get("neutral", (cfg["angle_min"] + cfg["angle_max"]) / 2.0)
        
        print(self._current_pose)

        self._enabled = True  # used by emergency_stop

        neutral_pose = {nm: ang for nm, ang in self._current_pose.items()}
        self.set_pose(neutral_pose)
        print("[INFO] Robot dog initialized to neutral pose ✅")

    def _load_map(self, path):
        with open(path, "r") as f:
            data = json.load(f)
        servos = {}
        addresses = set()
        for s in data.get("servos", []):
            name = s.get("name")
            if not name:
                raise ServoConfigError("servo_map: missing name field")
            if name in servos:
                raise ServoConfigError(f"duplicate servo name: {name}")
            board_addr = s.get("board_addr")
            if not board_addr:
                raise ServoConfigError(f"servo {name} missing board_addr")
            addresses.add(board_addr)
            servos[name] = s
        # verify channel uniqueness per address
        used = set()
        for name, cfg in servos.items():
            board_addr = cfg["board_addr"]
            ch = cfg["channel"]
            key = (board_addr, ch)
            if key in used:
                raise ServoConfigError(f"duplicate channel {ch} on board {board_addr}")
            used.add(key)
        self.servos = servos
        self._addresses = sorted(addresses)

    # --- angle -> PCA 12-bit conversion ---
    def _angle_to_pwm12(self, angle_deg, cfg):
        """
        Convert desired servo angle to 12-bit PWM value for PCA9685.

        Logic:
        - Mapping is always done over the full 0–180° servo range.
        - Each servo has its own mechanical limits (angle_min / angle_max),
        and those are respected by clamping.
        - If reversed=True:
            0° → 180°
            135° → 45°
            90° → 90°  (neutral remains the same)
        """

        amin, amax = cfg["angle_min"], cfg["angle_max"]
        offset = cfg.get("offset", 0)
        reversed_ = cfg.get("reversed", False)

        # --- 1️⃣ Apply offset ---
        angle = angle_deg + offset

        # --- 2️⃣ Apply reversal ---
        # Mirroring around 180° so 0 → 180, 135 → 45, 90 → 90
        if reversed_:
            angle = 180 - angle

        # --- 3️⃣ Clamp to physical movement limits ---
        if reversed_:
            logical_min = 180 - amax
            logical_max = 180 - amin
        else:
            logical_min = amin
            logical_max = amax

        angle = max(logical_min, min(logical_max, angle))

        # --- 4️⃣ Map angle → pulse width using full 0–180° range ---
        min_us = cfg.get("min_pulse_us", 500)
        max_us = cfg.get("max_pulse_us", 2500)
        us = min_us + (angle / 180.0) * (max_us - min_us)

        # --- 5️⃣ Convert pulse width → 12-bit PWM value ---
        period_us = 1_000_000.0 / self.freq  # e.g., 20,000 µs for 50 Hz
        duty_fraction = us / period_us
        pwm12 = int(round(max(0, min(4095, duty_fraction * 4096))))

        return pwm12



    # low-level write to PCA device
    def _write_pwm(self, board_addr, channel, pwm12):
        if not self._enabled:
            return
        if self.simulate:
            print(f"[SIM] write {board_addr} ch{channel} pwm={pwm12}")
            return
        pca = self._pca_devices.get(board_addr)
        if pca is None:
            raise RuntimeError(f"PCA device for {board_addr} not initialized")
        # adafruit channel expects 16-bit duty cycle (0..65535) but adafruit lib exposes channels[].duty_cycle (0..65535)
        # convert 0..4095 -> 0..65535
        value16 = int((pwm12 / 4095.0) * 65535.0)
        pca.channels[channel].duty_cycle = value16

    # public API
    def set_servo_angle(self, name, angle_deg):
        """
        Immediately set a servo to angle (degrees). Clamps to angle_min/angle_max.
        """
        if name not in self.servos:
            raise KeyError(f"unknown servo: {name}")
        cfg = self.servos[name]
        pwm12 = self._angle_to_pwm12(angle_deg, cfg)
        self._write_pwm(cfg["board_addr"], cfg["channel"], pwm12)
        self._current_pose[name] = angle_deg
        return True

    def set_pose(self, pose_dict):
        """
        pose_dict: {servo_name: angle, ...}
        Writes all specified servos. This function tries to write them quickly in a loop.
        """
        # group writes by board to maybe optimize (not necessary but clean)
        grouped = {}
        for name, angle in pose_dict.items():
            if name not in self.servos:
                raise KeyError(f"unknown servo in pose: {name}")
            cfg = self.servos[name]
            pwm12 = self._angle_to_pwm12(angle, cfg)
            grouped.setdefault(cfg["board_addr"], []).append((cfg["channel"], pwm12, name, angle))

        for board_addr, items in grouped.items():
            for channel, pwm12, name, angle in items:
                self._write_pwm(board_addr, channel, pwm12)
                self._current_pose[name] = angle

    def get_current_pose(self):
        return dict(self._current_pose)

    def get_current_value(self, name):
        return self._current_pose.get(name)

    def emergency_stop(self, set_neutral=False):
        """Immediately disable outputs. If set_neutral True, set neutral before disabling."""
        self._enabled = False
        if set_neutral:
            # attempt to set neutrals (best-effort)
            for nm, cfg in self.servos.items():
                try:
                    neutral = cfg.get("neutral", (cfg["angle_min"] + cfg["angle_max"]) / 2.0)
                    pwm12 = self._angle_to_pwm12(neutral, cfg)
                    if not self.simulate:
                        pca = self._pca_devices[cfg["board_addr"]]
                        value16 = int((pwm12 / 4095.0) * 65535.0)
                        pca.channels[cfg["channel"]].duty_cycle = value16
                    else:
                        print(f"[SIM] set neutral {nm} -> pwm {pwm12}")
                    self._current_pose[nm] = neutral
                except Exception:
                    pass
        else:
            # set all duty cycles to 0 (if hardware supports)
            if not self.simulate:
                for pca in self._pca_devices.values():
                    # adafruit lib supports pca.deinit() to release resources; but here set channels to 0
                    for ch in range(16):
                        pca.channels[ch].duty_cycle = 0
            else:
                print("[SIM] emergency stop: outputs disabled")

    def enable_outputs(self):
        self._enabled = True

if __name__ == "__main__":
    print("====== robo dog initialization ======")
    Dog = ServoController("servo_map_dog.json", simulate_if_no_hw=True)
    # print(Dog.get_current_pose())
