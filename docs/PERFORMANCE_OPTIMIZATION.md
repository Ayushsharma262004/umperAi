# UmpirAI Performance Optimization Guide

This document provides comprehensive guidance for optimizing the UmpirAI system to meet performance requirements.

## Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Frame Rate | ≥30 FPS | <25 FPS |
| Processing Latency | <1 second | >2 seconds |
| CPU Usage | <80% | >90% |
| Memory Usage | <8GB | >12GB |
| GPU Memory | <4GB | >6GB |
| Detection Accuracy | >95% | <90% |

## Performance Profiling

### Running the Profiler

```bash
python scripts/profile_performance.py \
    --video test_data/sample.mp4 \
    --calibration calibration.json \
    --duration 60 \
    --output performance_profile.json \
    --profile-output performance.prof
```

### Analyzing Results

The profiler identifies:
- Time spent in each component (video, detection, tracking, decision)
- Resource usage (CPU, memory, GPU)
- Performance bottlenecks
- Optimization recommendations

### Interpreting Bottlenecks

**Detection Bottleneck** (>50% of pipeline time)
- Most common bottleneck
- Usually indicates model is too large or GPU not utilized

**Video Processing Bottleneck** (>30% of pipeline time)
- Video decoding is slow
- Resolution too high
- Preprocessing too complex

**Tracking Bottleneck** (>20% of pipeline time)
- EKF computations are expensive
- Trajectory history too long

## Optimization Strategies

### 1. Model Optimization

#### Use Smaller Detection Model

**Current**: YOLOv8m (medium)
**Optimized**: YOLOv8n (nano) or YOLOv8s (small)

```python
# In config.yaml
detection:
  model_path: "yolov8n.pt"  # Instead of yolov8m.pt
```

**Impact**:
- 3-5x faster inference
- Slight accuracy reduction (2-3%)
- Recommended for real-time applications

#### Model Quantization

Convert model to INT8 for faster inference:

```python
from ultralytics import YOLO

# Load model
model = YOLO('yolov8m.pt')

# Export to INT8
model.export(format='onnx', int8=True)
```

**Impact**:
- 2-4x faster inference
- Minimal accuracy loss (<1%)
- Requires ONNX Runtime

#### Model Pruning

Remove unnecessary model weights:

```python
import torch
from torch.nn.utils import prune

# Prune 30% of weights
for module in model.modules():
    if isinstance(module, torch.nn.Conv2d):
        prune.l1_unstructured(module, name='weight', amount=0.3)
```

**Impact**:
- 20-30% faster inference
- 1-2% accuracy reduction
- Requires retraining

### 2. Video Processing Optimization

#### Reduce Resolution

```python
# In config.yaml
video:
  target_resolution: [960, 540]  # Instead of [1280, 720]
```

**Impact**:
- 2x faster processing
- Minimal accuracy impact for most scenarios
- Recommended for multi-camera setups

#### Skip Frame Processing

Process every Nth frame:

```python
# In umpirai/video/video_processor.py
class VideoProcessor:
    def __init__(self, skip_frames=2):
        self.skip_frames = skip_frames
        self.frame_counter = 0
    
    def should_process_frame(self):
        self.frame_counter += 1
        return self.frame_counter % (self.skip_frames + 1) == 0
```

**Impact**:
- Proportional speedup (skip 2 = 3x faster)
- May miss fast events
- Use with caution for critical decisions

#### Hardware-Accelerated Decoding

Use GPU for video decoding:

```python
import cv2

# Enable CUDA backend
cv2.setUseOptimized(True)
cv2.ocl.setUseOpenCL(True)

# Use hardware decoder
cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)
```

**Impact**:
- 30-50% faster video decoding
- Requires compatible GPU
- May not work on all systems

#### Optimize Preprocessing

Disable unnecessary preprocessing:

```python
# In config.yaml
video:
  enable_gamma_correction: false
  enable_normalization: false
```

**Impact**:
- 10-20% faster video processing
- May affect detection accuracy in poor lighting

### 3. Detection Optimization

#### Batch Processing

Process multiple frames in a batch:

```python
# In umpirai/detection/object_detector.py
def detect_batch(self, frames):
    """Detect objects in multiple frames at once."""
    results = self.model(frames, stream=False)
    return [self._process_result(r) for r in results]
```

**Impact**:
- 20-40% faster for batch sizes 4-8
- Increases latency slightly
- Good for offline processing

#### Reduce Detection Classes

Only detect necessary classes:

```python
# In config.yaml
detection:
  enabled_classes: [0, 1, 2, 3]  # ball, stumps, batsman, bowler only
```

**Impact**:
- 10-15% faster inference
- Reduces false positives
- May limit functionality

#### Confidence Threshold Tuning

Increase confidence threshold to reduce post-processing:

```python
# In config.yaml
detection:
  confidence_threshold_low: 0.75  # Instead of 0.70
```

**Impact**:
- 5-10% faster post-processing
- May miss some detections
- Balance with accuracy requirements

### 4. Tracking Optimization

#### Reduce Trajectory History

```python
# In config.yaml
tracking:
  max_trajectory_length: 20  # Instead of 30
```

**Impact**:
- 20-30% faster tracking
- Sufficient for most scenarios
- May affect long-term predictions

#### Optimize EKF Computations

Use sparse matrices for EKF:

```python
from scipy.sparse import csr_matrix

# In umpirai/tracking/ball_tracker.py
class BallTracker:
    def _init_ekf(self):
        # Use sparse matrices for large state spaces
        self.P = csr_matrix(self.P)
        self.Q = csr_matrix(self.Q)
```

**Impact**:
- 15-25% faster EKF updates
- Significant for high-dimensional states
- Requires scipy

#### Adaptive Prediction

Only predict when necessary:

```python
# In umpirai/tracking/ball_tracker.py
def update(self, detection):
    if self.occlusion_frames > 0:
        # Only predict during occlusion
        self.predict()
    self.occlusion_frames = 0
    # Update with detection
```

**Impact**:
- 10-20% faster tracking
- No accuracy impact
- Recommended optimization

### 5. Decision Engine Optimization

#### Parallel Detector Execution

Run detectors in parallel:

```python
from concurrent.futures import ThreadPoolExecutor

# In umpirai/decision/decision_engine.py
class DecisionEngine:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def process_frame(self, frame, detections, trajectory):
        # Run detectors in parallel
        futures = [
            self.executor.submit(self.wide_detector.detect, ...),
            self.executor.submit(self.no_ball_detector.detect, ...),
            self.executor.submit(self.lbw_detector.detect, ...)
        ]
        results = [f.result() for f in futures]
```

**Impact**:
- 30-50% faster decision making
- Requires multi-core CPU
- Recommended for production

#### Cache Calibration Data

Cache frequently accessed calibration data:

```python
from functools import lru_cache

# In umpirai/calibration/calibration_manager.py
class CalibrationManager:
    @lru_cache(maxsize=128)
    def get_pitch_boundary(self):
        return self._pitch_boundary
```

**Impact**:
- 5-10% faster decision making
- Minimal memory overhead
- Easy to implement

### 6. Multi-Camera Optimization

#### Selective Camera Processing

Process only necessary cameras for each decision:

```python
# In umpirai/system/umpirai_system.py
def process_frame(self):
    # Use primary camera for most decisions
    primary_frame = self.video_processor.get_frame("primary")
    
    # Only use secondary cameras for critical decisions
    if self.requires_multi_camera_validation():
        all_frames = self.video_processor.get_synchronized_frames()
```

**Impact**:
- 40-60% faster for multi-camera setups
- Maintains accuracy for critical decisions
- Recommended for 3+ camera systems

#### Asynchronous Frame Capture

Capture frames asynchronously:

```python
import asyncio

# In umpirai/video/video_processor.py
async def capture_frame_async(self, camera_id):
    loop = asyncio.get_event_loop()
    frame = await loop.run_in_executor(None, self._capture_frame, camera_id)
    return frame
```

**Impact**:
- 20-30% faster frame capture
- Reduces synchronization overhead
- Requires async/await support

### 7. Memory Optimization

#### Limit Frame Buffer Size

```python
# In config.yaml
video:
  buffer_size_seconds: 1.0  # Instead of 2.0
```

**Impact**:
- 50% reduction in memory usage
- Sufficient for most scenarios
- May limit replay capability

#### Clear Old Trajectories

Regularly clear old trajectory data:

```python
# In umpirai/tracking/ball_tracker.py
def cleanup_old_trajectories(self, max_age_seconds=10):
    current_time = time.time()
    self.trajectories = [
        t for t in self.trajectories
        if current_time - t.timestamp < max_age_seconds
    ]
```

**Impact**:
- Prevents memory leaks
- 10-20% memory reduction over time
- Recommended for long-running systems

#### Use Memory-Mapped Files

For large datasets, use memory-mapped files:

```python
import numpy as np

# In umpirai/training/training_data_manager.py
def load_large_dataset(self, path):
    return np.load(path, mmap_mode='r')
```

**Impact**:
- Significant memory reduction for large datasets
- Slightly slower access
- Good for training data

### 8. GPU Optimization

#### Enable GPU Acceleration

```python
import torch

# In umpirai/detection/object_detector.py
class ObjectDetector:
    def __init__(self, model_path):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = YOLO(model_path).to(self.device)
```

**Impact**:
- 5-10x faster inference
- Requires NVIDIA GPU with CUDA
- Essential for real-time performance

#### Mixed Precision Training

Use FP16 for faster inference:

```python
# In umpirai/detection/object_detector.py
self.model.half()  # Convert to FP16
```

**Impact**:
- 2x faster inference on modern GPUs
- Minimal accuracy loss
- Requires GPU with Tensor Cores

#### Optimize Batch Size

Find optimal batch size for GPU:

```python
# Test different batch sizes
for batch_size in [1, 2, 4, 8, 16]:
    # Measure throughput
    throughput = measure_throughput(batch_size)
    print(f"Batch size {batch_size}: {throughput} FPS")
```

**Impact**:
- 20-50% throughput improvement
- Varies by GPU model
- Balance with latency requirements

## Configuration Profiles

### High Performance Profile

For systems with powerful hardware:

```yaml
# config_high_performance.yaml
video:
  target_resolution: [1280, 720]
  buffer_size_seconds: 2.0

detection:
  model_path: "yolov8m.pt"
  confidence_threshold_low: 0.70
  enable_multi_view_fusion: true

tracking:
  max_trajectory_length: 30
  use_multi_camera_triangulation: true
```

**Expected Performance**: 30+ FPS, <1s latency

### Balanced Profile

For mid-range hardware:

```yaml
# config_balanced.yaml
video:
  target_resolution: [960, 540]
  buffer_size_seconds: 1.5

detection:
  model_path: "yolov8s.pt"
  confidence_threshold_low: 0.75
  enable_multi_view_fusion: true

tracking:
  max_trajectory_length: 20
  use_multi_camera_triangulation: false
```

**Expected Performance**: 25-30 FPS, <1.5s latency

### Low Resource Profile

For resource-constrained systems:

```yaml
# config_low_resource.yaml
video:
  target_resolution: [640, 360]
  buffer_size_seconds: 1.0

detection:
  model_path: "yolov8n.pt"
  confidence_threshold_low: 0.80
  enable_multi_view_fusion: false

tracking:
  max_trajectory_length: 15
  use_multi_camera_triangulation: false
```

**Expected Performance**: 20-25 FPS, <2s latency

## Monitoring and Tuning

### Real-Time Performance Monitoring

```python
from umpirai.monitoring.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor()

# Update metrics each frame
monitor.update_metrics({
    'fps': current_fps,
    'latency_ms': latency,
    'cpu_percent': cpu_usage,
    'memory_mb': memory_usage
})

# Check for alerts
alerts = monitor.check_alerts()
if alerts:
    print(f"Performance alerts: {alerts}")
```

### Continuous Optimization

1. **Profile regularly** - Run profiler weekly to catch regressions
2. **Monitor in production** - Track metrics in live deployments
3. **A/B test optimizations** - Compare before/after performance
4. **Iterate** - Apply optimizations incrementally

## Troubleshooting Performance Issues

### Issue: Low FPS (<25)

**Diagnosis**:
```bash
python scripts/profile_performance.py --video test.mp4 --calibration cal.json --duration 60 --output profile.json
```

**Solutions**:
1. Check bottleneck component in profile
2. Apply relevant optimizations from sections above
3. Consider hardware upgrade if all optimizations exhausted

### Issue: High Latency (>2s)

**Diagnosis**:
- Check decision engine processing time
- Verify network latency for RTSP streams
- Profile individual detector performance

**Solutions**:
1. Enable parallel detector execution
2. Reduce detection frequency
3. Optimize slowest detector

### Issue: Memory Leaks

**Diagnosis**:
```python
import tracemalloc

tracemalloc.start()
# Run system
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

**Solutions**:
1. Clear old trajectories regularly
2. Limit frame buffer size
3. Fix circular references

### Issue: GPU Not Utilized

**Diagnosis**:
```bash
nvidia-smi
```

**Solutions**:
1. Verify CUDA installation
2. Check PyTorch CUDA availability
3. Ensure model is moved to GPU

## Best Practices

1. **Profile before optimizing** - Measure to identify real bottlenecks
2. **Optimize incrementally** - Apply one optimization at a time
3. **Measure impact** - Verify each optimization improves performance
4. **Balance accuracy vs speed** - Don't sacrifice accuracy for marginal gains
5. **Test thoroughly** - Ensure optimizations don't break functionality
6. **Document changes** - Track what optimizations were applied
7. **Monitor production** - Watch for performance regressions

## Hardware Recommendations

### Minimum Requirements
- CPU: 4-core Intel i5 or AMD Ryzen 5
- RAM: 8GB
- GPU: NVIDIA GTX 1050 Ti (optional)
- Storage: SSD recommended

### Recommended Configuration
- CPU: 8-core Intel i7 or AMD Ryzen 7
- RAM: 16GB
- GPU: NVIDIA RTX 3060 or better
- Storage: NVMe SSD

### High-Performance Configuration
- CPU: 12+ core Intel i9 or AMD Ryzen 9
- RAM: 32GB
- GPU: NVIDIA RTX 4070 or better
- Storage: NVMe SSD RAID

## Conclusion

Performance optimization is an iterative process. Start with profiling to identify bottlenecks, apply targeted optimizations, and measure the impact. The goal is to achieve 30+ FPS with <1 second latency while maintaining >95% accuracy.

For additional support, consult the troubleshooting guide or contact the development team.
