from servo_controller import ServoController
from motion_engine import MotionEngine
from behavior_manager import BehaviorManager
import time

SERVO_MAP_PATH = "servo_map_dog.json"
BEHAVIORS_PATH = "behaviors.json"

def feedback_cb(feedback):
    print("Feedback:", feedback)

if __name__ == "__main__":
    print("\n--- BehaviorManager Test ---")
    servo = ServoController(SERVO_MAP_PATH, simulate_if_no_hw=True)
    engine = MotionEngine(servo, feedback_cb=feedback_cb)
    manager = BehaviorManager(engine, behaviors_path=BEHAVIORS_PATH)

    # List available behaviors and tasks
    manager.list_behaviors()

    # Test executing behaviors
    print("\nExecuting 'sit' behavior...")
    manager.execute_behavior("sit", priority=10)
    time.sleep(2)

    print("\nExecuting 'stand' behavior...")
    manager.execute_behavior("stand", priority=8)
    time.sleep(2)

    print("\nExecuting 'wave_paw' behavior...")
    manager.execute_behavior("wave_paw", priority=6)
    time.sleep(2)

    print("\nExecuting 'bow' behavior...")
    manager.execute_behavior("bow", priority=7)
    time.sleep(2.5)

    print("\nExecuting 'shake' behavior...")
    manager.execute_behavior("shake", priority=5)
    time.sleep(2)

    print("\nExecuting simple task 'sit'...")
    manager.execute_task("sit", duration=1.5, priority=9)
    time.sleep(2)

    engine.stop()
