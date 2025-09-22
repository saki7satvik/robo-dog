from servo_controller import ServoController
from motion_engine import MotionEngine, MotionGoal
import dog_sequences

SERVO_MAP_PATH = "servo_map_dog.json"

def feedback_cb(feedback):
    print("Feedback:", feedback)

if __name__ == "__main__":
    print("\n--- MotionEngine Dog Sequence Demo ---")
    servo = ServoController(SERVO_MAP_PATH, simulate_if_no_hw=True)
    engine = MotionEngine(servo, feedback_cb=feedback_cb)

    # Push sit sequence
    sit_goal = MotionGoal(
        goal_id="sit_test",
        action="sequence",
        poses=dog_sequences.sit,
        priority=10
    )
    engine.push_goal(sit_goal)

    # Push stand sequence
    stand_goal = MotionGoal(
        goal_id="stand_test",
        action="sequence",
        poses=dog_sequences.stand,
        priority=8
    )
    engine.push_goal(stand_goal)

    # Push wave paw sequence
    wave_goal = MotionGoal(
        goal_id="wave_test",
        action="sequence",
        poses=dog_sequences.wave_paw,
        priority=6
    )
    engine.push_goal(wave_goal)

    # Allow time for execution
    import time
    time.sleep(5)
    engine.stop()
