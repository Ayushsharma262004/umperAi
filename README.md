# UmpirAI - AI-Powered Cricket Umpiring System

An automated cricket umpiring system that uses computer vision and machine learning to detect and classify match events in real-time.

## Features

- **Real-time Video Processing**: Process video at 30+ FPS from multiple camera sources
- **Object Detection**: YOLOv8-based detection of cricket elements (ball, stumps, players, crease lines)
- **Ball Tracking**: Extended Kalman Filter for accurate trajectory tracking with occlusion handling
- **Automated Decisions**: Wide balls, no balls, dismissals (bowled, caught, LBW), and over completion
- **Multi-Camera Support**: Synchronized processing from up to 4 camera angles
- **Decision Confidence**: Confidence scoring with automatic flagging for manual review
- **Event Logging**: Comprehensive logging of all match events with video references

## Installation

### Prerequisites

- Python 3.10 or higher
- CUDA-capable GPU (recommended for real-time performance)

### Install from source

```bash
# Clone the repository
git clone https://github.com/umpirai/umpirai.git
cd umpirai

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Install for development

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
from umpirai import UmpirAISystem
from umpirai.config import ConfigManager

# Load configuration
config = ConfigManager.from_file("config.yaml")

# Initialize the system
system = UmpirAISystem(config)

# Add camera sources
system.add_camera("cam1", "rtsp://camera1.local/stream")
system.add_camera("cam2", "rtsp://camera2.local/stream")

# Calibrate the pitch
system.calibrate_pitch()

# Start processing
system.start()

# Process match events
for decision in system.process_match():
    print(f"Decision: {decision.event_type} (confidence: {decision.confidence:.2f})")

# Stop processing
system.stop()
```

## Project Structure

```
umpirai/
├── calibration/     # Pitch calibration management
├── config/          # Configuration management
├── decision/        # Decision engine components
├── detection/       # Object detection (YOLOv8)
├── logging/         # Event logging
├── models/          # Core data models
├── monitoring/      # Performance monitoring
├── output/          # Decision output formatting
├── tracking/        # Ball tracking (EKF)
└── video/           # Video processing and multi-camera sync
```

## Configuration

Create a `config.yaml` file:

```yaml
# Video Processing
target_fps: 30
frame_width: 1280
frame_height: 720

# Detection
detection_confidence_high: 0.90
detection_confidence_medium: 0.70
model_path: "models/yolov8m.pt"

# Decision Engine
decision_confidence_threshold: 0.80
wide_guideline_offset: 1.0

# Multi-Camera
max_cameras: 4
sync_tolerance_ms: 50.0
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=umpirai --cov-report=html

# Run property-based tests
pytest -m property
```

## Documentation

For detailed documentation, see:
- [Requirements Document](.kiro/specs/ai-auto-umpiring-system/requirements.md)
- [Design Document](.kiro/specs/ai-auto-umpiring-system/design.md)
- [Implementation Tasks](.kiro/specs/ai-auto-umpiring-system/tasks.md)

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please read CONTRIBUTING.md for guidelines.

## Acknowledgments

- YOLOv8 for object detection
- OpenCV for video processing
- Extended Kalman Filter for ball tracking
