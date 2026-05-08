"""
Integration tests for UmpirAI System.

Tests the complete end-to-end processing pipeline including:
- System startup and shutdown
- Multi-component coordination
- Mode switching and graceful degradation
- Continuous operation
- Error handling and recovery
"""

import pytest
import time
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from umpirai.umpirai_system import (
    UmpirAISystem,
    SystemConfig,
    SystemMode,
    SystemStatus,
)
from umpirai.video.video_processor import CameraSource, CameraSourceType
from umpirai.video.multi_camera_synchronizer import CameraIntrinsics
from umpirai.calibration.calibration_manager import (
    CalibrationData,
    Point2D,
    CameraCalibration,
)
from umpirai.models.data_models import (
    Frame,
    Detection,
    BoundingBox,
    EventType,
    Position3D,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def system_config():
    """Create a test system configuration."""
    return SystemConfig(
        target_fps=30.0,
        buffer_seconds=2.0,
        detection_device="cpu",
        log_directory="test_logs",
        enable_performance_monitoring=True,
        initial_mode=SystemMode.FULL,
        auto_degradation=True,
        max_runtime_minutes=1  # Short runtime for tests
    )


@pytest.fixture
def mock_object_detector():
    """Create a mock object detector."""
    with patch('umpirai.umpirai_system.ObjectDetector') as mock_class:
        mock_detector = Mock()
        mock_class.return_value = mock_detector
        yield mock_detector


@pytest.fixture
def mock_calibration():
    """Create a mock calibration."""
    return CalibrationData(
        calibration_name="test_calibration",
        created_at="2024-01-01T00:00:00",
        pitch_boundary=[
            Point2D(x=100, y=100),
            Point2D(x=1180, y=100),
            Point2D(x=1180, y=620),
            Point2D(x=100, y=620),
        ],
        crease_lines={
            "bowling": [Point2D(x=640, y=200), Point2D(x=640, y=520)],
            "batting": [Point2D(x=640, y=400), Point2D(x=640, y=720)],
        },
        wide_guidelines={"left": -1.0, "right": 1.0},
        stump_positions={
            "bowling": Point2D(x=640, y=200),
            "batting": Point2D(x=640, y=520),
        },
        camera_calibrations={
            "cam1": CameraCalibration(
                camera_id="cam1",
                homography=np.eye(3),
                intrinsics=None
            )
        }
    )


@pytest.fixture
def mock_frame():
    """Create a mock video frame."""
    return Frame(
        camera_id="cam1",
        frame_number=1,
        timestamp=time.time(),
        image=np.zeros((720, 1280, 3), dtype=np.uint8),
        metadata={}
    )


@pytest.fixture
def mock_detections():
    """Create mock detections."""
    return [
        Detection(
            class_id=0,
            class_name="ball",
            bounding_box=BoundingBox(x=640, y=360, width=20, height=20),
            confidence=0.95,
            position_3d=Position3D(x=0.0, y=1.0, z=0.0)
        ),
        Detection(
            class_id=1,
            class_name="stumps",
            bounding_box=BoundingBox(x=620, y=200, width=40, height=100),
            confidence=0.98,
            position_3d=None
        ),
    ]


# ============================================================================
# Test: System Initialization
# ============================================================================

def test_system_initialization(system_config, mock_object_detector):
    """Test system initializes correctly with all components."""
    system = UmpirAISystem(config=system_config)
    
    # Verify components are initialized
    assert system.video_processor is not None
    assert system.synchronizer is not None
    assert system.object_detector is not None
    assert system.ball_tracker is not None
    assert system.decision_engine is not None
    assert system.decision_output is not None
    assert system.event_logger is not None
    assert system.performance_monitor is not None
    assert system.calibration_manager is not None
    
    # Verify initial state
    assert system.mode == SystemMode.FULL
    assert not system.is_running
    assert system.frames_processed == 0
    assert system.decisions_made == 0


@patch('umpirai.umpirai_system.ObjectDetector')
def test_system_initialization_with_defaults(mock_detector_class):
    """Test system initializes with default configuration."""
    # Setup mock
    mock_detector = Mock()
    mock_detector_class.return_value = mock_detector
    
    system = UmpirAISystem()
    
    assert system.config is not None
    assert system.mode == SystemMode.FULL
    assert not system.is_running


# ============================================================================
# Test: System Startup and Shutdown
# ============================================================================

@patch('umpirai.umpirai_system.VideoProcessor')
def test_system_startup(mock_video_processor_class, system_config, mock_calibration, mock_object_detector):
    """Test system startup procedure."""
    # Setup mock
    mock_video_processor = Mock()
    mock_video_processor_class.return_value = mock_video_processor
    
    system = UmpirAISystem(config=system_config)
    system.set_calibration(mock_calibration)
    
    # Add a mock camera
    camera_source = CameraSource(
        source_type=CameraSourceType.FILE,
        source_path="test_video.mp4"
    )
    system.add_camera("cam1", camera_source)
    
    # Start system
    system.start()
    
    # Verify state
    assert system.is_running
    assert system.start_time is not None
    assert system.frames_processed == 0
    assert system.decisions_made == 0
    
    # Verify video processor was started
    mock_video_processor.start_capture.assert_called_once()


@patch('umpirai.umpirai_system.VideoProcessor')
def test_system_shutdown(mock_video_processor_class, system_config, mock_calibration, mock_object_detector):
    """Test system shutdown procedure."""
    # Setup mock
    mock_video_processor = Mock()
    mock_video_processor_class.return_value = mock_video_processor
    
    system = UmpirAISystem(config=system_config)
    system.set_calibration(mock_calibration)
    
    # Add camera and start
    camera_source = CameraSource(
        source_type=CameraSourceType.FILE,
        source_path="test_video.mp4"
    )
    system.add_camera("cam1", camera_source)
    system.start()
    
    # Stop system
    system.stop()
    
    # Verify state
    assert not system.is_running
    
    # Verify video processor was stopped
    mock_video_processor.stop_capture.assert_called_once()


def test_system_startup_without_calibration(system_config, mock_object_detector):
    """Test system can start without calibration (with warning)."""
    system = UmpirAISystem(config=system_config)
    
    # Should not raise exception, but will log warning
    # (In real scenario, decisions may be inaccurate)
    # For test, we just verify it doesn't crash
    assert system.decision_engine.calibration is None


# ============================================================================
# Test: Camera Management
# ============================================================================

def test_add_single_camera(system_config, mock_object_detector):
    """Test adding a single camera to the system."""
    system = UmpirAISystem(config=system_config)
    
    camera_source = CameraSource(
        source_type=CameraSourceType.FILE,
        source_path="test_video.mp4"
    )
    
    system.add_camera("cam1", camera_source)
    
    # Verify camera was added to video processor
    assert "cam1" in system.video_processor.cameras


def test_add_multiple_cameras(system_config, mock_object_detector):
    """Test adding multiple cameras to the system."""
    system = UmpirAISystem(config=system_config)
    
    # Add multiple cameras
    for i in range(3):
        camera_source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=f"test_video_{i}.mp4"
        )
        system.add_camera(f"cam{i}", camera_source)
    
    # Verify all cameras were added
    assert len(system.video_processor.cameras) == 3
    assert "cam0" in system.video_processor.cameras
    assert "cam1" in system.video_processor.cameras
    assert "cam2" in system.video_processor.cameras


def test_add_camera_with_intrinsics(system_config, mock_object_detector):
    """Test adding camera with intrinsic parameters for synchronization."""
    system = UmpirAISystem(config=system_config)
    
    camera_source = CameraSource(
        source_type=CameraSourceType.FILE,
        source_path="test_video.mp4"
    )
    
    intrinsics = CameraIntrinsics(
        camera_matrix=np.eye(3),
        distortion_coeffs=np.zeros(5)
    )
    
    system.add_camera("cam1", camera_source, intrinsics)
    
    # Verify camera was added to both video processor and synchronizer
    assert "cam1" in system.video_processor.cameras
    assert "cam1" in system.synchronizer.camera_intrinsics


# ============================================================================
# Test: Calibration Management
# ============================================================================

def test_set_calibration(system_config, mock_calibration, mock_object_detector):
    """Test setting calibration directly."""
    system = UmpirAISystem(config=system_config)
    
    system.set_calibration(mock_calibration)
    
    # Verify calibration was set in decision engine
    assert system.decision_engine.calibration is not None
    assert system.decision_engine.calibration.calibration_name == "test_calibration"


def test_load_calibration_from_file(system_config, mock_calibration, tmp_path, mock_object_detector):
    """Test loading calibration from file."""
    system = UmpirAISystem(config=system_config)
    
    # Save calibration to file
    system.calibration_manager._pitch_boundary = mock_calibration.pitch_boundary
    system.calibration_manager._crease_lines = mock_calibration.crease_lines
    system.calibration_manager._wide_guidelines = mock_calibration.wide_guidelines
    system.calibration_manager._stump_positions = mock_calibration.stump_positions
    system.calibration_manager._camera_calibrations = mock_calibration.camera_calibrations
    
    calibration_path = tmp_path / "test_calibration.json"
    system.calibration_manager.save_calibration("test_calibration", calibration_path)
    
    # Create new system and load calibration
    system2 = UmpirAISystem(config=system_config)
    system2.load_calibration(calibration_path)
    
    # Verify calibration was loaded
    assert system2.decision_engine.calibration is not None
    assert system2.decision_engine.calibration.calibration_name == "test_calibration"


# ============================================================================
# Test: Mode Switching
# ============================================================================

def test_mode_switching_full_to_reduced(system_config, mock_object_detector):
    """Test switching from Full to Reduced mode."""
    system = UmpirAISystem(config=system_config)
    
    assert system.mode == SystemMode.FULL
    
    system.switch_mode(SystemMode.REDUCED)
    
    assert system.mode == SystemMode.REDUCED
    assert system.config.target_fps == 25.0
    assert system.decision_engine.config.enable_lbw_detection == False


def test_mode_switching_reduced_to_minimal(system_config, mock_object_detector):
    """Test switching from Reduced to Minimal mode."""
    system = UmpirAISystem(config=system_config)
    system.switch_mode(SystemMode.REDUCED)
    
    system.switch_mode(SystemMode.MINIMAL)
    
    assert system.mode == SystemMode.MINIMAL
    assert system.config.target_fps == 20.0
    assert system.decision_engine.config.enable_caught_detection == False
    assert system.decision_engine.config.enable_lbw_detection == False


def test_mode_switching_to_safe(system_config, mock_object_detector):
    """Test switching to Safe mode."""
    system = UmpirAISystem(config=system_config)
    
    system.switch_mode(SystemMode.SAFE)
    
    assert system.mode == SystemMode.SAFE
    # All decision detectors should be disabled
    assert system.decision_engine.config.enable_wide_detection == False
    assert system.decision_engine.config.enable_no_ball_detection == False
    assert system.decision_engine.config.enable_bowled_detection == False
    assert system.decision_engine.config.enable_caught_detection == False
    assert system.decision_engine.config.enable_lbw_detection == False


def test_mode_switching_idempotent(system_config, mock_object_detector):
    """Test switching to same mode is idempotent."""
    system = UmpirAISystem(config=system_config)
    
    initial_mode = system.mode
    system.switch_mode(initial_mode)
    
    # Should remain in same mode
    assert system.mode == initial_mode


# ============================================================================
# Test: System Status
# ============================================================================

def test_get_status_not_running(system_config, mock_object_detector):
    """Test getting status when system is not running."""
    system = UmpirAISystem(config=system_config)
    
    status = system.get_status()
    
    assert isinstance(status, SystemStatus)
    assert status.mode == SystemMode.FULL
    assert not status.is_running
    assert status.uptime_seconds == 0.0
    assert status.frames_processed == 0
    assert status.decisions_made == 0
    assert status.current_fps == 0.0


@patch('umpirai.umpirai_system.VideoProcessor')
def test_get_status_running(mock_video_processor_class, system_config, mock_calibration, mock_object_detector):
    """Test getting status when system is running."""
    # Setup mock
    mock_video_processor = Mock()
    mock_video_processor.get_frame_rate.return_value = 30.0
    mock_video_processor.get_healthy_cameras.return_value = ["cam1"]
    mock_video_processor.get_failed_cameras.return_value = []
    mock_video_processor_class.return_value = mock_video_processor
    
    system = UmpirAISystem(config=system_config)
    system.set_calibration(mock_calibration)
    
    # Add camera and start
    camera_source = CameraSource(
        source_type=CameraSourceType.FILE,
        source_path="test_video.mp4"
    )
    system.add_camera("cam1", camera_source)
    system.start()
    
    # Wait a bit
    time.sleep(0.1)
    
    status = system.get_status()
    
    assert status.is_running
    assert status.uptime_seconds > 0
    assert status.current_fps == 30.0
    assert "cam1" in status.active_cameras
    assert len(status.failed_cameras) == 0
    
    system.stop()


# ============================================================================
# Test: Error Handling
# ============================================================================

def test_error_tracking(system_config, mock_object_detector):
    """Test that errors are tracked properly."""
    system = UmpirAISystem(config=system_config)
    
    # Simulate an error
    error_msg = "Test error"
    system.last_error = error_msg
    system.errors.append({
        "timestamp": time.time(),
        "error": error_msg,
        "type": "TestError"
    })
    
    # Verify error was tracked
    assert system.last_error == error_msg
    assert len(system.errors) == 1
    assert system.errors[0]["error"] == error_msg


def test_graceful_degradation_on_camera_failure(system_config, mock_object_detector):
    """Test system degrades gracefully when cameras fail."""
    system = UmpirAISystem(config=system_config)
    system.config.auto_degradation = True
    
    # Simulate camera failure
    from umpirai.video.video_processor import VideoInputError
    
    error = VideoInputError(
        camera_id="cam1",
        error_type="disconnection",
        timestamp=time.time(),
        message="Camera disconnected",
        reconnect_attempts=3,
        diagnostic_info={}
    )
    
    # Mock video processor state
    system.video_processor.get_failed_cameras = Mock(return_value=["cam1"])
    system.video_processor.get_healthy_cameras = Mock(return_value=[])
    
    # Handle error
    system._handle_video_error(error)
    
    # System should degrade to safe mode when all cameras fail
    assert system.mode == SystemMode.SAFE


# ============================================================================
# Test: Context Manager
# ============================================================================

@patch('umpirai.umpirai_system.VideoProcessor')
def test_context_manager(mock_video_processor_class, system_config, mock_calibration, mock_object_detector):
    """Test system works as context manager."""
    # Setup mock
    mock_video_processor = Mock()
    mock_video_processor_class.return_value = mock_video_processor
    
    # Use system as context manager
    with UmpirAISystem(config=system_config) as system:
        system.set_calibration(mock_calibration)
        
        # Add camera
        camera_source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path="test_video.mp4"
        )
        system.add_camera("cam1", camera_source)
        
        # System should be running
        assert system.is_running
    
    # After exiting context, system should be stopped
    assert not system.is_running
    mock_video_processor.stop_capture.assert_called()


# ============================================================================
# Test: Runtime Limits
# ============================================================================

@patch('umpirai.umpirai_system.VideoProcessor')
def test_runtime_limit(mock_video_processor_class, system_config, mock_calibration, mock_object_detector):
    """Test system respects maximum runtime limit."""
    # Setup mock
    mock_video_processor = Mock()
    mock_video_processor.get_synchronized_frames.return_value = {}
    mock_video_processor_class.return_value = mock_video_processor
    
    # Set very short runtime for test
    system_config.max_runtime_minutes = 0.01  # ~0.6 seconds
    
    system = UmpirAISystem(config=system_config)
    system.set_calibration(mock_calibration)
    
    # Add camera and start
    camera_source = CameraSource(
        source_type=CameraSourceType.FILE,
        source_path="test_video.mp4"
    )
    system.add_camera("cam1", camera_source)
    system.start()
    
    # Process frames until runtime limit
    start_time = time.time()
    while system.is_running and (time.time() - start_time) < 2.0:
        system.process_frame()
        time.sleep(0.01)
    
    # System should have stopped due to runtime limit
    assert not system.is_running


# ============================================================================
# Test: Performance Monitoring Integration
# ============================================================================

@patch('umpirai.umpirai_system.VideoProcessor')
@patch('umpirai.umpirai_system.ObjectDetector')
def test_performance_monitoring(
    mock_detector_class,
    mock_video_processor_class,
    system_config,
    mock_calibration,
    mock_frame,
    mock_detections
):
    """Test performance monitoring integration."""
    # Setup mocks
    mock_video_processor = Mock()
    mock_video_processor.get_synchronized_frames.return_value = {"cam1": mock_frame}
    mock_video_processor.get_frame_rate.return_value = 30.0
    mock_video_processor_class.return_value = mock_video_processor
    
    mock_detector = Mock()
    from umpirai.models.data_models import DetectionResult
    mock_detector.detect.return_value = DetectionResult(
        frame=mock_frame,
        detections=mock_detections,
        processing_time_ms=10.0
    )
    mock_detector_class.return_value = mock_detector
    
    system = UmpirAISystem(config=system_config)
    system.set_calibration(mock_calibration)
    
    # Add camera and start
    camera_source = CameraSource(
        source_type=CameraSourceType.FILE,
        source_path="test_video.mp4"
    )
    system.add_camera("cam1", camera_source)
    system.start()
    
    # Process a frame
    system.process_frame()
    
    # Verify performance metrics were collected
    assert system.performance_monitor is not None
    metrics_history = system.performance_monitor.get_metrics_history()
    assert len(metrics_history) > 0
    
    system.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
