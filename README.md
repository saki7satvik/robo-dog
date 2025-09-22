# RoboDog Motion & Behavior System

This project provides a modular motion engine and behavior manager for controlling a quadruped robot (RoboDog) using Python.

## Features
- Servo control via `ServoController` (see `servo_controller.py`)
- Motion sequencing and interpolation via `MotionEngine` (`motion_engine.py`)
- High-level behavior management via `BehaviorManager` (`behavior_manager.py`)
- Easy-to-edit behavior definitions in `behaviors.json`
- Example motion sequences in `dog_sequences.py`
- Test/demo scripts for motion and behavior execution

## File Overview
- `servo_controller.py`: Low-level servo control and pose management
- `motion_engine.py`: Executes pose and sequence goals with smooth interpolation
- `dog_sequences.py`: Example motion sequences for RoboDog
- `behavior_manager.py`: Loads and executes named behaviors from JSON
- `behaviors.json`: Defines named behaviors and their sequences
- `test.py`: Demo for MotionEngine and dog sequences
- `test_behavior_manager.py`: Demo for BehaviorManager and behaviors

## Usage

### 1. MotionEngine Demo
Run basic motion sequences:
```sh
python test.py
```

### 2. BehaviorManager Demo
Run named behaviors and tasks:
```sh
python test_behavior_manager.py
```

## Customizing Behaviors
- Edit `behaviors.json` to add or modify named behaviors.
- Each behavior is a sequence of keyframes with servo positions and durations.
- Servo names must match those in `servo_map_dog.json`.

## Adding New Sequences
- Add new sequences to `dog_sequences.py` for direct use with MotionEngine.

## Requirements
- Python 3.7+
- No hardware required for simulation mode (`simulate_if_no_hw=True`)
- For real hardware, ensure dependencies for servo control (e.g., Adafruit PCA9685 library) are installed.

## License
MIT License

## Author
Your Name Here
