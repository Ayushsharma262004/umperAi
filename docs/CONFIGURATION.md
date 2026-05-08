# UmpirAI Configuration Guide

This document describes the configuration system for the UmpirAI cricket umpiring system.

## Table of Contents

- [Overview](#overview)
- [Configuration File Format](#configuration-file-format)
- [Configuration Sections](#configuration-sections)
- [Loading Configuration](#loading-configuration)
- [Creating Custom Configurations](#creating-custom-configurations)
- [Configuration Validation](#configuration-validation)

## Overview

UmpirAI uses a hierarchical configuration system that allows you to customize all aspects of the system's behavior. Configuration can be provided in YAML or JSON format.

## Configuration File Format

UmpirAI supports two configuration file formats:

### YAML Format (Recommended)
```yaml
video:
  target_fps: 30
  resolution_width: 1280
  resolution_height: 720

detection:
  model_path: "yolov8m.pt"
  confidence_threshold_high: 0.9
```

### JSON Format
```json
{
  "video": {
    "target_fps": 30,
    "resolution_width": 1280,
    "resolution_height": 720
  },
  "detection": {
    "model_path": "yolov8m.pt",
    "confidence_threshold_high": 0.9
  }
}
```

## Configuration Sections

### Video Configuration

Controls video capture and preprocessing.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_fps` | int | 30 | Target frames per second for video processing |
| `resolution_width` | int | 1280 | Video resolution width in pixels |
| `resolution_height` | int | 720 | Video resolution height in pixels |
| `buffer_size_seconds` | float | 2.0 | Frame buffer size in seconds |
| `exposure_adjustment_threshold` | float | 0.3 | Threshold for automatic exposure adjustment (0-1) |
| `gamma_correction` | bool | true | Enable gamma correction for lighting changes |

### Detection Configuration

Controls object detection behavior.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_path` | str | "yolov8m.pt" | Path to YOLOv8 model file |
| `confidence_threshold_high` | float | 0.9 | High confidence threshold (≥90%) |
| `confidence_threshold_medium` | float | 0.7 | Medium confidence threshold (70-90%) |
| `confidence_threshold_low` | float | 0.5 | Low confidence threshold (<70%) |
| `enable_multi_view_fusion` | bool | true | Enable multi-camera detection fusion |
| `max_cameras` | int | 4 | Maximum number of cameras supported (1-4) |

### Tracking Configuration

Controls ball tracking and trajectory prediction.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_occlusion_frames` | int | 10 | Maximum frames to predict during occlusion |
| `trajectory_history_size` | int | 30 | Number of positions to store in trajectory history |
| `process_noise` | float | 0.1 | EKF process noise parameter |
| `measurement_noise` | float | 5.0 | EKF measurement noise (pixels) |
| `gravity` | float | 9.81 | Gravity constant (m/s²) |
| `air_resistance_coefficient` | float | 0.47 | Air resistance coefficient for ball |

### Decision Configuration

Controls decision engine behavior.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `confidence_review_threshold` | float | 0.8 | Confidence threshold for manual review (<80%) |
| `wide_guideline_offset` | float | 1.0 | Wide guideline offset from batsman (meters) |
| `batsman_movement_threshold` | float | 0.5 | Threshold for batsman movement detection (meters) |
| `fielder_control_frames` | int | 3 | Frames required to confirm fielder control |
| `ground_contact_height_threshold` | float | 0.1 | Height threshold for ground contact detection (meters) |
| `enable_wide_detector` | bool | true | Enable wide ball detection |
| `enable_no_ball_detector` | bool | true | Enable no ball detection |
| `enable_bowled_detector` | bool | true | Enable bowled dismissal detection |
| `enable_caught_detector` | bool | true | Enable caught dismissal detection |
| `enable_lbw_detector` | bool | true | Enable LBW detection |

### Output Configuration

Controls decision output and display.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_text_display` | bool | true | Enable on-screen text display |
| `enable_audio_announcement` | bool | false | Enable audio announcements (text-to-speech) |
| `enable_visual_indicators` | bool | true | Enable color-coded visual indicators |
| `decision_latency_target_ms` | float | 500.0 | Target decision latency (milliseconds) |
| `decision_latency_max_ms` | float | 1000.0 | Maximum acceptable decision latency (milliseconds) |

### Logging Configuration

Controls system logging.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `log_directory` | str | "logs" | Directory for log files |
| `log_level` | str | "INFO" | Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `retention_days` | int | 30 | Number of days to retain logs |
| `enable_event_logging` | bool | true | Enable match event logging |
| `enable_performance_logging` | bool | true | Enable performance metrics logging |
| `log_format` | str | "jsonl" | Log format: jsonl, json, or text |

### Performance Configuration

Controls performance monitoring and alerting.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fps_alert_threshold` | float | 25.0 | Alert if FPS drops below this value |
| `latency_alert_threshold_ms` | float | 2000.0 | Alert if processing latency exceeds this (ms) |
| `detection_accuracy_alert_threshold` | float | 0.8 | Alert if detection accuracy drops below this |
| `memory_alert_threshold_percent` | float | 90.0 | Alert if memory usage exceeds this percentage |
| `enable_performance_monitoring` | bool | true | Enable performance monitoring |
| `metrics_history_size` | int | 100 | Number of metrics to keep in history |

### Calibration Configuration

Controls calibration management.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `calibration_directory` | str | "calibrations" | Directory for calibration files |
| `auto_load_last_calibration` | bool | true | Automatically load last used calibration |
| `require_calibration_validation` | bool | true | Require calibration validation before use |

### System-Level Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_runtime_minutes` | int | 120 | Maximum continuous runtime (minutes) |
| `enable_graceful_degradation` | bool | true | Enable graceful degradation on errors |

## Loading Configuration

### From Python Code

```python
from umpirai.config import load_config

# Load from default locations (config.yaml, config.yml, config.json, etc.)
config = load_config()

# Load from specific file
config = load_config('my_config.yaml')

# Access configuration values
print(f"Target FPS: {config.video.target_fps}")
print(f"Model path: {config.detection.model_path}")
```

### Using ConfigManager

```python
from umpirai.config import ConfigManager

# Create manager
manager = ConfigManager()

# Load configuration
config = manager.load('config.yaml')

# Modify configuration
config.video.target_fps = 60

# Save modified configuration
manager.save(config, 'config_modified.yaml')
```

### Default Configuration Search Order

When no configuration file is specified, UmpirAI searches for configuration files in the following order:

1. `config.yaml`
2. `config.yml`
3. `config.json`
4. `umpirai_config.yaml`
5. `umpirai_config.yml`
6. `umpirai_config.json`

## Creating Custom Configurations

### Method 1: Copy Example File

```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your preferred settings
```

### Method 2: Create Programmatically

```python
from umpirai.config import SystemConfig, VideoConfig, DetectionConfig

# Create custom configuration
config = SystemConfig()

# Modify specific sections
config.video.target_fps = 60
config.video.resolution_width = 1920
config.video.resolution_height = 1080

config.detection.model_path = "custom_model.pt"
config.detection.confidence_threshold_high = 0.95

# Save configuration
from umpirai.config import save_config
save_config(config, 'my_custom_config.yaml')
```

### Method 3: Create Default Configuration

```python
from umpirai.config import create_default_config

# Create default configuration file
config = create_default_config('config.yaml')
```

## Configuration Validation

All configuration values are automatically validated when loaded. Invalid configurations will raise a `ValueError` with a descriptive error message.

### Validation Rules

- **Numeric ranges**: Values must be within specified ranges (e.g., confidence thresholds between 0 and 1)
- **Positive values**: Certain parameters must be positive (e.g., FPS, resolution)
- **Ordering constraints**: Some thresholds must be in ascending order (e.g., confidence thresholds)
- **Enum values**: Some parameters accept only specific values (e.g., log_level, log_format)

### Example Validation Errors

```python
from umpirai.config import SystemConfig

config = SystemConfig()

# This will raise ValueError: target_fps must be positive
config.video.target_fps = -1
config.validate()

# This will raise ValueError: Confidence thresholds must be in ascending order
config.detection.confidence_threshold_high = 0.5
config.detection.confidence_threshold_low = 0.9
config.validate()
```

## Environment-Specific Configurations

You can maintain different configurations for different environments:

```bash
# Development
config.dev.yaml

# Testing
config.test.yaml

# Production
config.prod.yaml
```

Load the appropriate configuration:

```python
import os
from umpirai.config import load_config

env = os.getenv('UMPIRAI_ENV', 'dev')
config = load_config(f'config.{env}.yaml')
```

## Best Practices

1. **Version Control**: Keep configuration files in version control, but exclude sensitive data
2. **Documentation**: Document any non-obvious configuration changes
3. **Validation**: Always validate configuration after manual edits
4. **Defaults**: Start with default configuration and only modify what's necessary
5. **Testing**: Test configuration changes in a non-production environment first
6. **Backup**: Keep backups of working configurations

## Troubleshooting

### Configuration File Not Found

```
FileNotFoundError: No configuration file found
```

**Solution**: Create a configuration file in one of the default locations or specify the path explicitly.

### Invalid Configuration Value

```
ValueError: target_fps must be positive
```

**Solution**: Check the configuration documentation for valid value ranges and correct the invalid value.

### YAML Parsing Error

```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Solution**: Check YAML syntax, especially indentation and colons. Use a YAML validator.

## See Also

- [CLI Documentation](CLI.md) - Command-line interface for configuration management
- [API Documentation](API.md) - Programmatic configuration API
- [Deployment Guide](DEPLOYMENT.md) - Production configuration recommendations
