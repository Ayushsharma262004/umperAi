## UmpirAI Command-Line Interface (CLI)

This document describes the command-line interface for the UmpirAI cricket umpiring system.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
  - [run](#run)
  - [calibrate](#calibrate)
  - [test](#test)
  - [config](#config)
  - [version](#version)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Installation

After installing UmpirAI, the CLI is available as:

```bash
# Using the Python module
python -m umpirai.cli

# Using the entry point script
python umpirai_cli.py

# If installed with setuptools entry points
umpirai
```

## Quick Start

```bash
# Create default configuration
python umpirai_cli.py config create

# Run with default settings
python umpirai_cli.py run

# Run with custom configuration and cameras
python umpirai_cli.py run --config config.yaml --cameras rtsp://camera1 rtsp://camera2
```

## Commands

### run

Run the UmpirAI system for live match umpiring.

**Usage:**
```bash
umpirai run [OPTIONS]
```

**Options:**
- `--config, -c PATH` - Path to configuration file
- `--calibration PATH` - Path to calibration file
- `--cameras SOURCE [SOURCE ...]` - Camera sources (RTSP URLs, USB IDs, or video files)
- `--duration MINUTES` - Run duration in minutes (default: run until interrupted)
- `--verbose, -v` - Enable verbose logging

**Examples:**
```bash
# Run with default configuration
umpirai run

# Run with custom configuration
umpirai run --config my_config.yaml

# Run with multiple cameras
umpirai run --cameras rtsp://192.168.1.100:554/stream rtsp://192.168.1.101:554/stream

# Run with USB cameras
umpirai run --cameras 0 1

# Run for specific duration
umpirai run --duration 120  # Run for 120 minutes

# Run with calibration
umpirai run --calibration pitch_calibration.json --cameras rtsp://camera1

# Verbose mode
umpirai run --verbose
```

**Camera Source Formats:**
- RTSP stream: `rtsp://192.168.1.100:554/stream`
- HTTP stream: `http://192.168.1.100:8080/video`
- USB camera: `0`, `1`, `2` (device index)
- Video file: `match_recording.mp4`

### calibrate

Run calibration mode to set up pitch boundaries and camera parameters.

**Usage:**
```bash
umpirai calibrate [OPTIONS]
```

**Options:**
- `--config, -c PATH` - Path to configuration file
- `--camera SOURCE` - Camera source for calibration (required)
- `--output, -o PATH` - Output calibration file path (default: calibration.json)
- `--verbose, -v` - Enable verbose logging

**Examples:**
```bash
# Calibrate with RTSP camera
umpirai calibrate --camera rtsp://192.168.1.100:554/stream

# Calibrate with USB camera
umpirai calibrate --camera 0 --output my_calibration.json

# Calibrate with custom configuration
umpirai calibrate --config config.yaml --camera rtsp://camera1
```

**Calibration Process:**
1. Start calibration mode with a camera
2. Mark the four corners of the pitch boundary
3. Mark the bowling and batting crease lines
4. Mark the stump positions
5. Define wide guidelines
6. Verify the calibration overlay
7. Save calibration to file

### test

Test the system with recorded cricket match footage.

**Usage:**
```bash
umpirai test [OPTIONS]
```

**Options:**
- `--config, -c PATH` - Path to configuration file
- `--video PATH` - Path to test video file (required)
- `--calibration PATH` - Path to calibration file
- `--verbose, -v` - Enable verbose logging

**Examples:**
```bash
# Test with video file
umpirai test --video match_recording.mp4

# Test with calibration
umpirai test --video match.mp4 --calibration pitch_calibration.json

# Test with custom configuration
umpirai test --config test_config.yaml --video match.mp4

# Verbose test mode
umpirai test --video match.mp4 --verbose
```

### config

Manage system configuration files.

**Usage:**
```bash
umpirai config <action> [OPTIONS]
```

**Actions:**
- `create` - Create default configuration file
- `validate` - Validate configuration file
- `show` - Display configuration summary

#### config create

Create a default configuration file.

**Usage:**
```bash
umpirai config create [OPTIONS]
```

**Options:**
- `--output, -o PATH` - Output configuration file path (default: config.yaml)
- `--verbose, -v` - Enable verbose logging

**Examples:**
```bash
# Create default configuration
umpirai config create

# Create with custom name
umpirai config create --output my_config.yaml

# Create in specific directory
umpirai config create --output configs/production.yaml
```

#### config validate

Validate a configuration file.

**Usage:**
```bash
umpirai config validate [OPTIONS]
```

**Options:**
- `--file, -f PATH` - Configuration file to validate
- `--verbose, -v` - Enable verbose logging

**Examples:**
```bash
# Validate default configuration
umpirai config validate

# Validate specific file
umpirai config validate --file my_config.yaml

# Verbose validation
umpirai config validate --file config.yaml --verbose
```

#### config show

Display configuration summary.

**Usage:**
```bash
umpirai config show [OPTIONS]
```

**Options:**
- `--file, -f PATH` - Configuration file to show
- `--verbose, -v` - Enable verbose logging

**Examples:**
```bash
# Show default configuration
umpirai config show

# Show specific configuration
umpirai config show --file my_config.yaml
```

### version

Show version information.

**Usage:**
```bash
umpirai version
```

**Example:**
```bash
$ umpirai version
UmpirAI - AI-Powered Cricket Umpiring System
Version: 0.1.0
Python: 3.10.0
```

## Examples

### Basic Match Setup

```bash
# 1. Create configuration
umpirai config create --output match_config.yaml

# 2. Edit configuration as needed
# (edit match_config.yaml with your preferred settings)

# 3. Run calibration
umpirai calibrate --camera rtsp://camera1 --output pitch_cal.json

# 4. Start match umpiring
umpirai run --config match_config.yaml --calibration pitch_cal.json \
  --cameras rtsp://camera1 rtsp://camera2
```

### Multi-Camera Setup

```bash
# Run with 4 cameras for maximum accuracy
umpirai run \
  --cameras \
    rtsp://192.168.1.100:554/stream \
    rtsp://192.168.1.101:554/stream \
    rtsp://192.168.1.102:554/stream \
    rtsp://192.168.1.103:554/stream \
  --calibration pitch_calibration.json
```

### Testing and Development

```bash
# Test with recorded match
umpirai test --video test_match.mp4 --calibration test_cal.json

# Run in verbose mode for debugging
umpirai run --verbose --cameras 0

# Validate configuration before use
umpirai config validate --file production_config.yaml
```

### Production Deployment

```bash
# Create production configuration
umpirai config create --output production.yaml

# Edit production.yaml:
# - Set appropriate log levels
# - Configure performance thresholds
# - Enable/disable features as needed

# Run with production settings
umpirai run \
  --config production.yaml \
  --calibration venue_calibration.json \
  --cameras rtsp://cam1 rtsp://cam2 \
  --duration 180  # 3-hour match
```

## Environment Variables

The CLI respects the following environment variables:

- `UMPIRAI_CONFIG` - Default configuration file path
- `UMPIRAI_CALIBRATION` - Default calibration file path
- `UMPIRAI_LOG_LEVEL` - Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Example:**
```bash
export UMPIRAI_CONFIG=production.yaml
export UMPIRAI_CALIBRATION=venue_cal.json
export UMPIRAI_LOG_LEVEL=INFO

umpirai run --cameras rtsp://camera1
```

## Exit Codes

The CLI uses the following exit codes:

- `0` - Success
- `1` - General error
- `2` - Configuration error
- `3` - Calibration error
- `4` - Camera error
- `130` - Interrupted by user (Ctrl+C)

## Logging

By default, logs are written to:
- Console (stdout) - INFO level and above
- Log files - As configured in configuration file

Use `--verbose` flag to enable DEBUG level logging to console.

**Log Locations:**
- Event logs: `logs/events_YYYYMMDD.jsonl`
- Performance logs: `logs/performance_YYYYMMDD.jsonl`
- System logs: `logs/system_YYYYMMDD.log`

## Troubleshooting

### Command Not Found

```bash
umpirai: command not found
```

**Solution:** Use the full Python command:
```bash
python umpirai_cli.py <command>
```

Or add the script directory to your PATH.

### Configuration File Not Found

```bash
FileNotFoundError: No configuration file found
```

**Solution:** Create a configuration file:
```bash
umpirai config create
```

Or specify the configuration file explicitly:
```bash
umpirai run --config /path/to/config.yaml
```

### Camera Connection Failed

```bash
Error: Failed to connect to camera
```

**Solutions:**
1. Check camera URL/device ID is correct
2. Verify network connectivity for RTSP cameras
3. Check camera permissions for USB devices
4. Test camera with another application first

### Calibration Required

```bash
Error: No calibration loaded
```

**Solution:** Run calibration first or specify calibration file:
```bash
umpirai calibrate --camera rtsp://camera1 --output calibration.json
umpirai run --calibration calibration.json --cameras rtsp://camera1
```

### Permission Denied

```bash
PermissionError: [Errno 13] Permission denied
```

**Solutions:**
1. Check file/directory permissions
2. Run with appropriate user permissions
3. Check USB camera device permissions (Linux: add user to `video` group)

## See Also

- [Configuration Guide](CONFIGURATION.md) - Detailed configuration documentation
- [Calibration Guide](CALIBRATION.md) - Calibration process and best practices
- [API Documentation](API.md) - Python API for programmatic control
- [Deployment Guide](DEPLOYMENT.md) - Production deployment recommendations
