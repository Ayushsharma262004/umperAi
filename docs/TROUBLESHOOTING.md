# UmpirAI Troubleshooting Guide

This guide helps diagnose and resolve common issues with the UmpirAI system.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Camera Issues](#camera-issues)
- [Detection Issues](#detection-issues)
- [Performance Issues](#performance-issues)
- [Decision Issues](#decision-issues)
- [Configuration Issues](#configuration-issues)
- [Known Limitations](#known-limitations)

## Quick Diagnostics

### System Health Check

```bash
# Check Python version
python --version  # Should be 3.10+

# Check dependencies
pip list | grep -E "opencv|torch|ultralytics"

# Run system tests
pytest tests/ -v

# Check configuration
python umpirai_cli.py config validate

# Test with sample video
python umpirai_cli.py test --video sample.mp4
```

### Common Quick Fixes

1. **Restart the system**
2. **Check camera connections**
3. **Verify configuration file**
4. **Check disk space**
5. **Review system logs**

## Installation Issues

### Issue: Python Version Too Old

**Symptoms:**
```
ERROR: Python 3.9 is not supported
```

**Solution:**
```bash
# Install Python 3.10 or higher
# Ubuntu:
sudo apt-get install python3.10

# macOS:
brew install python@3.11

# Windows: Download from python.org
```

### Issue: OpenCV Installation Fails

**Symptoms:**
```
ERROR: Failed building wheel for opencv-python
```

**Solutions:**

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-dev libopencv-dev
pip install opencv-python
```

**macOS:**
```bash
brew install opencv
pip install opencv-python
```

**Windows:**
```bash
# Install Visual C++ Redistributable first
pip install opencv-python
```

### Issue: PyTorch CUDA Not Available

**Symptoms:**
```python
torch.cuda.is_available()  # Returns False
```

**Solutions:**
```bash
# Install CUDA-enabled PyTorch
pip uninstall torch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Verify CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

### Issue: YOLOv8 Model Download Fails

**Symptoms:**
```
ERROR: Failed to download yolov8m.pt
```

**Solutions:**
```bash
# Download manually
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt

# Or use Python
python -c "from ultralytics import YOLO; YOLO('yolov8m.pt')"

# Specify path in config
# config.yaml:
detection:
  model_path: "/path/to/yolov8m.pt"
```

## Camera Issues

### Issue: Camera Not Detected

**Symptoms:**
```
ERROR: Failed to connect to camera
```

**Diagnosis:**
```bash
# Test camera directly
# For USB camera:
python -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened())"

# For RTSP camera:
ffplay rtsp://camera_ip:554/stream
```

**Solutions:**

**USB Camera:**
```bash
# Linux: Check permissions
sudo usermod -a -G video $USER
# Log out and back in

# Check device
ls -l /dev/video*

# Test with different index
python umpirai_cli.py run --cameras 0 1 2
```

**RTSP Camera:**
```bash
# Verify URL format
rtsp://username:password@ip:port/stream

# Test connectivity
ping camera_ip

# Check firewall
sudo ufw allow 554/tcp  # Linux
```

### Issue: Camera Feed Freezes

**Symptoms:**
- Video stops updating
- FPS drops to 0
- "Camera disconnected" message

**Solutions:**
1. **Check network stability**
   ```bash
   ping -c 100 camera_ip
   ```

2. **Reduce resolution**
   ```yaml
   # config.yaml
   video:
     resolution_width: 640
     resolution_height: 480
   ```

3. **Check bandwidth**
   ```bash
   # Monitor network usage
   iftop  # Linux
   ```

4. **Restart camera**
   - Power cycle camera
   - Check camera settings
   - Verify stream format

### Issue: Poor Video Quality

**Symptoms:**
- Blurry images
- Low frame rate
- Compression artifacts

**Solutions:**
1. **Adjust camera settings**
   - Increase bitrate
   - Adjust focus
   - Improve lighting

2. **Check network bandwidth**
   ```yaml
   # Reduce resolution if needed
   video:
     resolution_width: 1280
     resolution_height: 720
   ```

3. **Use wired connection**
   - Prefer Ethernet over WiFi
   - Check cable quality

## Detection Issues

### Issue: Low Detection Accuracy

**Symptoms:**
- Many uncertain decisions
- Missed ball detections
- False positives

**Diagnosis:**
```bash
# Check detection confidence in logs
grep "confidence" logs/events_*.jsonl | tail -20
```

**Solutions:**

1. **Improve Lighting**
   - Ensure adequate lighting
   - Avoid backlighting
   - Use consistent lighting

2. **Adjust Confidence Thresholds**
   ```yaml
   # config.yaml
   detection:
     confidence_threshold_low: 0.6  # Lower for more detections
     confidence_threshold_high: 0.85  # Adjust as needed
   ```

3. **Recalibrate System**
   ```bash
   python umpirai_cli.py calibrate --camera rtsp://camera1
   ```

4. **Check Camera Position**
   - Ensure clear view of pitch
   - Avoid obstructions
   - Adjust camera angles

### Issue: Ball Not Detected

**Symptoms:**
- "Ball not found" messages
- Tracking failures
- No trajectory data

**Solutions:**

1. **Check Ball Visibility**
   - Ensure ball is in frame
   - Check lighting on ball
   - Verify ball color contrast

2. **Adjust Detection Settings**
   ```yaml
   detection:
     confidence_threshold_low: 0.5  # Lower threshold
   ```

3. **Use Multiple Cameras**
   - Add more camera angles
   - Improves detection reliability

4. **Check Model**
   - Verify model file exists
   - Try different model variant
   - Retrain model if needed

### Issue: False Detections

**Symptoms:**
- Detecting non-existent objects
- Misclassifying objects
- Spurious decisions

**Solutions:**

1. **Increase Confidence Threshold**
   ```yaml
   detection:
     confidence_threshold_low: 0.75  # Higher threshold
   ```

2. **Improve Calibration**
   - Recalibrate pitch boundaries
   - Verify stump positions
   - Check wide guidelines

3. **Filter Background**
   - Remove moving objects from background
   - Use consistent background
   - Avoid crowd movement in frame

## Performance Issues

### Issue: Low FPS

**Symptoms:**
```
FPS: 15.2 (Alert: Below 25)
```

**Diagnosis:**
```bash
# Check system resources
top  # Linux/macOS
# or
Task Manager  # Windows

# Check GPU usage
nvidia-smi  # If NVIDIA GPU
```

**Solutions:**

1. **Reduce Resolution**
   ```yaml
   video:
     resolution_width: 640
     resolution_height: 480
     target_fps: 15
   ```

2. **Use GPU Acceleration**
   ```bash
   # Verify GPU is being used
   python -c "import torch; print(torch.cuda.is_available())"
   ```

3. **Reduce Camera Count**
   ```yaml
   detection:
     max_cameras: 1  # Use fewer cameras
   ```

4. **Close Other Applications**
   - Free up system resources
   - Stop unnecessary services

5. **Upgrade Hardware**
   - Add more RAM
   - Use faster CPU
   - Add GPU

### Issue: High Latency

**Symptoms:**
```
Latency: 2500ms (Alert: Above 2000ms)
```

**Solutions:**

1. **Optimize Processing**
   ```yaml
   tracking:
     trajectory_history_size: 15  # Reduce from 30
   ```

2. **Disable Non-Essential Detectors**
   ```yaml
   decision:
     enable_lbw_detector: false  # If not needed
   ```

3. **Check Network Latency**
   ```bash
   ping camera_ip
   ```

4. **Use Local Cameras**
   - Prefer USB over network cameras
   - Reduce network hops

### Issue: High Memory Usage

**Symptoms:**
```
Memory: 95% (Alert: Above 90%)
```

**Solutions:**

1. **Reduce Buffer Size**
   ```yaml
   video:
     buffer_size_seconds: 1.0  # Reduce from 2.0
   ```

2. **Limit History**
   ```yaml
   tracking:
     trajectory_history_size: 15
   performance:
     metrics_history_size: 50
   ```

3. **Restart System Periodically**
   - Clear memory leaks
   - Fresh start

4. **Add More RAM**
   - Upgrade system memory

### Issue: CPU Overload

**Symptoms:**
```
CPU: 98% (High usage)
```

**Solutions:**

1. **Use GPU**
   - Enable CUDA if available
   - Offload processing to GPU

2. **Reduce Processing Load**
   - Lower resolution
   - Reduce FPS
   - Fewer cameras

3. **Optimize Configuration**
   ```yaml
   video:
     target_fps: 15
     resolution_width: 640
   ```

## Decision Issues

### Issue: Incorrect Wide Ball Decisions

**Symptoms:**
- Legal deliveries called wide
- Wide balls not detected

**Solutions:**

1. **Check Calibration**
   - Verify wide guidelines
   - Check batsman stance detection
   - Recalibrate if needed

2. **Adjust Wide Guidelines**
   ```yaml
   decision:
     wide_guideline_offset: 1.2  # Adjust from 1.0
   ```

3. **Review Batsman Movement**
   ```yaml
   decision:
     batsman_movement_threshold: 0.3  # More sensitive
   ```

### Issue: Incorrect No Ball Decisions

**Symptoms:**
- Legal deliveries called no ball
- No balls not detected

**Solutions:**

1. **Check Crease Calibration**
   - Verify crease line position
   - Recalibrate crease

2. **Check Foot Detection**
   - Ensure clear view of bowler's feet
   - Improve lighting on crease area

3. **Review Decisions**
   - Check video evidence
   - Verify foot position

### Issue: LBW Decisions Uncertain

**Symptoms:**
- Many LBW decisions flagged for review
- Low confidence scores

**Solutions:**

1. **Improve Trajectory Tracking**
   - Use multiple cameras
   - Ensure clear ball visibility
   - Check tracking parameters

2. **Verify Calibration**
   - Check stump positions
   - Verify pitch dimensions

3. **Review Manually**
   - Use trajectory visualization
   - Check all three LBW conditions

## Configuration Issues

### Issue: Configuration File Not Found

**Symptoms:**
```
FileNotFoundError: No configuration file found
```

**Solutions:**
```bash
# Create default configuration
python umpirai_cli.py config create

# Or specify path
python umpirai_cli.py run --config /path/to/config.yaml
```

### Issue: Invalid Configuration

**Symptoms:**
```
ValueError: target_fps must be positive
```

**Solutions:**
```bash
# Validate configuration
python umpirai_cli.py config validate --file config.yaml

# Check specific values
python umpirai_cli.py config show
```

### Issue: Configuration Not Applied

**Symptoms:**
- Changes not taking effect
- System using default values

**Solutions:**
1. **Verify file path**
   ```bash
   python umpirai_cli.py run --config config.yaml
   ```

2. **Check file format**
   - Ensure valid YAML/JSON
   - Check indentation (YAML)

3. **Restart system**
   - Configuration loaded at startup

## Known Limitations

### Current Limitations

1. **Occlusion Handling**
   - Limited to 10 frames (333ms at 30 FPS)
   - May lose tracking in heavy occlusion

2. **Lighting Conditions**
   - Performance degrades in poor lighting
   - Requires consistent lighting

3. **Camera Requirements**
   - Minimum 720p resolution recommended
   - 30 FPS required for accurate tracking

4. **Processing Speed**
   - Real-time processing requires adequate hardware
   - May need GPU for multiple cameras

5. **Decision Accuracy**
   - Not 100% accurate
   - Manual review recommended for critical decisions

### Workarounds

1. **For Occlusion**
   - Use multiple camera angles
   - Position cameras to minimize occlusion

2. **For Lighting**
   - Use artificial lighting
   - Avoid direct sunlight
   - Use consistent lighting setup

3. **For Performance**
   - Use GPU acceleration
   - Reduce resolution if needed
   - Limit number of cameras

## Getting Additional Help

### Log Files

Check log files for detailed error information:
```bash
# Event logs
cat logs/events_YYYYMMDD.jsonl

# Performance logs
cat logs/performance_YYYYMMDD.jsonl

# System logs
cat logs/system_YYYYMMDD.log
```

### Debug Mode

Run in verbose mode for detailed output:
```bash
python umpirai_cli.py run --verbose
```

### Support Channels

1. **Documentation**: Check all documentation files
2. **GitHub Issues**: Search existing issues
3. **GitHub Discussions**: Ask questions
4. **Email Support**: support@umpirai.example.com

### Reporting Issues

When reporting issues, include:
- Python version
- Operating system
- Hardware specifications
- Configuration file
- Error messages and logs
- Steps to reproduce
- Expected vs actual behavior

## See Also

- [Installation Guide](INSTALLATION.md)
- [Operation Manual](OPERATION.md)
- [Configuration Guide](CONFIGURATION.md)
- [FAQ](FAQ.md)
