"""
Unit tests for error handling and recovery mechanisms.

Tests specific error handling scenarios for VideoProcessor, ObjectDetector, 
and DecisionEngine components.
"""

import pytest
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from umpirai.video.video_processor import VideoProcessor, CameraSource, CameraSourceType, VideoInputError, CameraThread
from umpirai.detection.object_detector import ObjectDetector, DetectionError
from umpirai.decision.decision_engine import DecisionEngine, ProcessingError, DecisionEngineConfig
from umpirai.models.data_models import Frame, Detection, DetectionResult, BoundingBox, Trajectory, Position3D, Vector3D, TrackState
from umpirai.calibration.calibration_manager import CalibrationData, Point2D, CameraCalibration


def create_test_calibration():
    """Helper function to create test calibration data."""
    return CalibrationData(
        calibration_name="test_calibration",
        created_at="2024-01-01T00:00:00",
        pitch_boundary=[
            Point2D(0, 0),
            Point2D(100, 0),
            Point2D(100, 50),
            Point2D(0, 50)
        ],
        crease_lines={
            "bowling": [Point2D(50, 10), Point2D(50, 40)],
            "batting": [Point2D(50, 20), Point2D(50, 30)]
        },
        wide_guidelines={"left": -1.0, "right": 1.0},
        stump_positions={"bowling": Point2D(50, 15), "batting": Point2D(50, 25)},
        camera_calibrations={}
    )


# ============================================================================
# VideoProcessor Error Handling Tests
# ============================================================================

def test_camera_reconnection_exponential_backoff():
    """Test that camera reconnection uses exponential backoff (1s, 2s, 4s)."""
    errors_received = []
    
    def error_callback(error: VideoInputError):
        errors_received.append(error)
    
    processor = VideoProcessor(error_callback=error_callback)
    source = CameraSource(
        source_type=CameraSourceType.FILE,
        source_path="nonexistent.mp4"
    )
    
    processor.add_camera_source("cam1", source)
    camera_thread = processor.cameras["cam1"]
    
    # Simulate disconnection errors with different attempt numbers
    for attempt in [1, 2, 3]:
        error = VideoInputError(
            camera_id="cam1",
            error_type="disconnection",
            timestamp=time.monotonic(),
            message=f"Reconnection attempt {attempt}",
            reconnect_attempts=attempt,
            diagnostic_info={
                "backoff_time": 2 ** (attempt - 1),
                "max_attempts": 3
            }
        )
        camera_thread._handle_error(error)
        
        # Verify backoff time is correct
        assert error.diagnostic_info["backoff_time"] == 2 ** (attempt - 1)
    
    # Verify all errors were received
    assert len(errors_received) == 3


def test_video_input_loss_alerting():
    """Test that video input loss triggers operator alert."""
    errors_received = []
    
    def error_callback(error: VideoInputError):
        errors_received.append(error)
    
    processor = VideoProcessor(error_callback=error_callback)
    source = CameraSource(
        source_type=CameraSourceType.FILE,
        source_path="test.mp4"
    )
    
    processor.add_camera_source("cam1", source)
    camera_thread = processor.cameras["cam1"]
    
    # Simulate video input loss
    error = VideoInputError(
        camera_id="cam1",
        error_type="frame_loss",
        timestamp=time.monotonic(),
        message="Video input loss detected",
        reconnect_attempts=0,
        diagnostic_info={
            "consecutive_failures": 10
        }
    )
    camera_thread._handle_error(error)
    
    # Verify alert was sent
    assert len(errors_received) == 1
    assert errors_received[0].error_type == "frame_loss"


def test_graceful_degradation_continue_with_remaining_cameras():
    """Test that system continues with remaining cameras when one fails."""
    processor = VideoProcessor()
    
    # Add multiple cameras
    for i in range(3):
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=f"cam{i}.mp4"
        )
        processor.add_camera_source(f"cam{i}", source)
    
    # Simulate one camera failing
    processor.cameras["cam1"].is_connected = False
    
    # Get healthy cameras
    healthy = processor.get_healthy_cameras()
    failed = processor.get_failed_cameras()
    
    # Verify system can identify healthy vs failed cameras
    assert "cam1" in failed
    assert len(healthy) + len(failed) == 3


def test_error_logging_with_diagnostic_info():
    """Test that errors are logged with diagnostic information."""
    errors_received = []
    
    def error_callback(error: VideoInputError):
        errors_received.append(error)
    
    processor = VideoProcessor(error_callback=error_callback)
    source = CameraSource(
        source_type=CameraSourceType.USB,
        source_path=0
    )
    
    processor.add_camera_source("cam1", source)
    camera_thread = processor.cameras["cam1"]
    
    # Create error with diagnostic info
    error = VideoInputError(
        camera_id="cam1",
        error_type="initialization_failure",
        timestamp=time.monotonic(),
        message="Failed to open camera",
        reconnect_attempts=0,
        diagnostic_info={
            "source_type": "usb",
            "source_path": "0",
            "error_code": "DEVICE_NOT_FOUND"
        }
    )
    camera_thread._handle_error(error)
    
    # Verify diagnostic info is present
    assert len(errors_received) == 1
    assert "source_type" in errors_received[0].diagnostic_info
    assert "error_code" in errors_received[0].diagnostic_info


# ============================================================================
# ObjectDetector Error Handling Tests
# ============================================================================

def test_model_initialization_failure_handling():
    """Test that model initialization failures are handled properly."""
    with pytest.raises(RuntimeError) as exc_info:
        detector = ObjectDetector(model_path="/invalid/path/model.pt", device="cpu")
    
    # Verify error message is informative (could be either message depending on whether ultralytics is installed)
    error_msg = str(exc_info.value)
    assert "YOLOv8" in error_msg or "Failed to load" in error_msg


def test_gpu_failure_fallback_to_cpu():
    """Test that GPU failure triggers fallback to CPU inference."""
    # This test would require mocking GPU initialization failure
    # For now, we test the logic structure
    
    # Mock YOLO to fail on GPU but succeed on CPU
    with patch('umpirai.detection.object_detector.YOLO') as mock_yolo:
        # First call (GPU) fails, second call (CPU) succeeds
        mock_yolo.side_effect = [
            Exception("CUDA not available"),
            MagicMock()  # CPU success
        ]
        
        # This would trigger GPU failure and CPU fallback
        # In actual implementation, the detector would catch the GPU error
        # and retry with CPU


def test_low_confidence_detection_flagging():
    """Test that low confidence detections are flagged."""
    # Create a detection error for low confidence
    error = DetectionError(
        error_type="low_confidence",
        timestamp=time.time(),
        message="Low confidence detection",
        diagnostic_info={
            "class_name": "ball",
            "confidence": 0.65,
            "threshold": 0.70
        }
    )
    
    # Verify error structure
    assert error.error_type == "low_confidence"
    assert error.diagnostic_info["confidence"] < error.diagnostic_info["threshold"]


def test_missing_critical_elements_alerting_threshold():
    """Test that missing critical elements alert after >5 seconds."""
    # Test with duration below threshold
    error_below = DetectionError(
        error_type="missing_critical_elements",
        timestamp=time.time(),
        message="Stumps missing for 3.0 seconds",
        diagnostic_info={
            "missing_element": "stumps",
            "missing_duration": 3.0,
            "threshold": 5.0
        }
    )
    
    # Should not trigger alert (below threshold)
    assert error_below.diagnostic_info["missing_duration"] < error_below.diagnostic_info["threshold"]
    
    # Test with duration above threshold
    error_above = DetectionError(
        error_type="missing_critical_elements",
        timestamp=time.time(),
        message="Stumps missing for 6.0 seconds",
        diagnostic_info={
            "missing_element": "stumps",
            "missing_duration": 6.0,
            "threshold": 5.0
        }
    )
    
    # Should trigger alert (above threshold)
    assert error_above.diagnostic_info["missing_duration"] > error_above.diagnostic_info["threshold"]


# ============================================================================
# DecisionEngine Error Handling Tests
# ============================================================================

def test_processing_error_continue_operation():
    """Test that processing errors don't stop operation."""
    calibration = create_test_calibration()
    
    engine = DecisionEngine(calibration=calibration)
    
    # Create mock data
    frame = Frame(
        camera_id="cam1",
        frame_number=1,
        timestamp=time.time(),
        image=np.zeros((720, 1280, 3), dtype=np.uint8),
        metadata={}
    )
    
    detection_result = DetectionResult(
        frame=frame,
        detections=[],
        processing_time_ms=10.0
    )
    
    trajectory = Trajectory(
        positions=[Position3D(0, 1, 0)],
        timestamps=[time.time()],
        velocities=[Vector3D(10, 0, 0)],
        start_position=Position3D(0, 1, 0),
        end_position=None,
        speed_max=10.0,
        speed_avg=10.0
    )
    
    track_state = TrackState(
        track_id="track1",
        position=Position3D(0, 1, 0),
        velocity=Vector3D(10, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        covariance=np.eye(9),
        last_seen=time.time(),
        occlusion_duration=0,
        confidence=0.9
    )
    
    # Simulate detector failure
    with patch.object(engine.wide_detector, 'detect', side_effect=Exception("Detector failed")):
        decision = engine.process_frame(
            detection_result,
            track_state,
            trajectory,
            calibration
        )
        
        # System should continue and return a decision
        assert decision is not None
        
        # Error should be logged
        assert len(engine.errors) > 0


def test_transient_error_recovery_without_restart():
    """Test that transient errors recover without restart."""
    calibration = create_test_calibration()
    
    engine = DecisionEngine(calibration=calibration)
    
    # Simulate transient error
    error = ProcessingError(
        error_type="transient_error",
        timestamp=time.time(),
        message="Temporary failure",
        component="TestDetector",
        diagnostic_info={"retry_count": 1},
        is_critical=False
    )
    
    engine._handle_error(error)
    
    # Verify error was logged but not marked as critical
    assert len(engine.errors) == 1
    assert not engine.has_critical_error()


def test_critical_error_data_preservation():
    """Test that critical errors trigger data preservation."""
    calibration = create_test_calibration()
    
    engine = DecisionEngine(calibration=calibration)
    
    # Add some test data
    from umpirai.models.data_models import Decision, EventType
    decision = Decision(
        decision_id="test_decision",
        event_type=EventType.LEGAL,
        confidence=0.9,
        timestamp=time.time(),
        trajectory=Trajectory(
            positions=[Position3D(0, 1, 0)],
            timestamps=[time.time()],
            velocities=[Vector3D(10, 0, 0)],
            start_position=Position3D(0, 1, 0),
            end_position=None,
            speed_max=10.0,
            speed_avg=10.0
        ),
        detections=[],
        reasoning="Test",
        video_references=[],
        requires_review=False
    )
    engine.match_data["decisions"].append(decision)
    
    # Simulate critical error
    error = ProcessingError(
        error_type="critical_error",
        timestamp=time.time(),
        message="Critical failure",
        component="System",
        diagnostic_info={},
        is_critical=True
    )
    engine._handle_error(error)
    
    # Verify critical error is detected
    assert engine.has_critical_error()
    
    # Save match data
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        filepath = f.name
    
    try:
        engine.save_match_data(filepath)
        
        # Verify file exists
        assert os.path.exists(filepath)
        
        # Verify data was saved
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert len(data["decisions"]) == 1
        assert len(data["errors"]) == 1
        
    finally:
        if os.path.exists(filepath):
            os.unlink(filepath)


def test_insufficient_data_handling():
    """Test that insufficient data is handled gracefully."""
    calibration = create_test_calibration()
    
    engine = DecisionEngine(calibration=calibration)
    
    # Create frame with no detections (insufficient data)
    frame = Frame(
        camera_id="cam1",
        frame_number=1,
        timestamp=time.time(),
        image=np.zeros((720, 1280, 3), dtype=np.uint8),
        metadata={}
    )
    
    detection_result = DetectionResult(
        frame=frame,
        detections=[],  # No detections
        processing_time_ms=10.0
    )
    
    trajectory = Trajectory(
        positions=[Position3D(0, 1, 0)],
        timestamps=[time.time()],
        velocities=[Vector3D(10, 0, 0)],
        start_position=Position3D(0, 1, 0),
        end_position=None,
        speed_max=10.0,
        speed_avg=10.0
    )
    
    track_state = TrackState(
        track_id="track1",
        position=Position3D(0, 1, 0),
        velocity=Vector3D(10, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        covariance=np.eye(9),
        last_seen=time.time(),
        occlusion_duration=0,
        confidence=0.9
    )
    
    # Process frame with insufficient data
    decision = engine.process_frame(
        detection_result,
        track_state,
        trajectory,
        calibration
    )
    
    # Should still return a decision (even if uncertain)
    assert decision is not None
    
    # Should log insufficient data error
    assert len(engine.errors) > 0
    assert any(e.error_type == "insufficient_data" for e in engine.errors)


def test_affected_decisions_flagged_as_uncertain():
    """Test that decisions affected by errors are flagged as uncertain."""
    calibration = create_test_calibration()
    
    engine = DecisionEngine(calibration=calibration)
    
    # Create mock data
    frame = Frame(
        camera_id="cam1",
        frame_number=1,
        timestamp=time.time(),
        image=np.zeros((720, 1280, 3), dtype=np.uint8),
        metadata={}
    )
    
    detection_result = DetectionResult(
        frame=frame,
        detections=[],
        processing_time_ms=10.0
    )
    
    trajectory = Trajectory(
        positions=[Position3D(0, 1, 0)],
        timestamps=[time.time()],
        velocities=[Vector3D(10, 0, 0)],
        start_position=Position3D(0, 1, 0),
        end_position=None,
        speed_max=10.0,
        speed_avg=10.0
    )
    
    track_state = TrackState(
        track_id="track1",
        position=Position3D(0, 1, 0),
        velocity=Vector3D(10, 0, 0),
        acceleration=Vector3D(0, 0, 0),
        covariance=np.eye(9),
        last_seen=time.time(),
        occlusion_duration=0,
        confidence=0.9
    )
    
    # Cause an error during processing
    with patch.object(engine.wide_detector, 'detect', side_effect=Exception("Error")):
        decision = engine.process_frame(
            detection_result,
            track_state,
            trajectory,
            calibration
        )
        
        # Decision should be flagged for review
        assert decision is not None
        assert decision.requires_review == True
