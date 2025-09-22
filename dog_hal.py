# dog_hal.py
import time
from servo_controller import ServoController

# Optional: use any IMU library (example: MPU6050)
try:
    from mpu6050 import mpu6050
    _HAS_IMU = True
except Exception:
    _HAS_IMU = False


class GyroSensor:
    """
    Wrapper around an IMU (gyro + accel).
    Falls back to simulation if hardware not available.
    """
    def __init__(self, i2c_addr=0x68, simulate_if_no_hw=True):
        self.simulate = simulate_if_no_hw or not _HAS_IMU
        if not self.simulate and _HAS_IMU:
            try:
                self.sensor = mpu6050(i2c_addr)
                print("[HAL] GyroSensor initialized (hardware mode)")
            except Exception as e:
                print(f"[HAL] Gyro init failed: {e}, switching to simulation")
                self.simulate = True
        if self.simulate:
            print("[HAL] GyroSensor initialized (simulation mode)")

    def read_orientation(self):
        """
        Returns dict with accel (m/s^2), gyro (deg/s), temp (°C).
        In simulation mode, returns dummy values.
        """
        if self.simulate:
            return {
                "accel": {"x": 0.0, "y": 0.0, "z": 9.8},
                "gyro": {"x": 0.0, "y": 0.0, "z": 0.0},
                "temp": 25.0
            }
        return {
            "accel": self.sensor.get_accel_data(),
            "gyro": self.sensor.get_gyro_data(),
            "temp": self.sensor.get_temp()
        }


class DogHAL:
    """
    Robo Dog Hardware Abstraction Layer.
    Provides unified access to servos (via ServoController) and sensors (gyro).
    """
    def __init__(self, servo_map_path="servo_map_dog.json",
                 imu_addr=0x68, simulate_if_no_hw=True):
        self.servos = ServoController(servo_map_path, simulate_if_no_hw=simulate_if_no_hw)
        self.gyro = GyroSensor(i2c_addr=imu_addr, simulate_if_no_hw=simulate_if_no_hw)
        self.simulate = simulate_if_no_hw

    # ---- Servo Control Wrappers ----
    def set_pose(self, pose_dict):
        """Set multiple servo angles at once"""
        self.servos.set_pose(pose_dict)

    def set_servo_angle(self, name, angle_deg):
        """Set single servo angle"""
        return self.servos.set_servo_angle(name, angle_deg)

    def get_pose(self):
        """Return last commanded pose dict"""
        return self.servos.get_current_pose()

    def get_servo_value(self, name):
        """Return last commanded angle for single servo"""
        return self.servos.get_current_value(name)

    # ---- Sensor Access ----
    def get_orientation(self):
        """Return IMU orientation (accel, gyro, temp)"""
        return self.gyro.read_orientation()

    # ---- Safety ----
    def emergency_stop(self, set_neutral=False):
        """Stop all servos (optionally set neutral pose)"""
        self.servos.emergency_stop(set_neutral=set_neutral)

    def enable_outputs(self):
        """Re-enable servo outputs after stop"""
        self.servos.enable_outputs()
