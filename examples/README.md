# UmpirAI Examples

This directory contains example scripts demonstrating how to use the UmpirAI system in various configurations.

## Prerequisites

Before running these examples, ensure you have:

1. Installed UmpirAI and all dependencies (see `docs/INSTALLATION.md`)
2. Created a configuration file (`config.yaml`)
3. Performed camera calibration (see `docs/OPERATION.md` or run `custom_calibration.py`)

## Examples

### 1. Basic Single-Camera Setup (`basic_single_camera.py`)

Demonstrates the simplest UmpirAI setup with a single camera.

**Use case**: Practice sessions, training, or venues with limited camera infrastructure.

**Features**:
- Single camera video processing
- Basic decision making (wide, no ball, dismissals)
- Performance monitoring
- Log export

**Usage**:
```bash
python examples/basic_single_camera.py
```

**Requirements**:
- One camera (RTSP stream or USB/HDMI capture)
- Calibration file: `calibration_single_camera.json`
- Configuration file: `config.yaml`

---

### 2. Multi-Camera Setup (`multi_camera_setup.py`)

Demonstrates advanced multi-camera setup with synchronized views for enhanced accuracy.

**Use case**: Professional matches, tournaments, or venues requiring high accuracy.

**Features**:
- Multiple synchronized cameras
- Multi-view detection fusion
- 3D ball position triangulation
- Camera synchronization quality monitoring
- Automatic camera failure handling
- Training data export from overrides

**Usage**:
```bash
python examples/multi_camera_setup.py
```

**Requirements**:
- Multiple cameras (3+ recommended)
- Calibration file: `calibration_multi_camera.json`
- Configuration file: `config.yaml` with multi-camera settings

**Camera placement recommendations**:
- Camera 1: Bowler's end (behind bowler)
- Camera 2: Side-on view (perpendicular to pitch)
- Camera 3: Batsman's end (behind batsman)
- Optional Camera 4: Elevated view (for LBW decisions)

---

### 3. Custom Calibration (`custom_calibration.py`)

Interactive tool for performing custom calibration of the UmpirAI system.

**Use case**: Initial setup, new venue, or recalibration after camera repositioning.

**Features**:
- Pitch boundary definition
- Crease line marking
- Stump position specification
- Wide guideline configuration
- Camera homography calculation
- Calibration validation
- Save/load calibration files

**Usage**:
```bash
python examples/custom_calibration.py
```

**Process**:
1. Define pitch dimensions (standard or custom)
2. Mark crease lines (bowling, popping, return)
3. Specify stump positions
4. Set wide guidelines
5. Capture reference frame from camera
6. Click on known pitch points for homography
7. Validate and save calibration

**Output**: `calibration.json` (or custom filename)

---

### 4. Decision Review Workflow (`decision_review_workflow.py`)

Demonstrates the decision review and override system for manual verification.

**Use case**: Matches requiring human oversight, training the system, or collecting feedback data.

**Features**:
- Real-time decision monitoring
- Video replay for review
- Decision override with justification
- Multi-camera view comparison
- Ball trajectory visualization
- Detection confidence timeline
- Review session reporting
- Override data export for model improvement

**Usage**:
```bash
python examples/decision_review_workflow.py
```

**Workflow**:
1. System makes a decision
2. If decision requires review (low confidence or critical type):
   - Display decision details
   - Show video replay
   - Present options: accept, override, or request more info
3. If override selected:
   - Choose new decision type
   - Provide justification
   - Record override for training data
4. Generate review session report

**Output**:
- `review_data.json` - Override data for model improvement
- `match_logs_with_reviews.jsonl` - Complete event logs

---

## Configuration

All examples use a `config.yaml` file. Create one from the template:

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` to match your setup:
- Camera URLs/sources
- Detection thresholds
- Tracking parameters
- Output preferences
- Performance settings

See `docs/CONFIGURATION.md` for detailed configuration options.

---

## Calibration Files

Each example requires appropriate calibration:

- **Single camera**: `calibration_single_camera.json`
- **Multi-camera**: `calibration_multi_camera.json`

Generate calibration files using `custom_calibration.py` or the CLI:

```bash
python umpirai_cli.py calibrate --output calibration.json
```

---

## Common Issues

### Camera Connection Failed
- Verify camera URL/device path
- Check network connectivity for RTSP streams
- Ensure camera is powered on and accessible

### Low Frame Rate
- Reduce video resolution in config
- Disable unnecessary features
- Check system resources (CPU/GPU/memory)

### Poor Detection Accuracy
- Recalibrate cameras
- Adjust detection confidence thresholds
- Improve lighting conditions
- Add more camera views (multi-camera setup)

### Synchronization Issues (Multi-Camera)
- Ensure cameras have similar frame rates
- Check network latency for RTSP streams
- Recalibrate temporal offsets
- Use hardware-synchronized cameras if available

See `docs/TROUBLESHOOTING.md` for more solutions.

---

## Next Steps

After running these examples:

1. **Customize configuration** for your specific needs
2. **Perform thorough calibration** for your venue
3. **Test with recorded footage** before live use
4. **Review and tune parameters** based on performance
5. **Set up monitoring and alerting** for production use

For detailed operation instructions, see `docs/OPERATION.md`.

---

## Support

For issues, questions, or contributions:
- Check documentation in `docs/`
- Review troubleshooting guide
- Submit issues on the project repository

---

## License

These examples are part of the UmpirAI project and follow the same license.
