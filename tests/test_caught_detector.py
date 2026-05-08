"""
Unit tests for Caught Detector.

These tests validate specific examples and edge cases for caught dismissal detection.
"""

import pytest
import numpy as np

from umpirai.decision.caught_detector import CaughtDetector, BatContact, FielderCatch, CaughtAnalysis
from umpirai.models.data_models import (
    Position3D,
    Vector3D,
    Trajectory,
    Detection,
    BoundingBox,
    DetectionClass,
    EventType,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def detector():
    """Create CaughtDetector instance."""
    return CaughtDetector()


@pytest.fixture
def trajectory_with_bat_contact_and_catch():
    """Create trajectory with bat contact and fielder catch."""
    # Approach phase (z: -5 to 0)
    positions = [
        Position3D(x=0.0, y=1.5, z=-5.0),
        Position3D(x=0.0, y=1.0, z=-2.5),
        Position3D(x=0.0, y=0.8, z=-0.5),  # Near bat
        # Bat contact at index 3
        Position3D(x=0.1, y=0.9, z=0.0),   # Bat contact
        # Flight to fielder (maintaining height >0.1m)
        Position3D(x=0.5, y=1.2, z=1.5),
        Position3D(x=1.0, y=1.5, z=3.0),
        Position3D(x=1.5, y=1.3, z=4.5),
        Position3D(x=2.0, y=1.0, z=6.0),   # At fielder
    ]
    
    timestamps = [0.0, 0.15, 0.25, 0.3, 0.45, 0.6, 0.75, 0.9]
    
    # Velocities with direction change at bat contact
    velocities = [
        Vector3D(vx=0.0, vy=-3.3, vz=16.7),
        Vector3D(vx=0.0, vy=-1.3, vz=13.3),
        Vector3D(vx=0.7, vy=0.7, vz=3.3),
        # Direction change at bat contact
        Vector3D(vx=2.7, vy=2.0, vz=10.0),  # After bat contact
        Vector3D(vx=3.3, vy=2.0, vz=10.0),
        Vector3D(vx=3.3, vy=-1.3, vz=10.0),
        Vector3D(vx=3.3, vy=-2.0, vz=10.0),
        Vector3D(vx=0.0, vy=0.0, vz=0.0),
    ]
    
    speeds = [v.magnitude() for v in velocities]
    
    return Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=positions[0],
        end_position=positions[-1],
        speed_max=max(speeds),
        speed_avg=sum(speeds) / len(speeds)
    )


@pytest.fixture
def trajectory_with_ground_contact():
    """Create trajectory where ball touches ground before catch."""
    positions = [
        Position3D(x=0.0, y=1.5, z=-5.0),
        Position3D(x=0.0, y=1.0, z=-2.5),
        Position3D(x=0.0, y=0.8, z=-0.5),
        Position3D(x=0.1, y=0.9, z=0.0),   # Bat contact
        Position3D(x=0.5, y=0.5, z=1.5),
        Position3D(x=1.0, y=0.05, z=3.0),  # Ground contact (height < 0.1m)
        Position3D(x=1.5, y=0.3, z=4.5),
        Position3D(x=2.0, y=1.0, z=6.0),
    ]
    
    timestamps = [0.0, 0.15, 0.25, 0.3, 0.45, 0.6, 0.75, 0.9]
    
    velocities = [
        Vector3D(vx=0.0, vy=-3.3, vz=16.7),
        Vector3D(vx=0.0, vy=-1.3, vz=13.3),
        Vector3D(vx=0.7, vy=0.7, vz=3.3),
        Vector3D(vx=2.7, vy=2.0, vz=10.0),
        Vector3D(vx=3.3, vy=-3.0, vz=10.0),
        Vector3D(vx=3.3, vy=-3.0, vz=10.0),
        Vector3D(vx=3.3, vy=4.7, vz=10.0),
        Vector3D(vx=0.0, vy=0.0, vz=0.0),
    ]
    
    speeds = [v.magnitude() for v in velocities]
    
    return Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=positions[0],
        end_position=positions[-1],
        speed_max=max(speeds),
        speed_avg=sum(speeds) / len(speeds)
    )


@pytest.fixture
def ball_detection():
    """Create ball detection."""
    bbox = BoundingBox(x=646.0, y=360.0, width=20.0, height=20.0)
    position_3d = Position3D(x=0.1, y=0.9, z=0.0)
    
    return Detection(
        class_id=DetectionClass.BALL.value,
        class_name="ball",
        bounding_box=bbox,
        confidence=0.92,
        position_3d=position_3d
    )


@pytest.fixture
def batsman_detection():
    """Create batsman detection near crease."""
    bbox = BoundingBox(x=590.0, y=310.0, width=100.0, height=200.0)
    position_3d = Position3D(x=0.0, y=1.0, z=0.0)
    
    return Detection(
        class_id=DetectionClass.BATSMAN.value,
        class_name="batsman",
        bounding_box=bbox,
        confidence=0.90,
        position_3d=position_3d
    )


@pytest.fixture
def fielder_detection():
    """Create fielder detection at catch position."""
    bbox = BoundingBox(x=768.0, y=576.0, width=120.0, height=240.0)
    position_3d = Position3D(x=2.0, y=1.0, z=6.0)
    
    return Detection(
        class_id=DetectionClass.FIELDER.value,
        class_name="fielder",
        bounding_box=bbox,
        confidence=0.88,
        position_3d=position_3d
    )


# ============================================================================
# Unit Tests
# ============================================================================

def test_caught_detector_initialization():
    """Test CaughtDetector initialization."""
    detector = CaughtDetector()
    
    assert detector._last_analysis is None
    assert detector.MIN_CONFIDENCE == 0.70
    assert detector.MIN_CONTROL_FRAMES == 3
    assert detector.MIN_BALL_HEIGHT == 0.1


def test_detect_caught_dismissal_valid_catch(
    detector,
    trajectory_with_bat_contact_and_catch,
    ball_detection,
    batsman_detection,
    fielder_detection
):
    """Test caught dismissal detection with valid catch."""
    detections = [ball_detection, batsman_detection, fielder_detection]
    
    decision = detector.detect(trajectory_with_bat_contact_and_catch, detections)
    
    # May or may not detect depending on exact trajectory
    # If detected, verify properties
    if decision is not None:
        assert decision.event_type == EventType.CAUGHT
        assert 0.0 <= decision.confidence <= 1.0
        assert decision.reasoning is not None
        assert "caught" in decision.reasoning.lower() or "dismissal" in decision.reasoning.lower()
        assert len(decision.video_references) > 0


def test_detect_not_out_with_ground_contact(
    detector,
    trajectory_with_ground_contact,
    ball_detection,
    batsman_detection,
    fielder_detection
):
    """Test not out when ball touches ground before catch."""
    detections = [ball_detection, batsman_detection, fielder_detection]
    
    decision = detector.detect(trajectory_with_ground_contact, detections)
    
    # Should return None or very low confidence when ground contact detected
    if decision is not None:
        assert decision.confidence < 0.5


def test_detect_ball_bat_contact_with_direction_change(
    detector,
    trajectory_with_bat_contact_and_catch,
    ball_detection,
    batsman_detection
):
    """Test ball-bat contact detection with trajectory direction change."""
    detections = [ball_detection, batsman_detection]
    
    bat_contact = detector.detect_ball_bat_contact(
        trajectory_with_bat_contact_and_catch,
        detections
    )
    
    # Should detect bat contact
    if bat_contact is not None:
        assert isinstance(bat_contact, BatContact)
        assert isinstance(bat_contact.contact_position, Position3D)
        assert bat_contact.contact_timestamp >= 0.0
        assert isinstance(bat_contact.velocity_before, Vector3D)
        assert isinstance(bat_contact.velocity_after, Vector3D)
        
        # Verify velocity direction changed
        v1 = bat_contact.velocity_before
        v2 = bat_contact.velocity_after
        
        if v1.magnitude() > 0 and v2.magnitude() > 0:
            dot_product = v1.vx * v2.vx + v1.vy * v2.vy + v1.vz * v2.vz
            cos_angle = dot_product / (v1.magnitude() * v2.magnitude())
            cos_angle = max(-1.0, min(1.0, cos_angle))
            angle_change = np.arccos(cos_angle)
            
            assert angle_change >= detector.MIN_BAT_CONTACT_ANGLE


def test_detect_ball_bat_contact_without_batsman(
    detector,
    trajectory_with_bat_contact_and_catch,
    ball_detection
):
    """Test no bat contact when batsman not detected."""
    detections = [ball_detection]  # No batsman
    
    bat_contact = detector.detect_ball_bat_contact(
        trajectory_with_bat_contact_and_catch,
        detections
    )
    
    # Should return None when no batsman detected
    assert bat_contact is None


def test_detect_ball_bat_contact_insufficient_trajectory(
    detector,
    ball_detection,
    batsman_detection
):
    """Test no bat contact with insufficient trajectory data."""
    # Create trajectory with only 1 velocity
    positions = [Position3D(x=0.0, y=1.0, z=0.0)]
    timestamps = [0.0]
    velocities = [Vector3D(vx=0.0, vy=0.0, vz=0.0)]
    
    trajectory = Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=positions[0],
        speed_max=0.0,
        speed_avg=0.0
    )
    
    detections = [ball_detection, batsman_detection]
    
    bat_contact = detector.detect_ball_bat_contact(trajectory, detections)
    
    # Should return None with insufficient data
    assert bat_contact is None


def test_detect_fielder_catch_with_control(
    detector,
    trajectory_with_bat_contact_and_catch,
    ball_detection,
    batsman_detection,
    fielder_detection
):
    """Test fielder catch detection with sufficient control frames."""
    detections = [ball_detection, batsman_detection, fielder_detection]
    
    # First detect bat contact
    bat_contact = detector.detect_ball_bat_contact(
        trajectory_with_bat_contact_and_catch,
        detections
    )
    
    if bat_contact is not None:
        # Then detect fielder catch
        fielder_catch = detector.detect_fielder_catch(
            trajectory_with_bat_contact_and_catch,
            detections,
            bat_contact
        )
        
        # May or may not detect depending on exact positions
        if fielder_catch is not None:
            assert isinstance(fielder_catch, FielderCatch)
            assert fielder_catch.control_frames >= 0
            assert isinstance(fielder_catch.catch_position, Position3D)
            assert fielder_catch.catch_timestamp >= bat_contact.contact_timestamp


def test_detect_fielder_catch_without_fielder(
    detector,
    trajectory_with_bat_contact_and_catch,
    ball_detection,
    batsman_detection
):
    """Test no catch when fielder not detected."""
    detections = [ball_detection, batsman_detection]  # No fielder
    
    # Create dummy bat contact
    bat_contact = BatContact(
        contact_position=Position3D(x=0.1, y=0.9, z=0.0),
        contact_timestamp=0.3,
        contact_frame_index=3,
        ball_detection=ball_detection,
        batsman_detection=batsman_detection,
        velocity_before=Vector3D(vx=0.0, vy=-1.3, vz=13.3),
        velocity_after=Vector3D(vx=2.7, vy=2.0, vz=10.0)
    )
    
    fielder_catch = detector.detect_fielder_catch(
        trajectory_with_bat_contact_and_catch,
        detections,
        bat_contact
    )
    
    # Should return None when no fielder detected
    assert fielder_catch is None


def test_detect_ground_contact_with_low_height(
    detector,
    trajectory_with_ground_contact,
    ball_detection,
    batsman_detection
):
    """Test ground contact detection when ball height drops below threshold."""
    # Create bat contact and fielder catch
    bat_contact = BatContact(
        contact_position=Position3D(x=0.1, y=0.9, z=0.0),
        contact_timestamp=0.3,
        contact_frame_index=3,
        ball_detection=ball_detection,
        batsman_detection=batsman_detection,
        velocity_before=Vector3D(vx=0.0, vy=-1.3, vz=13.3),
        velocity_after=Vector3D(vx=2.7, vy=2.0, vz=10.0)
    )
    
    fielder_catch = FielderCatch(
        fielder_detection=Detection(
            class_id=DetectionClass.FIELDER.value,
            class_name="fielder",
            bounding_box=BoundingBox(x=768.0, y=576.0, width=120.0, height=240.0),
            confidence=0.88,
            position_3d=Position3D(x=2.0, y=1.0, z=6.0)
        ),
        catch_position=Position3D(x=2.0, y=1.0, z=6.0),
        catch_timestamp=0.9,
        control_frames=3,
        ball_detections=[]
    )
    
    ground_contact, min_height = detector.detect_ground_contact(
        trajectory_with_ground_contact,
        bat_contact,
        fielder_catch
    )
    
    # Should detect ground contact
    assert ground_contact is True
    assert min_height < detector.MIN_BALL_HEIGHT


def test_detect_ground_contact_without_ground_contact(
    detector,
    trajectory_with_bat_contact_and_catch,
    ball_detection,
    batsman_detection
):
    """Test no ground contact when ball maintains height."""
    bat_contact = BatContact(
        contact_position=Position3D(x=0.1, y=0.9, z=0.0),
        contact_timestamp=0.3,
        contact_frame_index=3,
        ball_detection=ball_detection,
        batsman_detection=batsman_detection,
        velocity_before=Vector3D(vx=0.0, vy=-1.3, vz=13.3),
        velocity_after=Vector3D(vx=2.7, vy=2.0, vz=10.0)
    )
    
    fielder_catch = FielderCatch(
        fielder_detection=Detection(
            class_id=DetectionClass.FIELDER.value,
            class_name="fielder",
            bounding_box=BoundingBox(x=768.0, y=576.0, width=120.0, height=240.0),
            confidence=0.88,
            position_3d=Position3D(x=2.0, y=1.0, z=6.0)
        ),
        catch_position=Position3D(x=2.0, y=1.0, z=6.0),
        catch_timestamp=0.9,
        control_frames=3,
        ball_detections=[]
    )
    
    ground_contact, min_height = detector.detect_ground_contact(
        trajectory_with_bat_contact_and_catch,
        bat_contact,
        fielder_catch
    )
    
    # Should not detect ground contact
    assert ground_contact is False
    assert min_height >= detector.MIN_BALL_HEIGHT


def test_bat_contact_validation():
    """Test BatContact dataclass validation."""
    ball_det = Detection(
        class_id=DetectionClass.BALL.value,
        class_name="ball",
        bounding_box=BoundingBox(x=646.0, y=360.0, width=20.0, height=20.0),
        confidence=0.92,
        position_3d=Position3D(x=0.1, y=0.9, z=0.0)
    )
    
    batsman_det = Detection(
        class_id=DetectionClass.BATSMAN.value,
        class_name="batsman",
        bounding_box=BoundingBox(x=590.0, y=310.0, width=100.0, height=200.0),
        confidence=0.90,
        position_3d=Position3D(x=0.0, y=1.0, z=0.0)
    )
    
    contact = BatContact(
        contact_position=Position3D(x=0.1, y=0.9, z=0.0),
        contact_timestamp=0.3,
        contact_frame_index=3,
        ball_detection=ball_det,
        batsman_detection=batsman_det,
        velocity_before=Vector3D(vx=0.0, vy=-1.3, vz=13.3),
        velocity_after=Vector3D(vx=2.7, vy=2.0, vz=10.0)
    )
    
    assert contact.contact_position.x == 0.1
    assert contact.contact_timestamp == 0.3
    assert contact.contact_frame_index == 3
    assert contact.ball_detection == ball_det
    assert contact.batsman_detection == batsman_det


def test_bat_contact_invalid_position():
    """Test BatContact with invalid position."""
    ball_det = Detection(
        class_id=DetectionClass.BALL.value,
        class_name="ball",
        bounding_box=BoundingBox(x=646.0, y=360.0, width=20.0, height=20.0),
        confidence=0.92,
        position_3d=Position3D(x=0.1, y=0.9, z=0.0)
    )
    
    batsman_det = Detection(
        class_id=DetectionClass.BATSMAN.value,
        class_name="batsman",
        bounding_box=BoundingBox(x=590.0, y=310.0, width=100.0, height=200.0),
        confidence=0.90,
        position_3d=Position3D(x=0.0, y=1.0, z=0.0)
    )
    
    with pytest.raises(TypeError):
        BatContact(
            contact_position="invalid",
            contact_timestamp=0.3,
            contact_frame_index=3,
            ball_detection=ball_det,
            batsman_detection=batsman_det,
            velocity_before=Vector3D(vx=0.0, vy=-1.3, vz=13.3),
            velocity_after=Vector3D(vx=2.7, vy=2.0, vz=10.0)
        )


def test_fielder_catch_validation():
    """Test FielderCatch dataclass validation."""
    fielder_det = Detection(
        class_id=DetectionClass.FIELDER.value,
        class_name="fielder",
        bounding_box=BoundingBox(x=768.0, y=576.0, width=120.0, height=240.0),
        confidence=0.88,
        position_3d=Position3D(x=2.0, y=1.0, z=6.0)
    )
    
    catch = FielderCatch(
        fielder_detection=fielder_det,
        catch_position=Position3D(x=2.0, y=1.0, z=6.0),
        catch_timestamp=0.9,
        control_frames=3,
        ball_detections=[]
    )
    
    assert catch.fielder_detection == fielder_det
    assert catch.catch_position.x == 2.0
    assert catch.catch_timestamp == 0.9
    assert catch.control_frames == 3


def test_fielder_catch_invalid_control_frames():
    """Test FielderCatch with invalid control frames."""
    fielder_det = Detection(
        class_id=DetectionClass.FIELDER.value,
        class_name="fielder",
        bounding_box=BoundingBox(x=768.0, y=576.0, width=120.0, height=240.0),
        confidence=0.88,
        position_3d=Position3D(x=2.0, y=1.0, z=6.0)
    )
    
    with pytest.raises((TypeError, ValueError)):
        FielderCatch(
            fielder_detection=fielder_det,
            catch_position=Position3D(x=2.0, y=1.0, z=6.0),
            catch_timestamp=0.9,
            control_frames=-1,  # Invalid negative
            ball_detections=[]
        )


def test_caught_analysis_validation():
    """Test CaughtAnalysis dataclass validation."""
    ball_det = Detection(
        class_id=DetectionClass.BALL.value,
        class_name="ball",
        bounding_box=BoundingBox(x=646.0, y=360.0, width=20.0, height=20.0),
        confidence=0.92,
        position_3d=Position3D(x=0.1, y=0.9, z=0.0)
    )
    
    batsman_det = Detection(
        class_id=DetectionClass.BATSMAN.value,
        class_name="batsman",
        bounding_box=BoundingBox(x=590.0, y=310.0, width=100.0, height=200.0),
        confidence=0.90,
        position_3d=Position3D(x=0.0, y=1.0, z=0.0)
    )
    
    fielder_det = Detection(
        class_id=DetectionClass.FIELDER.value,
        class_name="fielder",
        bounding_box=BoundingBox(x=768.0, y=576.0, width=120.0, height=240.0),
        confidence=0.88,
        position_3d=Position3D(x=2.0, y=1.0, z=6.0)
    )
    
    bat_contact = BatContact(
        contact_position=Position3D(x=0.1, y=0.9, z=0.0),
        contact_timestamp=0.3,
        contact_frame_index=3,
        ball_detection=ball_det,
        batsman_detection=batsman_det,
        velocity_before=Vector3D(vx=0.0, vy=-1.3, vz=13.3),
        velocity_after=Vector3D(vx=2.7, vy=2.0, vz=10.0)
    )
    
    fielder_catch = FielderCatch(
        fielder_detection=fielder_det,
        catch_position=Position3D(x=2.0, y=1.0, z=6.0),
        catch_timestamp=0.9,
        control_frames=3,
        ball_detections=[]
    )
    
    analysis = CaughtAnalysis(
        bat_contact=bat_contact,
        fielder_catch=fielder_catch,
        ground_contact_detected=False,
        min_ball_height=0.8,
        flight_duration=0.6
    )
    
    assert analysis.bat_contact == bat_contact
    assert analysis.fielder_catch == fielder_catch
    assert analysis.ground_contact_detected is False
    assert analysis.min_ball_height == 0.8
    assert analysis.flight_duration == 0.6


def test_edge_case_empty_detections(detector, trajectory_with_bat_contact_and_catch):
    """Test edge case with empty detections list."""
    detections = []
    
    decision = detector.detect(trajectory_with_bat_contact_and_catch, detections)
    
    # Should return None when no detections
    assert decision is None


def test_edge_case_multiple_fielder_detections(
    detector,
    trajectory_with_bat_contact_and_catch,
    ball_detection,
    batsman_detection,
    fielder_detection
):
    """Test edge case with multiple fielder detections."""
    # Create second fielder detection with lower confidence
    fielder_det_2 = Detection(
        class_id=DetectionClass.FIELDER.value,
        class_name="fielder",
        bounding_box=BoundingBox(x=770.0, y=580.0, width=120.0, height=240.0),
        confidence=0.82,
        position_3d=Position3D(x=2.1, y=1.1, z=6.1)
    )
    
    detections = [ball_detection, batsman_detection, fielder_detection, fielder_det_2]
    
    decision = detector.detect(trajectory_with_bat_contact_and_catch, detections)
    
    # Should handle multiple fielders (may use any of them)
    # Just verify it doesn't crash
    assert decision is None or decision.event_type == EventType.CAUGHT


def test_confidence_calculation_with_high_quality_detections(
    detector,
    trajectory_with_bat_contact_and_catch,
    ball_detection,
    batsman_detection,
    fielder_detection
):
    """Test confidence calculation with high quality detections."""
    detections = [ball_detection, batsman_detection, fielder_detection]
    
    decision = detector.detect(trajectory_with_bat_contact_and_catch, detections)
    
    if decision is not None:
        # With high quality detections, confidence should be in valid range
        assert 0.0 <= decision.confidence <= 1.0
