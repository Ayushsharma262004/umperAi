# UmpirAI System Testing Guide

This document provides comprehensive guidance for performing system testing with real cricket footage.

## Overview

System testing validates the complete UmpirAI system with real-world cricket match footage to ensure:
- All dismissal types are correctly detected
- Wide and no ball detection works accurately
- Multi-camera operation functions properly
- Error recovery scenarios are handled gracefully
- End-to-end latency meets requirements (<1 second)
- System can operate continuously for 120+ minutes

## Prerequisites

### Hardware Requirements
- **CPU**: Multi-core processor (4+ cores recommended)
- **RAM**: 16GB minimum, 32GB recommended
- **GPU**: NVIDIA GPU with CUDA support (optional but recommended)
- **Storage**: 100GB+ free space for test footage and logs

### Software Requirements
- Python 3.10+
- All dependencies installed (see `docs/INSTALLATION.md`)
- Calibrated system (see `docs/OPERATION.md`)
- Test cricket footage (see Test Footage Requirements below)

### Test Footage Requirements

Prepare cricket match footage covering:

1. **Wide Ball Scenarios** (minimum 20 examples)
   - Clear wide balls (>1m from batsman)
   - Marginal wide balls (near guideline)
   - Wide balls with batsman movement
   - Wide balls on both sides (off/leg)

2. **No Ball Scenarios** (minimum 20 examples)
   - Clear front-foot no balls
   - Marginal no balls (foot on line)
   - No balls with occluded foot position
   - No balls at different bowling speeds

3. **Dismissal Scenarios**
   - **Bowled** (minimum 15 examples)
     - Clean bowled
     - Bowled via deflection
     - Stumps hit but bails not dislodged
   - **LBW** (minimum 20 examples)
     - Clear LBW (pitched in line, hit in line, hitting stumps)
     - Umpire's call scenarios
     - Not out (pitched outside leg, impact outside off, missing stumps)
     - Bat-first scenarios
   - **Caught** (minimum 15 examples)
     - Clean catches
     - Catches after deflection
     - Dropped catches
     - Catches with ground contact

4. **Multi-Camera Scenarios** (if available)
   - Same delivery from 2+ camera angles
   - Occlusion in one camera, visible in another
   - Synchronized multi-camera footage

5. **Error Scenarios**
   - Poor lighting conditions
   - Camera shake or movement
   - Partial occlusions
   - Fast-paced action

## Test Execution

### Phase 1: Single Delivery Testing

Test individual deliveries to validate basic functionality.

#### Setup
```bash
# Create test data directory
mkdir -p test_data/single_deliveries

# Organize footage by scenario type
mkdir -p test_data/single_deliveries/{wide,no_ball,bowled,lbw,caught}
```

#### Execution
```python
# Run single delivery test
python scripts/test_single_delivery.py \
    --video test_data/single_deliveries/wide/wide_001.mp4 \
    --calibration calibration.json \
    --expected-decision WIDE \
    --output results/wide_001_result.json
```

#### Validation
- Compare system decision with expected decision
- Check confidence scores (should be >80% for clear cases)
- Verify decision latency (<1 second)
- Review trajectory visualization
- Check for uncertainty flags on marginal cases

### Phase 2: Over-by-Over Testing

Test complete overs to validate delivery counting and over completion.

#### Setup
```bash
mkdir -p test_data/overs
```

#### Execution
```python
# Run over test
python scripts/test_over.py \
    --video test_data/overs/over_001.mp4 \
    --calibration calibration.json \
    --expected-legal-deliveries 6 \
    --output results/over_001_result.json
```

#### Validation
- Verify legal delivery count matches expected
- Confirm over completion signal at 6 legal deliveries
- Check that extras (wides, no balls) don't increment counter
- Validate dismissals count as legal deliveries

### Phase 3: Multi-Camera Testing

Test multi-camera synchronization and fusion.

#### Setup
```bash
mkdir -p test_data/multi_camera
```

#### Execution
```python
# Run multi-camera test
python scripts/test_multi_camera.py \
    --videos test_data/multi_camera/delivery_cam1.mp4 \
                test_data/multi_camera/delivery_cam2.mp4 \
                test_data/multi_camera/delivery_cam3.mp4 \
    --calibration calibration_multi_camera.json \
    --output results/multi_camera_result.json
```

#### Validation
- Check synchronization quality (>80%)
- Verify detection fusion improves confidence
- Confirm 3D ball position triangulation
- Validate occlusion handling across views

### Phase 4: Continuous Operation Testing

Test system stability over extended periods.

#### Setup
```bash
mkdir -p test_data/full_match
```

#### Execution
```python
# Run continuous operation test (120 minutes)
python scripts/test_continuous_operation.py \
    --video test_data/full_match/match_footage.mp4 \
    --calibration calibration.json \
    --duration 7200 \
    --output results/continuous_operation_result.json
```

#### Validation
- Verify system runs for full duration without crashes
- Check memory usage remains stable (<90%)
- Confirm FPS maintains >25 throughout
- Validate latency stays <2 seconds
- Review error logs for any issues

### Phase 5: Error Recovery Testing

Test system resilience to various failure scenarios.

#### Test Cases

**Camera Disconnection**
```python
python scripts/test_camera_failure.py \
    --simulate-disconnect-at 60 \
    --reconnect-after 10 \
    --output results/camera_failure_result.json
```

**Low Confidence Scenarios**
```python
python scripts/test_low_confidence.py \
    --video test_data/difficult/poor_lighting.mp4 \
    --calibration calibration.json \
    --output results/low_confidence_result.json
```

**Occlusion Scenarios**
```python
python scripts/test_occlusion.py \
    --video test_data/difficult/heavy_occlusion.mp4 \
    --calibration calibration.json \
    --output results/occlusion_result.json
```

#### Validation
- Confirm system continues operation after camera reconnection
- Verify uncertainty flags on low confidence decisions
- Check graceful degradation modes activate appropriately
- Validate error logging captures diagnostic information

## Performance Metrics

### Target Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Detection Accuracy | >95% | Compare with ground truth |
| Decision Latency | <1 second | Timestamp analysis |
| Frame Rate | >30 FPS | Performance monitor |
| Synchronization Quality | >80% | Multi-camera sync metric |
| Continuous Operation | 120 minutes | Stability test |
| Memory Usage | <90% | Resource monitor |
| CPU Usage | <80% | Resource monitor |

### Measurement Tools

**Accuracy Measurement**
```python
python scripts/measure_accuracy.py \
    --results results/ \
    --ground-truth ground_truth.json \
    --output accuracy_report.json
```

**Latency Measurement**
```python
python scripts/measure_latency.py \
    --results results/ \
    --output latency_report.json
```

**Performance Profiling**
```python
python scripts/profile_performance.py \
    --video test_data/sample.mp4 \
    --calibration calibration.json \
    --output performance_profile.json
```

## Test Result Analysis

### Automated Analysis

Run the comprehensive test analysis script:

```bash
python scripts/analyze_test_results.py \
    --results-dir results/ \
    --ground-truth ground_truth.json \
    --output test_report.html
```

This generates:
- Accuracy metrics by decision type
- Confusion matrix
- Latency distribution
- Performance trends
- Error analysis
- Recommendations

### Manual Review

For each test case, review:

1. **Decision Correctness**
   - Does system decision match ground truth?
   - Is confidence score appropriate?
   - Are uncertainty flags correct?

2. **Trajectory Visualization**
   - Does ball path look realistic?
   - Are occlusion gaps handled properly?
   - Is 3D reconstruction accurate?

3. **Performance Metrics**
   - Is latency within target?
   - Is frame rate stable?
   - Are resources within limits?

4. **Error Handling**
   - Are errors logged properly?
   - Does system recover gracefully?
   - Are alerts triggered appropriately?

## Common Issues and Solutions

### Issue: Low Detection Accuracy

**Symptoms**: System misses ball or player detections

**Solutions**:
- Recalibrate cameras
- Adjust detection confidence thresholds
- Improve lighting conditions
- Retrain detection model with venue-specific data

### Issue: High Latency

**Symptoms**: Decisions take >1 second

**Solutions**:
- Reduce video resolution
- Enable GPU acceleration
- Optimize detection model (use YOLOv8n instead of YOLOv8m)
- Disable unnecessary features

### Issue: Poor Multi-Camera Sync

**Symptoms**: Sync quality <80%

**Solutions**:
- Ensure cameras have similar frame rates
- Check network latency for RTSP streams
- Recalibrate temporal offsets
- Use hardware-synchronized cameras

### Issue: Memory Leaks

**Symptoms**: Memory usage increases over time

**Solutions**:
- Check frame buffer cleanup
- Verify trajectory history limits
- Review log retention settings
- Profile memory usage to identify leaks

## Test Data Management

### Ground Truth Annotation

Create ground truth annotations for test footage:

```json
{
  "video_id": "wide_001",
  "deliveries": [
    {
      "timestamp": 5.2,
      "decision_type": "WIDE",
      "confidence": 1.0,
      "details": {
        "ball_position_at_crease": {"x": 20.12, "y": 2.8, "z": 0.0},
        "batsman_position": {"x": 20.12, "y": 1.525, "z": 0.0},
        "wide_guideline_left": 0.525,
        "wide_guideline_right": 2.525
      }
    }
  ]
}
```

### Test Result Storage

Store test results in structured format:

```
results/
├── single_deliveries/
│   ├── wide_001_result.json
│   ├── no_ball_001_result.json
│   └── ...
├── overs/
│   ├── over_001_result.json
│   └── ...
├── multi_camera/
│   ├── multi_camera_001_result.json
│   └── ...
├── continuous_operation/
│   ├── continuous_001_result.json
│   └── ...
└── error_recovery/
    ├── camera_failure_001_result.json
    └── ...
```

## Reporting

### Test Summary Report

Generate a comprehensive test summary:

```bash
python scripts/generate_test_report.py \
    --results-dir results/ \
    --ground-truth ground_truth.json \
    --output test_summary_report.pdf
```

Report includes:
- Executive summary
- Test coverage matrix
- Accuracy metrics by scenario
- Performance benchmarks
- Error analysis
- Recommendations for improvement

### Continuous Integration

Integrate system tests into CI/CD pipeline:

```yaml
# .github/workflows/system-test.yml
name: System Tests

on: [push, pull_request]

jobs:
  system-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run system tests
        run: python scripts/run_system_tests.py --quick
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: results/
```

## Next Steps

After completing system testing:

1. **Address Issues**: Fix any bugs or performance issues identified
2. **Optimize**: Proceed to task 28.3 (Performance Optimization)
3. **Document**: Update known limitations in documentation
4. **Deploy**: Prepare system for production deployment

## Support

For issues or questions:
- Review `docs/TROUBLESHOOTING.md`
- Check system logs in `logs/`
- Contact development team

---

**Note**: This testing guide assumes availability of real cricket footage. For initial development and testing without real footage, use the simulation framework in `scripts/simulate_cricket_footage.py`.
