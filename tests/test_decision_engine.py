"""
Unit tests for DecisionEngine.

These tests validate specific examples and edge cases for decision priority logic,
conflicting rule scenarios, and confidence aggregation.
"""

import pytest
import numpy as np

from umpirai.decision.decision_engine import DecisionEngine, DecisionEngineConfig
from umpirai.models.data_models import (
    Detection,
    DetectionResult,
    Frame,
    TrackState,
    Trajectory,
    Position3D,
    Vector3D,
    BoundingBox,
    EventType,
    DetectionClass,
)
from umpirai.calibration.calibration_manager import CalibrationData, Point2D


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_calibration() -> CalibrationData:
    """Create a test calibration."""
    return CalibrationData(
        calibration_name="test_calibration",
        created_at="2024-01-01T00:00:00Z",
        pitch_boundary=[
            Point2D(x=100.0, y=100.0),
            Point2D(x=1180.0, y=100.0),
            Point2D(x=1180.0, y=620.0),
            Point2D(x=100.0, y=620.0)
        ],
        crease_lines={
            "bowling": [Point2D(x=640.0, y=-10.0), Point2D(x=640.0, y=-10.0)],
            "batting": [Point2D(x=640.0, y=0.0), Point2D(x=640.0, y=0.0)]
        },
        wide_guidelines={"left": -1.0, "right": 1.0},
        stump_positions={
            "bowling": Point2D(x=640.0, y=-10.0),
            "batting": Point2D(x=640.0, y=0.0)
        },
        camera_calibrations={}
    )


def create_test_trajectory(timestamp: float = 1.0) -> Trajectory:
    """Create a test trajectory."""
    return Trajectory(
        positions=[
            Position3D(x=0.0, y=1.0, z=-10.0),
            Position3D(x=0.0, y=1.0, z=-5.0),
            Position3D(x=0.0, y=1.0, z=0.0)
        ],
        timestamps=[timestamp, timestamp + 0.1, timestamp + 0.2],
        velocities=[
            Vector3D(vx=0.0, vy=0.0, vz=20.0),
            Vector3D(vx=0.0, vy=0.0, vz=20.0),
            Vector3D(vx=0.0, vy=0.0, vz=20.0)
        ],
        start_position=Position3D(x=0.0, y=1.0, z=-10.0),
        end_position=Position3D(x=0.0, y=1.0, z=0.0),
        speed_max=20.0,
        speed_avg=20.0
    )


def create_test_detections(confidence: float = 0.95) -> list[Detection]:
    """Create test detections."""
    return [
        Detection(
            class_id=DetectionClass.BALL.value,
            class_name="ball",
            bounding_box=BoundingBox(x=640.0, y=360.0, width=20.0, height=20.0),
            confidence=confidence,
            position_3d=Position3D(x=0.0, y=1.0, z=0.0)
        ),
        Detection(
            class_id=DetectionClass.STUMPS.value,
            class_name="stumps",
            bounding_box=BoundingBox(x=620.0, y=400.0, width=40.0, height=60.0),
            confidence=confidence
        ),
        Detection(
            class_id=DetectionClass.BATSMAN.value,
            class_name="batsman",
            bounding_box=BoundingBox(x=600.0, y=300.0, width=80.0, height=150.0),
            confidence=confidence
        )
    ]


# ============================================================================
# Initialization Tests
# ============================================================================

def test_initialization_default():
    """Test default initialization."""
    engine = DecisionEngine()
    
    assert engine.wide_detector is not None
    assert engine.no_ball_detector is not None
    assert engine.bowled_detector is not None
    assert engine.caught_detector is not None
    assert engine.lbw_detector is not None
    assert engine.legal_delivery_counter is not None
    assert engine.config is not None


def test_initialization_with_calibration():
    """Test initialization with calibration."""
    calibration = create_test_calibration()
    engine = DecisionEngine(calibration=calibration)
    
    assert engine.calibration == calibration


def test_initialization_with_config():
    """Test initialization with custom config."""
    config = DecisionEngineConfig(
        enable_wide_detection=False,
        enable_lbw_detection=False,
        review_threshold=0.85
    )
    engine = DecisionEngine(config=config)
    
    assert engine.config.enable_wide_detection is False
    assert engine.config.enable_lbw_detection is False
    assert engine.config.review_threshold == 0.85


# ============================================================================
# Decision Priority Logic Tests
# ============================================================================

def test_priority_legal_delivery():
    """Test legal delivery classification when no events detected."""
    engine = DecisionEngine()
    calibration = create_test_calibration()
    trajectory = create_test_trajectory()
    detections = create_test_detections()
    
    decision = engine.classify_delivery(trajectory, detections, calibration)
    
    assert decision.event_type == EventType.LEGAL
    assert decision.confidence > 0.0


def test_priority_dismissal_over_legal():
    """Test that dismissals take priority over legal delivery."""
    engine = DecisionEngine()
    calibration = create_test_calibration()
    
    # Create trajectory that hits stumps
    trajectory = Trajectory(
        positions=[
            Position3D(x=0.0, y=0.5, z=-10.0),
            Position3D(x=0.0, y=0.3, z=-5.0),
            Position3D(x=0.0, y=0.2, z=0.0)
        ],
        timestamps=[1.0, 1.1, 1.2],
        velocities=[
            Vector3D(vx=0.0, vy=-2.0, vz=20.0),
            Vector3D(vx=0.0, vy=-2.0, vz=20.0),
            Vector3D(vx=0.0, vy=-2.0, vz=20.0)
        ],
        start_position=Position3D(x=0.0, y=0.5, z=-10.0),
        end_position=Position3D(x=0.0, y=0.2, z=0.0)
    )
    
    # Create detections with ball-stump contact
    detections = [
        Detection(
            class_id=DetectionClass.BALL.value,
            class_name="ball",
            bounding_box=BoundingBox(x=640.0, y=400.0, width=20.0, height=20.0),
            confidence=0.95,
            position_3d=Position3D(x=0.0, y=0.2, z=0.0)
        ),
        Detection(
            class_id=DetectionClass.STUMPS.value,
            class_name="stumps",
            bounding_box=BoundingBox(x=635.0, y=395.0, width=40.0, height=60.0),
            confidence=0.95
        )
    ]
    
    decision = engine.classify_delivery(trajectory, detections, calibration)
    
    # Should detect bowled dismissal
    assert decision.event_type == EventType.BOWLED


def test_priority_no_ball_over_wide():
    """Test that no ball takes priority over wide."""
    engine = DecisionEngine()
    calibration = create_test_calibration()
    
    # Create trajectory for wide ball with bowler overstepping
    trajectory = Trajectory(
        positions=[
            Position3D(x=2.0, y=1.0, z=-10.0),  # Wide position
            Position3D(x=2.0, y=1.0, z=-5.0),
            Position3D(x=2.0, y=1.0, z=0.0)
        ],
        timestamps=[1.0, 1.1, 1.2],
        velocities=[
            Vector3D(vx=0.0, vy=0.0, vz=5.0),  # Slow velocity change for release
            Vector3D(vx=0.0, vy=0.0, vz=20.0),  # Fast after release
            Vector3D(vx=0.0, vy=0.0, vz=20.0)
        ],
        start_position=Position3D(x=2.0, y=1.0, z=-10.0)
    )
    
    # Create detections with bowler foot over crease
    detections = [
        Detection(
            class_id=DetectionClass.BALL.value,
            class_name="ball",
            bounding_box=BoundingBox(x=800.0, y=360.0, width=20.0, height=20.0),
            confidence=0.95,
            position_3d=Position3D(x=2.0, y=1.0, z=0.0)
        ),
        Detection(
            class_id=DetectionClass.BOWLER.value,
            class_name="bowler",
            bounding_box=BoundingBox(x=600.0, y=200.0, width=80.0, height=150.0),
            confidence=0.95,
            position_3d=Position3D(x=0.0, y=0.1, z=-9.0)  # Over crease at z=-10
        ),
        Detection(
            class_id=DetectionClass.BATSMAN.value,
            class_name="batsman",
            bounding_box=BoundingBox(x=600.0, y=400.0, width=80.0, height=150.0),
            confidence=0.95,
            position_3d=Position3D(x=0.0, y=1.0, z=0.0)
        )
    ]
    
    decision = engine.classify_delivery(trajectory, detections, calibration)
    
    # Should detect no ball (priority over wide)
    assert decision.event_type == EventType.NO_BALL


# ============================================================================
# Conflicting Rule Resolution Tests
# ============================================================================

def test_conflicting_dismissal_and_no_ball():
    """Test resolution when both dismissal and no ball detected."""
    engine = DecisionEngine()
    calibration = create_test_calibration()
    
    # Create trajectory that hits stumps with bowler overstepping
    trajectory = Trajectory(
        positions=[
            Position3D(x=0.0, y=0.5, z=-10.0),
            Position3D(x=0.0, y=0.3, z=-5.0),
            Position3D(x=0.0, y=0.2, z=0.0)
        ],
        timestamps=[1.0, 1.1, 1.2],
        velocities=[
            Vector3D(vx=0.0, vy=-2.0, vz=5.0),  # Slow for release
            Vector3D(vx=0.0, vy=-2.0, vz=20.0),  # Fast after release
            Vector3D(vx=0.0, vy=-2.0, vz=20.0)
        ],
        start_position=Position3D(x=0.0, y=0.5, z=-10.0)
    )
    
    # Create detections with ball-stump contact AND bowler foot over crease
    detections = [
        Detection(
            class_id=DetectionClass.BALL.value,
            class_name="ball",
            bounding_box=BoundingBox(x=640.0, y=400.0, width=20.0, height=20.0),
            confidence=0.95,
            position_3d=Position3D(x=0.0, y=0.2, z=0.0)
        ),
        Detection(
            class_id=DetectionClass.STUMPS.value,
            class_name="stumps",
            bounding_box=BoundingBox(x=635.0, y=395.0, width=40.0, height=60.0),
            confidence=0.95
        ),
        Detection(
            class_id=DetectionClass.BOWLER.value,
            class_name="bowler",
            bounding_box=BoundingBox(x=600.0, y=200.0, width=80.0, height=150.0),
            confidence=0.95,
            position_3d=Position3D(x=0.0, y=0.1, z=-9.0)  # Over crease
        )
    ]
    
    decision = engine.classify_delivery(trajectory, detections, calibration)
    
    # Should detect dismissal but note the no ball conflict
    assert decision.event_type == EventType.BOWLED
    assert "no ball" in decision.reasoning.lower() or decision.requires_review


# ============================================================================
# Confidence Aggregation Tests
# ============================================================================

def test_confidence_aggregation_high():
    """Test confidence aggregation with high confidence detections."""
    engine = DecisionEngine()
    calibration = create_test_calibration()
    trajectory = create_test_trajectory()
    detections = create_test_detections(confidence=0.95)
    
    decision = engine.classify_delivery(trajectory, detections, calibration)
    
    # High confidence detections should result in high confidence decision
    assert decision.confidence >= 0.80


def test_confidence_aggregation_low():
    """Test confidence aggregation with low confidence detections."""
    engine = DecisionEngine()
    calibration = create_test_calibration()
    trajectory = create_test_trajectory()
    detections = create_test_detections(confidence=0.60)
    
    decision = engine.classify_delivery(trajectory, detections, calibration)
    
    # Low confidence detections should result in low confidence decision
    assert decision.confidence < 0.80
    assert decision.requires_review is True


def test_confidence_below_threshold_flags_review():
    """Test that low confidence flags decision for review."""
    engine = DecisionEngine()
    calibration = create_test_calibration()
    trajectory = create_test_trajectory()
    detections = create_test_detections(confidence=0.70)
    
    decision = engine.classify_delivery(trajectory, detections, calibration)
    
    if decision.confidence < 0.80:
        assert decision.requires_review is True


# ============================================================================
# Match State Tests
# ============================================================================

def test_get_match_state():
    """Test get_match_state method."""
    engine = DecisionEngine()
    match_state = engine.get_match_state()
    
    assert match_state.over_number == 0
    assert match_state.ball_number == 0
    assert match_state.legal_deliveries == 0
    assert match_state.total_deliveries == 0


def test_match_state_updates_with_deliveries():
    """Test that match state updates as deliveries are processed."""
    engine = DecisionEngine()
    calibration = create_test_calibration()
    
    # Process 3 legal deliveries using process_frame
    for i in range(3):
        trajectory = create_test_trajectory(timestamp=float(i))
        detections = create_test_detections()
        
        # Create frame and detection result
        frame = Frame(
            camera_id="cam1",
            frame_number=i,
            timestamp=float(i),
            image=np.zeros((720, 1280, 3), dtype=np.uint8)
        )
        
        detection_result = DetectionResult(
            frame=frame,
            detections=detections,
            processing_time_ms=10.0
        )
        
        track_state = TrackState(
            track_id="track_1",
            position=Position3D(x=0.0, y=1.0, z=0.0),
            velocity=Vector3D(vx=0.0, vy=0.0, vz=20.0),
            acceleration=Vector3D(vx=0.0, vy=0.0, vz=0.0),
            covariance=np.eye(9),
            last_seen=float(i),
            occlusion_duration=0,
            confidence=0.95
        )
        
        engine.process_frame(detection_result, track_state, trajectory, calibration)
    
    match_state = engine.get_match_state()
    assert match_state.legal_deliveries == 3
    assert match_state.ball_number == 3


def test_reset_match_state():
    """Test reset_match_state method."""
    engine = DecisionEngine()
    calibration = create_test_calibration()
    
    # Process some deliveries
    for i in range(3):
        trajectory = create_test_trajectory(timestamp=float(i))
        detections = create_test_detections()
        engine.classify_delivery(trajectory, detections, calibration)
    
    # Reset
    engine.reset_match_state(starting_over=10)
    
    match_state = engine.get_match_state()
    assert match_state.over_number == 10
    assert match_state.ball_number == 0
    assert match_state.legal_deliveries == 0


# ============================================================================
# Calibration Tests
# ============================================================================

def test_update_calibration():
    """Test update_calibration method."""
    engine = DecisionEngine()
    
    new_calibration = create_test_calibration()
    new_calibration.wide_guidelines = {"left": -1.5, "right": 1.5}
    
    engine.update_calibration(new_calibration)
    
    assert engine.calibration == new_calibration
    assert engine.wide_detector.calibration == new_calibration


def test_process_without_calibration():
    """Test that processing without calibration returns None."""
    engine = DecisionEngine()
    
    frame = Frame(
        camera_id="cam1",
        frame_number=1,
        timestamp=1.0,
        image=np.zeros((720, 1280, 3), dtype=np.uint8)
    )
    
    detection_result = DetectionResult(
        frame=frame,
        detections=create_test_detections(),
        processing_time_ms=10.0
    )
    
    track_state = TrackState(
        track_id="track_1",
        position=Position3D(x=0.0, y=1.0, z=0.0),
        velocity=Vector3D(vx=0.0, vy=0.0, vz=20.0),
        acceleration=Vector3D(vx=0.0, vy=0.0, vz=0.0),
        covariance=np.eye(9),
        last_seen=1.0,
        occlusion_duration=0,
        confidence=0.95
    )
    
    trajectory = create_test_trajectory()
    
    # Process without calibration
    decision = engine.process_frame(detection_result, track_state, trajectory)
    
    # Should return None without calibration
    assert decision is None


# ============================================================================
# Decision History Tests
# ============================================================================

def test_get_last_decisions():
    """Test get_last_decisions method."""
    engine = DecisionEngine()
    calibration = create_test_calibration()
    
    # Make 5 decisions using process_frame
    for i in range(5):
        trajectory = create_test_trajectory(timestamp=float(i))
        detections = create_test_detections()
        
        # Create frame and detection result
        frame = Frame(
            camera_id="cam1",
            frame_number=i,
            timestamp=float(i),
            image=np.zeros((720, 1280, 3), dtype=np.uint8)
        )
        
        detection_result = DetectionResult(
            frame=frame,
            detections=detections,
            processing_time_ms=10.0
        )
        
        track_state = TrackState(
            track_id="track_1",
            position=Position3D(x=0.0, y=1.0, z=0.0),
            velocity=Vector3D(vx=0.0, vy=0.0, vz=20.0),
            acceleration=Vector3D(vx=0.0, vy=0.0, vz=0.0),
            covariance=np.eye(9),
            last_seen=float(i),
            occlusion_duration=0,
            confidence=0.95
        )
        
        engine.process_frame(detection_result, track_state, trajectory, calibration)
    
    # Get last 3
    last_3 = engine.get_last_decisions(count=3)
    assert len(last_3) == 3
    
    # Get all
    all_decisions = engine.get_last_decisions(count=10)
    assert len(all_decisions) == 5


def test_decision_history_cleared_on_reset():
    """Test that decision history is cleared on reset."""
    engine = DecisionEngine()
    calibration = create_test_calibration()
    
    # Make some decisions
    for i in range(3):
        trajectory = create_test_trajectory(timestamp=float(i))
        detections = create_test_detections()
        engine.classify_delivery(trajectory, detections, calibration)
    
    # Reset
    engine.reset_match_state()
    
    # History should be cleared
    assert len(engine.get_last_decisions()) == 0


# ============================================================================
# Configuration Tests
# ============================================================================

def test_config_disable_detectors():
    """Test disabling specific detectors via config."""
    config = DecisionEngineConfig(
        enable_wide_detection=False,
        enable_no_ball_detection=False
    )
    engine = DecisionEngine(config=config)
    
    assert engine.config.enable_wide_detection is False
    assert engine.config.enable_no_ball_detection is False


def test_config_validation():
    """Test configuration validation."""
    # Valid config
    config = DecisionEngineConfig(
        min_confidence_threshold=0.75,
        review_threshold=0.85
    )
    assert config.min_confidence_threshold == 0.75
    
    # Invalid threshold (out of range)
    with pytest.raises(ValueError):
        DecisionEngineConfig(min_confidence_threshold=1.5)
    
    with pytest.raises(ValueError):
        DecisionEngineConfig(review_threshold=-0.1)
