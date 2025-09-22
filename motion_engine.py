# motion_engine.py
import time
import threading
import heapq
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Callable, List

# states
PENDING = "PENDING"
ACTIVE = "ACTIVE"
SUCCEEDED = "SUCCEEDED"
PREEMPTED = "PREEMPTED"
ABORTED = "ABORTED"
FAILED = "FAILED"

def lerp(a, b, t): return a + (b - a) * t

@dataclass(order=True)
class PrioritizedItem:
    priority: int
    count: int
    goal: Any=field(compare=False)

@dataclass
class MotionGoal:
    goal_id: str
    action: str
    poses: List[Dict]  # for 'sequence' : list of {duration, pose}
    priority: int = 5
    preemptable: bool = True
    timeout: float = None
    metadata: Dict = None

class MotionEngine:
    def __init__(self, servo_controller, feedback_cb: Callable[[Dict], None]=None, control_hz: int=30):
        self.servo = servo_controller
        self.control_hz = control_hz
        self._queue = []
        self._counter = 0
        self._queue_lock = threading.Lock()
        self._active_goal = None
        self._active_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._feedback_cb = feedback_cb
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()

    def push_goal(self, goal: MotionGoal):
        with self._queue_lock:
            self._counter += 1
            item = PrioritizedItem(priority=-goal.priority, count=self._counter, goal=goal)
            heapq.heappush(self._queue, item)
        return goal.goal_id

    def cancel_goal(self, goal_id: str):
        with self._active_lock:
            if self._active_goal and self._active_goal.goal_id == goal_id:
                self._active_goal._cancel_requested = True
                return True
        # remove from queue
        with self._queue_lock:
            newq = [itm for itm in self._queue if itm.goal.goal_id != goal_id]
            if len(newq) != len(self._queue):
                heapq.heapify(newq)
                self._queue = newq
                return True
        return False

    def _pop_next_goal(self):
        with self._queue_lock:
            if not self._queue: return None
            item = heapq.heappop(self._queue)
            return item.goal

    def _loop(self):
        while not self._stop_event.is_set():
            goal = self._pop_next_goal()
            if goal is None:
                time.sleep(0.05)
                continue
            with self._active_lock:
                self._active_goal = goal
                goal._cancel_requested = False
            try:
                if goal.action == "pose":
                    self._execute_pose(goal)
                elif goal.action == "sequence":
                    self._execute_sequence(goal)
                else:
                    self._publish_feedback(goal.goal_id, FAILED, 0.0, "unsupported action")
            finally:
                with self._active_lock:
                    self._active_goal = None

    def _publish_feedback(self, goal_id, status, progress, message=None):
        fb = {
            "goal_id": goal_id,
            "status": status,
            "progress": progress,
            "current_pose": self.servo.get_current_pose(),
            "message": message,
            "timestamp": time.time()
        }
        if self._feedback_cb:
            try:
                self._feedback_cb(fb)
            except Exception:
                pass

    def _execute_pose(self, goal: MotionGoal):
        pose = goal.poses[0]["pose"]
        duration = goal.poses[0].get("duration", 0.5)
        # reuse sequence executor
        seq_goal = MotionGoal(goal_id=goal.goal_id, action="sequence", poses=[{"duration": duration, "pose": pose}], priority=goal.priority)
        self._execute_sequence(seq_goal)

    def _execute_sequence(self, goal: MotionGoal):
        current = self.servo.get_current_pose()
        total_k = len(goal.poses)
        if total_k == 0:
            self._publish_feedback(goal.goal_id, SUCCEEDED, 1.0, "empty sequence")
            return

        for k_index, kf in enumerate(goal.poses, start=1):
            dur = max(0.0, float(kf.get("duration", 0.5)))
            target = kf["pose"]
            steps = max(1, int(self.control_hz * max(0.001, dur)))
            for step in range(1, steps + 1):
                if getattr(goal, "_cancel_requested", False):
                    self._publish_feedback(goal.goal_id, PREEMPTED, 0.0, "preempted")
                    return
                t = step / steps
                interp = {}
                for joint, tgt in target.items():
                    start_val = current.get(joint, self.servo.get_current_value(joint) or 0.0)
                    interp[joint] = lerp(start_val, tgt, t)
                self.servo.set_pose(interp)
                # feedback at ~5Hz
                if step % max(1, int(self.control_hz/5)) == 0:
                    progress = ((k_index - 1) + (step / steps)) / total_k
                    self._publish_feedback(goal.goal_id, ACTIVE, progress, f"keyframe {k_index}/{total_k}")
                time.sleep(1.0 / self.control_hz)
            # reached keyframe
            current.update(target)
        self._publish_feedback(goal.goal_id, SUCCEEDED, 1.0, "sequence complete")

    def stop(self):
        self._stop_event.set()
        self._worker.join(timeout=1.0)
