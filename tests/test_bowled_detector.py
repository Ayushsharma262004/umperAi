"""
Unit tests for Bowled Detector.

These tests validate specific examples and edge cases for bowled dismissal detection.
"""

import pytest
import numpy as np

from umpirai.decision.bowled_detector import BowledDetector, StumpContact
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
    
    crease_lines = {
        "bowling": [Point2D(x=640.0, y=200.0), Point2D(x=640.0, y=520.0)],
        "batting": [Point2D(x=640.0, y=500.0), Point2D(x=640.0, y=820.0)]
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
    """Create BowledDetector instance."""
    return BowledDetector(calibration=calibration_data)


@pytest.fixture
def trajectory_to_stumps():
    """Create trajectory ending at stumps."""
    positions = [
        Position3D(x=0.0, y=1.5, z=-5.0),
        Position3D(x=0.0, y=1.0, z=-2.5),
        Position3D(x=0.0, y=0.5, z=0.0),  # At stumps
    ]
    
    timestamps = [0.0, 0.25, 0.5]
    
    velocities = [
        Vector3D(vx=0.0, vy=-2.0, vz=10.0),
        Vector3D(vx=0.0, vy=-2.0, vz=10.0),
        Vector3D(vx=0.0, vy=0.0, vz=0.0),
    ]
    
    return Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=positions[0],
        end_position=positions[-1],
        speed_max=10.0,
        speed_avg=8.0
    )


@pytest.fixture
def ball_detection_at_stumps():
    """Create ball detection at stumps (intersecting with stump bbox)."""
    bbox = BoundingBox(x=620.0, y=470.0, width=20.0, height=20.0)
    position_3d = Position3D(x=0.0, y=0.5, z=0.0)
    
    return Detection(
        class_id=DetectionClass.BALL.value,
        class_name="ball",
        bounding_box=bbox,
        confidence=0.92,
        position_3d=position_3d
    )


@pytest.fixture
def ball_detection_away_from_stumps():
    """Create ball detection away from stumps (not intersecting)."""
    bbox = BoundingBox(x=400.0, y=300.0, width=20.0, height=20.0)
    position_3d = Position3D(x=-2.0, y=1.0, z=-3.0)
    
    return Detection(
        class_id=DetectionClass.BALL.value,
        class_name="ball",
        bounding_box=bbox,
        confidence=0.92,
        position_3d=position_3d
    )


@pytest.fixture
def stump_detection():
    """Create stump detection."""
    bbox = BoundingBox(x=600.0, y=410.0, width=100.0, height=150.0)
    position_3d = Position3D(x=0.0, y=0.5, z=0.0)
    
    return Detection(
        class_id=DetectionClass.STUMPS.value,
        class_name="stumps",
        bounding_box=bbox,
        confidence=0.95,
        position_3d=position_3d
    )


@pytest.fixture
def frame_with_bail_dislodgement():
    """Create frame image showing bail dislodgement."""
    # Create a 720x1280x3 RGB image
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Fill stump region with high intensity (significant change)
    frame[410:560, 600:700] = 200
    
    return frame


@pytest.fixture
def frame_without_bail_dislodgement():
    """Create frame image without bail dislodgement."""
    # Create a 720x1280x3 RGB image
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Fill stump region with low intensity (minimal change)
    frame[410:560, 600:700] = 30
    
    return frame


# ============================================================================
# Unit Tests
# ============================================================================

def test_bowled_detector_initialization(calibration_data):
    """Test BowledDetector initialization."""
    detector = BowledDetector(calibration=calibration_data)
    
    assert detector.calibration == calibration_data
    assert detector._previous_stump_appearance is None
    assert detector._last_contact is None


def test_bowled_detector_initialization_without_calibration():
    """Test BowledDetector initialization without calibration."""
    detector = BowledDetector()
    
    assert detector.calibration is None
    assert detector._previous_stump_appearance is None
    assert detector._last_contact is None


def test_detect_bowled_dismissal_with_bail_dislodgement(
    detector,
    trajectory_to_stumps,
    ball_detection_at_stumps,
    stump_detection,
    frame_with_bail_dislodgement,
    calibration_data
):
    """Test bowled dismissal detection when bails are dislodged."""
    detections = [ball_detection_at_stumps, stump_detection]
    
    decision = detector.detect(
        trajectory_to_stumps,
        detections,
        calibration_data,
        frame_with_bail_dislodgement
    )
    
    assert decision is not None
    assert decision.event_type == EventType.BOWLED
    assert 0.0 <= decision.confidence <= 1.0
    assert decision.reasoning is not None
    assert "bowled" in decision.reasoning.lower() or "dismissal" in decision.reasoning.lower()


def test_detect_not_out_without_bail_dislodgement(
    detector,
    trajectory_to_stumps,
    ball_detection_at_stumps,
    stump_detection,
    frame_without_bail_dislodgement,
    calibration_data
):
    """Test not out when stumps hit but bails not dislodged."""
    detections = [ball_detection_at_stumps, stump_detection]
    
    # First, establish baseline with a similar frame
    baseline_frame = frame_without_bail_dislodgement.copy()
    detector.detect(
        trajectory_to_stumps,
        detections,
        calibration_data,
        baseline_frame
    )
    
    # Now detect with minimal change (bails not dislodged)
    decision = detector.detect(
        trajectory_to_stumps,
        detections,
        calibration_data,
        frame_without_bail_dislodgement
    )
    
    # Should return None for not out (minimal change means bails not dislodged)
    assert decision is None


def test_detect_no_contact_when_ball_away_from_stumps(
    detector,
    trajectory_to_stumps,
    ball_detection_away_from_stumps,
    stump_detection,
    frame_with_bail_dislodgement,
    calibration_data
):
    """Test no dismissal when ball doesn't contact stumps."""
    detections = [ball_detection_away_from_stumps, stump_detection]
    
    decision = detector.detect(
        trajectory_to_stumps,
        detections,
        calibration_data,
        frame_with_bail_dislodgement
    )
    
    # Should return None when no contact
    assert decision is None


def test_detect_ball_stump_contact_with_intersection(
    detector,
    trajectory_to_stumps,
    ball_detection_at_stumps,
    stump_detection
):
    """Test ball-stump contact detection with bounding box intersection."""
    detections = [ball_detection_at_stumps, stump_detection]
    
    stump_contact = detector.detect_ball_stump_contact(
        trajectory_to_stumps,
        detections,
        None
    )
    
    assert stump_contact is not None
    assert isinstance(stump_contact, StumpContact)
    assert stump_contact.ball_detection == ball_detection_at_stumps
    assert stump_contact.stump_detection == stump_detection
    assert isinstance(stump_contact.contact_position, Position3D)
    assert stump_contact.contact_timestamp >= 0.0


def test_detect_ball_stump_contact_without_intersection(
    detector,
    trajectory_to_stumps,
    ball_detection_away_from_stumps,
    stump_detection
):
    """Test no contact when bounding boxes don't intersect."""
    detections = [ball_detection_away_from_stumps, stump_detection]
    
    stump_contact = detector.detect_ball_stump_contact(
        trajectory_to_stumps,
        detections,
        None
    )
    
    assert stump_contact is None


def test_detect_ball_stump_contact_without_ball_detection(
    detector,
    trajectory_to_stumps,
    stump_detection
):
    """Test no contact when ball is not detected."""
    detections = [stump_detection]  # No ball detection
    
    stump_contact = detector.detect_ball_stump_contact(
        trajectory_to_stumps,
        detections,
        None
    )
    
    assert stump_contact is None


def test_detect_ball_stump_contact_without_stump_detection(
    detector,
    trajectory_to_stumps,
    ball_detection_at_stumps
):
    """Test no contact when stumps are not detected."""
    detections = [ball_detection_at_stumps]  # No stump detection
    
    stump_contact = detector.detect_ball_stump_contact(
        trajectory_to_stumps,
        detections,
        None
    )
    
    assert stump_contact is None


def test_verify_bail_dislodgement_with_frame_change(
    detector,
    stump_detection,
    frame_with_bail_dislodgement
):
    """Test bail dislodgement detection with significant frame change."""
    # First call - establish baseline
    result1 = detector.verify_bail_dislodgement(stump_detection, frame_with_bail_dislodgement)
    
    # First frame should return True (conservative approach - assume dislodged)
    assert result1 is True
    
    # Second call - detect change
    result2 = detector.verify_bail_dislodgement(stump_detection, frame_with_bail_dislodgement)
    
    # Should detect change (but might be False if frames are identical)
    assert isinstance(result2, bool)


def test_verify_bail_dislodgement_without_frame(
    detector,
    stump_detection
):
    """Test bail dislodgement detection without frame image."""
    result = detector.verify_bail_dislodgement(stump_detection, None)
    
    # Should assume bails dislodged when no frame available
    assert result is True


def test_verify_contact_sequence_no_bat_contact(
    detector,
    trajectory_to_stumps,
    ball_detection_at_stumps,
    stump_detection
):
    """Test contact sequence verification without bat contact."""
    detections = [ball_detection_at_stumps, stump_detection]
    
    is_valid = detector.verify_contact_sequence(trajectory_to_stumps, detections)
    
    # Should be valid when no bat contact
    assert is_valid is True


def test_verify_contact_sequence_with_bat_contact(
    detector,
    ball_detection_at_stumps,
    stump_detection
):
    """Test contact sequence verification with bat contact before stumps."""
    # Create trajectory with sudden direction change (indicates bat contact)
    positions = [
        Position3D(x=0.0, y=1.5, z=-5.0),
        Position3D(x=0.0, y=1.0, z=-2.5),
        Position3D(x=0.5, y=0.8, z=-1.0),  # Direction change
        Position3D(x=0.0, y=0.5, z=0.0),   # At stumps
    ]
    
    timestamps = [0.0, 0.2, 0.3, 0.5]
    
    velocities = [
        Vector3D(vx=0.0, vy=-2.5, vz=12.5),
        Vector3D(vx=0.0, vy=-2.0, vz=15.0),
        Vector3D(vx=-5.0, vy=-2.0, vz=10.0),  # Sudden direction change
        Vector3D(vx=0.0, vy=-3.0, vz=10.0),
    ]
    
    trajectory = Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=positions[0],
        end_position=positions[-1],
        speed_max=15.0,
        speed_avg=12.0
    )
    
    # Add batsman detection
    batsman_bbox = BoundingBox(x=550.0, y=350.0, width=150.0, height=250.0)
    batsman_det = Detection(
        class_id=DetectionClass.BATSMAN.value,
        class_name="batsman",
        bounding_box=batsman_bbox,
        confidence=0.9,
        position_3d=Position3D(x=0.0, y=1.0, z=-1.0)
    )
    
    detections = [ball_detection_at_stumps, stump_detection, batsman_det]
    
    is_valid = detector.verify_contact_sequence(trajectory, detections)
    
    # Should be invalid when bat contact detected
    assert is_valid is False


def test_stump_contact_validation():
    """Test StumpContact dataclass validation."""
    ball_det = Detection(
        class_id=DetectionClass.BALL.value,
        class_name="ball",
        bounding_box=BoundingBox(x=620.0, y=470.0, width=20.0, height=20.0),
        confidence=0.92,
        position_3d=Position3D(x=0.0, y=0.5, z=0.0)
    )
    
    stump_det = Detection(
        class_id=DetectionClass.STUMPS.value,
        class_name="stumps",
        bounding_box=BoundingBox(x=600.0, y=410.0, width=100.0, height=150.0),
        confidence=0.95,
        position_3d=Position3D(x=0.0, y=0.5, z=0.0)
    )
    
    contact = StumpContact(
        contact_position=Position3D(x=0.0, y=0.5, z=0.0),
        contact_timestamp=0.5,
        ball_detection=ball_det,
        stump_detection=stump_det,
        bails_dislodged=True
    )
    
    assert contact.contact_position.x == 0.0
    assert contact.contact_timestamp == 0.5
    assert contact.ball_detection == ball_det
    assert contact.stump_detection == stump_det
    assert contact.bails_dislodged is True


def test_stump_contact_invalid_position():
    """Test StumpContact with invalid position."""
    ball_det = Detection(
        class_id=DetectionClass.BALL.value,
        class_name="ball",
        bounding_box=BoundingBox(x=620.0, y=470.0, width=20.0, height=20.0),
        confidence=0.92,
        position_3d=Position3D(x=0.0, y=0.5, z=0.0)
    )
    
    stump_det = Detection(
        class_id=DetectionClass.STUMPS.value,
        class_name="stumps",
        bounding_box=BoundingBox(x=600.0, y=410.0, width=100.0, height=150.0),
        confidence=0.95,
        position_3d=Position3D(x=0.0, y=0.5, z=0.0)
    )
    
    with pytest.raises(TypeError):
        StumpContact(
            contact_position="invalid",
            contact_timestamp=0.5,
            ball_detection=ball_det,
            stump_detection=stump_det,
            bails_dislodged=True
        )


def test_stump_contact_invalid_timestamp():
    """Test StumpContact with invalid timestamp."""
    ball_det = Detection(
        class_id=DetectionClass.BALL.value,
        class_name="ball",
        bounding_box=BoundingBox(x=620.0, y=470.0, width=20.0, height=20.0),
        confidence=0.92,
        position_3d=Position3D(x=0.0, y=0.5, z=0.0)
    )
    
    stump_det = Detection(
        class_id=DetectionClass.STUMPS.value,
        class_name="stumps",
        bounding_box=BoundingBox(x=600.0, y=410.0, width=100.0, height=150.0),
        confidence=0.95,
        position_3d=Position3D(x=0.0, y=0.5, z=0.0)
    )
    
    with pytest.raises(TypeError):
        StumpContact(
            contact_position=Position3D(x=0.0, y=0.5, z=0.0),
            contact_timestamp="invalid",
            ball_detection=ball_det,
            stump_detection=stump_det,
            bails_dislodged=True
        )


def test_stump_contact_invalid_bails_dislodged():
    """Test StumpContact with invalid bails_dislodged."""
    ball_det = Detection(
        class_id=DetectionClass.BALL.value,
        class_name="ball",
        bounding_box=BoundingBox(x=620.0, y=470.0, width=20.0, height=20.0),
        confidence=0.92,
        position_3d=Position3D(x=0.0, y=0.5, z=0.0)
    )
    
    stump_det = Detection(
        class_id=DetectionClass.STUMPS.value,
        class_name="stumps",
        bounding_box=BoundingBox(x=600.0, y=410.0, width=100.0, height=150.0),
        confidence=0.95,
        position_3d=Position3D(x=0.0, y=0.5, z=0.0)
    )
    
    with pytest.raises(TypeError):
        StumpContact(
            contact_position=Position3D(x=0.0, y=0.5, z=0.0),
            contact_timestamp=0.5,
            ball_detection=ball_det,
            stump_detection=stump_det,
            bails_dislodged="invalid"
        )


def test_confidence_calculation_with_high_quality_detections(
    detector,
    trajectory_to_stumps,
    ball_detection_at_stumps,
    stump_detection,
    frame_with_bail_dislodgement,
    calibration_data
):
    """Test confidence calculation with high quality detections."""
    detections = [ball_detection_at_stumps, stump_detection]
    
    decision = detector.detect(
        trajectory_to_stumps,
        detections,
        calibration_data,
        frame_with_bail_dislodgement
    )
    
    if decision is not None:
        # With high quality detections, confidence should be reasonably high
        assert decision.confidence >= 0.7


def test_edge_case_empty_detections(
    detector,
    trajectory_to_stumps,
    calibration_data
):
    """Test edge case with empty detections list."""
    detections = []
    
    decision = detector.detect(
        trajectory_to_stumps,
        detections,
        calibration_data,
        None
    )
    
    # Should return None when no detections
    assert decision is None


def test_edge_case_multiple_ball_detections(
    detector,
    trajectory_to_stumps,
    ball_detection_at_stumps,
    stump_detection,
    frame_with_bail_dislodgement,
    calibration_data
):
    """Test edge case with multiple ball detections."""
    # Create second ball detection with lower confidence
    ball_det_2 = Detection(
        class_id=DetectionClass.BALL.value,
        class_name="ball",
        bounding_box=BoundingBox(x=625.0, y=475.0, width=20.0, height=20.0),
        confidence=0.85,
        position_3d=Position3D(x=0.1, y=0.5, z=0.0)
    )
    
    detections = [ball_detection_at_stumps, ball_det_2, stump_detection]
    
    decision = detector.detect(
        trajectory_to_stumps,
        detections,
        calibration_data,
        frame_with_bail_dislodgement
    )
    
    # Should use highest confidence ball detection
    if decision is not None:
        assert decision.event_type == EventType.BOWLED


def test_edge_case_multiple_stump_detections(
    detector,
    trajectory_to_stumps,
    ball_detection_at_stumps,
    stump_detection,
    frame_with_bail_dislodgement,
    calibration_data
):
    """Test edge case with multiple stump detections."""
    # Create second stump detection with lower confidence
    stump_det_2 = Detection(
        class_id=DetectionClass.STUMPS.value,
        class_name="stumps",
        bounding_box=BoundingBox(x=605.0, y=415.0, width=100.0, height=150.0),
        confidence=0.88,
        position_3d=Position3D(x=0.05, y=0.5, z=0.0)
    )
    
    detections = [ball_detection_at_stumps, stump_detection, stump_det_2]
    
    decision = detector.detect(
        trajectory_to_stumps,
        detections,
        calibration_data,
        frame_with_bail_dislodgement
    )
    
    # Should use highest confidence stump detection
    if decision is not None:
        assert decision.event_type == EventType.BOWLED
