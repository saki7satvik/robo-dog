from motion_engine import MotionGoal
import uuid
import json

class BehaviorManager:
    def __init__(self, motion_engine, behaviors_path="behaviors.json"):
        self.motion_engine = motion_engine
        self.behaviors = self._load_behaviors(behaviors_path)
        # Map from behaviors.json names to servo_map.json names (if needed)
        self.servo_name_mapping = {
            # Example: "front_left_hip": "fl_hip", etc. Add more if needed
        }
        # Simple tasks for backward compatibility
        self.tasks = {
            "sit": {"fl_hip": 30, "fl_knee": 90, "fr_hip": 30, "fr_knee": 90, "bl_hip": 30, "bl_knee": 90, "br_hip": 30, "br_knee": 90},
            "stand": {"fl_hip": 0, "fl_knee": 0, "fr_hip": 0, "fr_knee": 0, "bl_hip": 0, "bl_knee": 0, "br_hip": 0, "br_knee": 0},
            "wave_paw": {"fl_hip": 30, "fl_knee": 45},
        }

    def _load_behaviors(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[BehaviorManager] Warning: {path} not found, using default behaviors")
            return {}
        except json.JSONDecodeError as e:
            print(f"[BehaviorManager] Error parsing {path}: {e}")
            return {}

    def _map_servo_names(self, target_positions):
        mapped = {}
        for servo_name, angle in target_positions.items():
            mapped_name = self.servo_name_mapping.get(servo_name, servo_name)
            mapped[mapped_name] = angle
        return mapped

    def execute_behavior(self, behavior_name, priority=5):
        if behavior_name not in self.behaviors:
            print(f"[BehaviorManager] Unknown behavior: {behavior_name}")
            return None
        behavior = self.behaviors[behavior_name]
        sequence = behavior.get("sequence", [])
        if not sequence:
            print(f"[BehaviorManager] Empty sequence for behavior: {behavior_name}")
            return None
        poses = []
        for step in sequence:
            target_positions = step.get("target_positions", {})
            duration = step.get("duration", 1.0)
            mapped_pose = self._map_servo_names(target_positions)
            poses.append({"duration": duration, "pose": mapped_pose})
        goal = MotionGoal(
            goal_id=str(uuid.uuid4()),
            action="sequence",
            poses=poses,
            priority=priority,
        )
        print(f"[BehaviorManager] Executing behavior: {behavior_name} with {len(poses)} steps")
        return self.motion_engine.push_goal(goal)

    def execute_task(self, task_name, duration=1.0, priority=5):
        if task_name in self.behaviors:
            return self.execute_behavior(task_name, priority)
        if task_name not in self.tasks:
            print(f"[BehaviorManager] Unknown task: {task_name}")
            return None
        pose = self.tasks[task_name]
        goal = MotionGoal(
            goal_id=str(uuid.uuid4()),
            action="pose",
            poses=[{"duration": duration, "pose": pose}],
            priority=priority,
        )
        return self.motion_engine.push_goal(goal)

    def list_behaviors(self):
        print(f"[BehaviorManager] Available behaviors from JSON: {list(self.behaviors.keys())}")
        print(f"[BehaviorManager] Available simple tasks: {list(self.tasks.keys())}")
        return list(self.behaviors.keys()) + list(self.tasks.keys())
