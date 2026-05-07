"""
Unit tests for No Ball Detector.

These tests validate specific examples and edge cases for no ball detection.
"""

import pytest
import numpy as np

from umpirai.decision.no_ball_detector import NoBallDetector, BallReleasePoint
from umpirai.models.data_models import (
    Position3D,
    Vector3D,
    Trajectory,
    Detection,
    BoundingBox,
    DetectionClass,
    EventType,
)
from umpirai.calibration.calibration_manager import (
    CalibrationData,
    Point2D,
    CameraCalibration,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def calibration_data():
    """Create test calibration data."""
    pitch_boundary = [
        Point2D(x=0.0, y=0.0),
        Point2D(x=1280.0, y=0.0),
        Point2D(x=1280.0, y=720.0),
        Point2D(x=0.0, y=720.0)
    ]
    
    # Store the bowling crease z-coordinate in the y field (hack for testing)
    # In production, this would use proper 3D calibration
    crease_lines = {
        "bowling": [Point2D(x=640.0, y=-10.0), Point2D(x=640.0, y=-10.0)],  # z=-10.0
        "batting": [Point2D(x=640.0, y=0.0), Point2D(x=640.0, y=0.0)]  # z=0.0
    }
    
    wide_guidelines = {
        "left": -1.0,
        "right": 1.0
    }
    
    stump_positions = {
        "bowling": Point2D(x=640.0, y=200.0),
        "batting": Point2D(x=640.0, y=600.0)
    }
    
    camera_calibrations = {
        "cam1": CameraCalibration(
            camera_id="cam1",
            homography=np.eye(3),
            intrinsics=None
        )
    }
    
    return CalibrationData(
        calibration_name="test_calibration",
        created_at="2024-01-01T00:00:00",
        pitch_boundary=pitch_boundary,
        crease_lines=crease_lines,
        wide_guidelines=wide_guidelines,
        stump_positions=stump_positions,
        camera_calibrations=camera_calibrations
    )


@pytest.fixture
def detector(calibration_data):
    """Create NoBallDetector instance."""
    return NoBallDetector(calibration=calibration_data)


@pytest.fixture
def trajectory_with_release():
    """Create trajectory with clear release point."""
    positions = [
        Position3D(x=0.0, y=2.0, z=-10.0),
        Position3D(x=0.0, y=1.8, z=-8.0),
        Position3D(x=0.0, y=1.5, z=-6.0),  # Release point (velocity spike)
        Position3D(x=0.0, y=1.2, z=-4.0),
        Position3D(x=0.0, y=0.8, z=-2.0),
        Position3D(x=0.0, y=0.5, z=0.0),
    ]
    
    timestamps = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    
    velocities = [
        Vector3D(vx=0.0, vy=-2.0, vz=20.0),
        Vector3D(vx=0.0, vy=-3.0, vz=20.0),
        Vector3D(vx=0.0, vy=-3.0, vz=30.0),  # Velocity spike at release
        Vector3D(vx=0.0, vy=-3.0, vz=20.0),
        Vector3D(vx=0.0, vy=-4.0, vz=20.0),
        Vector3D(vx=0.0, vy=-3.0, vz=20.0),
    ]
    
    return Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=positions[0],
        end_position=positions[-1],
        speed_max=30.0,
        speed_avg=22.0
    )


@pytest.fixture
def bowler_detection_over_crease():
    """Create bowler detection with foot over crease."""
    bbox = BoundingBox(x=600.0, y=150.0, width=80.0, height=160.0)
    foot_position = Position3D(x=0.0, y=0.1, z=-9.5)  # Over crease at z=-10
    
    return Detection(
        class_id=DetectionClass.BOWLER.value,
        class_name="bowler",
        bounding_box=bbox,
        confidence=0.92,
        position_3d=foot_position
    )


@pytest.fixture
def bowler_detection_behind_crease():
    """Create bowler detection with foot behind crease."""
    bbox = BoundingBox(x=600.0, y=150.0, width=80.0, height=160.0)
    foot_position = Position3D(x=0.0, y=0.1, z=-10.5)  # Behind crease at z=-10
    
    return Detection(
        class_id=DetectionClass.BOWLER.value,
        class_name="bowler",
        bounding_box=bbox,
        confidence=0.92,
        position_3d=foot_position
    )


@pytest.fixture
def crease_detection():
    """Create crease line detection."""
    bbox = BoundingBox(x=200.0, y=300.0, width=880.0, height=10.0)
    
    return Detection(
        class_id=DetectionClass.CREASE.value,
        class_name="crease",
        bounding_box=bbox,
        confidence=0.95,
        position_3d=None
    )


# ============================================================================
# Unit Tests
# ============================================================================

def test_no_ball_detector_initialization(calibration_data):
    """Test NoBallDetector initialization."""
    detector = NoBallDetector(calibration=calibration_data)
    
    assert detector.calibration == calibration_data
    assert detector._last_release_point is None


def test_no_ball_detector_initialization_without_calibration():
    """Test NoBallDetector initialization without calibration."""
    detector = NoBallDetector()
    
    assert detector.calibration is None
    assert detector._last_release_point is None


def test_detect_no_ball_foot_over_crease(
    detector,
    trajectory_with_release,
    bowler_detection_over_crease,
    crease_detection,
    calibration_data
):
    """Test no ball detection when foot is over crease."""
    detections = [bowler_detection_over_crease, crease_detection]
    
    decision = detector.detect(trajectory_with_release, detections, calibration_data)
    
    assert decision is not None
    assert decision.event_type == EventType.NO_BALL
    assert 0.0 <= decision.confidence <= 1.0
    assert decision.reasoning is not None
    assert "No ball" in decision.reasoning or "no ball" in decision.reasoning.lower()


def test_detect_legal_delivery_foot_behind_crease(
    detector,
    trajectory_with_release,
    bowler_detection_behind_crease,
    crease_detection,
    calibration_data
):
    """Test legal delivery when foot is behind crease."""
    detections = [bowler_detection_behind_crease, crease_detection]
    
    decision = detector.detect(trajectory_with_release, detections, calibration_data)
    
    # Should return None for legal delivery
    assert decision is None


def test_detect_no_ball_foot_exactly_on_crease(
    detector,
    trajectory_with_release,
    crease_detection,
    calibration_data
):
    """Test edge case: foot exactly on crease line."""
    # Create bowler detection with foot exactly on crease
    bbox = BoundingBox(x=600.0, y=150.0, width=80.0, height=160.0)
    foot_position = Position3D(x=0.0, y=0.1, z=-10.0)  # Exactly on crease
    
    bowler_det = Detection(
        class_id=DetectionClass.BOWLER.value,
        class_name="bowler",
        bounding_box=bbox,
        confidence=0.92,
        position_3d=foot_position
    )
    
    detections = [bowler_det, crease_detection]
    
    decision = detector.detect(trajectory_with_release, detections, calibration_data)
    
    # Foot on crease should be no ball
    assert decision is not None
    assert decision.event_type == EventType.NO_BALL


def test_ball_release_detection_with_velocity_spike(detector, trajectory_with_release):
    """Test ball release detection with velocity spike."""
    release_point = detector.detect_ball_release(trajectory_with_release)
    
    assert release_point is not None
    assert isinstance(release_point, BallReleasePoint)
    assert release_point.velocity_change >= detector.VELOCITY_CHANGE_THRESHOLD
    assert release_point.position is not None
    assert 0.0 <= release_point.timestamp <= trajectory_with_release.timestamps[-1]


def test_ball_release_detection_no_velocity_spike(detector):
    """Test ball release detection with no velocity spike."""
    # Create trajectory with constant velocity (no release spike)
    positions = [
        Position3D(x=0.0, y=2.0, z=-10.0),
        Position3D(x=0.0, y=1.5, z=-5.0),
        Position3D(x=0.0, y=1.0, z=0.0),
    ]
    
    timestamps = [0.0, 0.25, 0.5]
    
    velocities = [
        Vector3D(vx=0.0, vy=-2.0, vz=20.0),
        Vector3D(vx=0.0, vy=-2.0, vz=20.0),
        Vector3D(vx=0.0, vy=-2.0, vz=20.0),
    ]
    
    trajectory = Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=positions[0],
        end_position=positions[-1],
        speed_max=20.0,
        speed_avg=20.0
    )
    
    release_point = detector.detect_ball_release(trajectory)
    
    # Should not detect release without velocity spike
    assert release_point is None


def test_ball_release_detection_empty_trajectory(detector):
    """Test ball release detection with empty trajectory."""
    trajectory = Trajectory(
        positions=[],
        timestamps=[],
        velocities=[],
        start_position=Position3D(x=0.0, y=0.0, z=0.0),
        end_position=None,
        speed_max=0.0,
        speed_avg=0.0
    )
    
    release_point = detector.detect_ball_release(trajectory)
    
    assert release_point is None


def test_calculate_foot_crease_distance_foot_behind(detector):
    """Test foot-crease distance calculation when foot is behind crease."""
    foot_position = Position3D(x=0.0, y=0.1, z=-10.5)
    crease_line_z = -10.0
    
    distance = detector.calculate_foot_crease_distance(foot_position, crease_line_z)
    
    # Distance should be positive (foot behind crease)
    assert distance > 0
    assert abs(distance - 0.5) < 0.001


def test_calculate_foot_crease_distance_foot_over(detector):
    """Test foot-crease distance calculation when foot is over crease."""
    foot_position = Position3D(x=0.0, y=0.1, z=-9.5)
    crease_line_z = -10.0
    
    distance = detector.calculate_foot_crease_distance(foot_position, crease_line_z)
    
    # Distance should be negative (foot over crease)
    assert distance < 0
    assert abs(distance - (-0.5)) < 0.001


def test_calculate_foot_crease_distance_foot_on_crease(detector):
    """Test foot-crease distance calculation when foot is exactly on crease."""
    foot_position = Position3D(x=0.0, y=0.1, z=-10.0)
    crease_line_z = -10.0
    
    distance = detector.calculate_foot_crease_distance(foot_position, crease_line_z)
    
    # Distance should be zero
    assert abs(distance) < 0.001


def test_is_no_ball_foot_over_crease(detector):
    """Test is_no_ball when foot is over crease."""
    foot_position = Position3D(x=0.0, y=0.1, z=-9.5)
    crease_line_z = -10.0
    
    result = detector.is_no_ball(foot_position, crease_line_z)
    
    assert result is True


def test_is_no_ball_foot_behind_crease(detector):
    """Test is_no_ball when foot is behind crease."""
    foot_position = Position3D(x=0.0, y=0.1, z=-10.5)
    crease_line_z = -10.0
    
    result = detector.is_no_ball(foot_position, crease_line_z)
    
    assert result is False


def test_is_no_ball_foot_on_crease(detector):
    """Test is_no_ball when foot is exactly on crease."""
    foot_position = Position3D(x=0.0, y=0.1, z=-10.0)
    crease_line_z = -10.0
    
    result = detector.is_no_ball(foot_position, crease_line_z)
    
    # Foot on crease should be no ball
    assert result is True


def test_detect_no_ball_without_bowler_detection(
    detector,
    trajectory_with_release,
    crease_detection,
    calibration_data
):
    """Test no ball detection when bowler is not detected (occlusion)."""
    detections = [crease_detection]  # No bowler detection
    
    decision = detector.detect(trajectory_with_release, detections, calibration_data)
    
    # Should create uncertain decision due to occlusion
    assert decision is not None
    assert decision.requires_review is True
    assert decision.confidence < 0.80
    assert "occluded" in decision.reasoning.lower() or "uncertain" in decision.reasoning.lower()


def test_detect_no_ball_without_release_point(
    detector,
    bowler_detection_over_crease,
    crease_detection,
    calibration_data
):
    """Test no ball detection when ball release cannot be detected."""
    # Create trajectory without velocity spike (no release point)
    positions = [
        Position3D(x=0.0, y=2.0, z=-10.0),
        Position3D(x=0.0, y=1.5, z=-5.0),
    ]
    
    timestamps = [0.0, 0.5]
    
    velocities = [
        Vector3D(vx=0.0, vy=-1.0, vz=10.0),
        Vector3D(vx=0.0, vy=-1.0, vz=10.0),
    ]
    
    trajectory = Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=positions[0],
        end_position=positions[-1],
        speed_max=10.0,
        speed_avg=10.0
    )
    
    detections = [bowler_detection_over_crease, crease_detection]
    
    decision = detector.detect(trajectory, detections, calibration_data)
    
    # Should return None if release point cannot be detected
    assert decision is None


def test_ball_release_point_validation():
    """Test BallReleasePoint validation."""
    position = Position3D(x=0.0, y=1.5, z=-6.0)
    
    release_point = BallReleasePoint(
        position=position,
        timestamp=0.2,
        velocity_change=10.0
    )
    
    assert release_point.position == position
    assert release_point.timestamp == 0.2
    assert release_point.velocity_change == 10.0


def test_ball_release_point_invalid_position():
    """Test BallReleasePoint with invalid position."""
    with pytest.raises(TypeError):
        BallReleasePoint(
            position="invalid",
            timestamp=0.2,
            velocity_change=10.0
        )


def test_ball_release_point_invalid_timestamp():
    """Test BallReleasePoint with invalid timestamp."""
    position = Position3D(x=0.0, y=1.5, z=-6.0)
    
    with pytest.raises(TypeError):
        BallReleasePoint(
            position=position,
            timestamp="invalid",
            velocity_change=10.0
        )


def test_calculate_foot_crease_distance_invalid_inputs(detector):
    """Test calculate_foot_crease_distance with invalid inputs."""
    foot_position = Position3D(x=0.0, y=0.1, z=-10.0)
    
    with pytest.raises(TypeError):
        detector.calculate_foot_crease_distance("invalid", -10.0)
    
    with pytest.raises(TypeError):
        detector.calculate_foot_crease_distance(foot_position, "invalid")


def test_is_no_ball_invalid_inputs(detector):
    """Test is_no_ball with invalid inputs."""
    foot_position = Position3D(x=0.0, y=0.1, z=-10.0)
    
    with pytest.raises(TypeError):
        detector.is_no_ball("invalid", -10.0)
    
    with pytest.raises(TypeError):
        detector.is_no_ball(foot_position, "invalid")


def test_confidence_calculation_with_high_quality_detections(
    detector,
    trajectory_with_release,
    bowler_detection_over_crease,
    crease_detection,
    calibration_data
):
    """Test confidence calculation with high quality detections."""
    detections = [bowler_detection_over_crease, crease_detection]
    
    decision = detector.detect(trajectory_with_release, detections, calibration_data)
    
    assert decision is not None
    # With high quality detections, confidence should be reasonably high
    assert decision.confidence >= 0.7


def test_confidence_calculation_with_low_quality_detections(
    detector,
    trajectory_with_release,
    crease_detection,
    calibration_data
):
    """Test confidence calculation with low quality detections."""
    # Create bowler detection with low confidence
    bbox = BoundingBox(x=600.0, y=150.0, width=80.0, height=160.0)
    foot_position = Position3D(x=0.0, y=0.1, z=-9.5)  # Over crease
    
    bowler_det = Detection(
        class_id=DetectionClass.BOWLER.value,
        class_name="bowler",
        bounding_box=bbox,
        confidence=0.65,  # Low confidence
        position_3d=foot_position
    )
    
    detections = [bowler_det, crease_detection]
    
    decision = detector.detect(trajectory_with_release, detections, calibration_data)
    
    assert decision is not None
    # With low quality detections, confidence might be lower
    # But we don't enforce a specific threshold in this test
    assert 0.0 <= decision.confidence <= 1.0
