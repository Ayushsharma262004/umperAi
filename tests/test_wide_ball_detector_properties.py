"""
Property-based tests for Wide Ball Detector.

These tests validate universal properties that should hold for all wide ball
detection scenarios.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
import numpy as np

from umpirai.decision.wide_ball_detector import WideBallDetector, WideGuidelines
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
# Custom Hypothesis Strategies
# ============================================================================

@st.composite
def batsman_stance_position(draw):
    """Generate valid batsman stance positions."""
    # Batsman typically stands near batting crease (z=0)
    # and within pitch width (x: -2m to 2m)
    x = draw(st.floats(min_value=-2.0, max_value=2.0))
    y = draw(st.floats(min_value=0.5, max_value=2.0))  # Standing height
    z = draw(st.floats(min_value=-0.5, max_value=0.5))  # Near crease
    
    return Position3D(x=x, y=y, z=z)


@st.composite
def ball_trajectory_crossing_crease(draw, batsman_x=0.0, wide_offset=1.0):
    """
    Generate ball trajectory that crosses batsman's crease.
    
    Args:
        batsman_x: Batsman x-coordinate
        wide_offset: Wide guideline offset from batsman
    """
    # Generate ball x-position at crease
    # Can be anywhere from -5m to 5m (well outside to well inside)
    ball_x_at_crease = draw(st.floats(min_value=-5.0, max_value=5.0))
    
    # Generate trajectory with at least 2 points crossing crease
    num_points = draw(st.integers(min_value=2, max_value=20))
    
    positions = []
    timestamps = []
    velocities = []
    
    # Start position (before crease, z < 0)
    start_z = draw(st.floats(min_value=-10.0, max_value=-0.5))
    start_x = ball_x_at_crease + draw(st.floats(min_value=-0.5, max_value=0.5))
    start_y = draw(st.floats(min_value=0.5, max_value=2.0))
    
    positions.append(Position3D(x=start_x, y=start_y, z=start_z))
    timestamps.append(0.0)
    
    # Generate points crossing crease
    for i in range(1, num_points):
        t = i / (num_points - 1)
        
        # Interpolate z from start to past crease
        z = start_z + t * (abs(start_z) + 2.0)
        
        # Interpolate x towards ball_x_at_crease
        x = start_x + t * (ball_x_at_crease - start_x)
        
        # Ball height decreases slightly
        y = start_y - t * 0.5
        
        positions.append(Position3D(x=x, y=max(0.1, y), z=z))
        timestamps.append(t * 0.5)  # 0.5 seconds total
    
    # Generate velocities (simplified)
    for i in range(len(positions)):
        if i < len(positions) - 1:
            dt = timestamps[i + 1] - timestamps[i]
            if dt > 0:
                vx = (positions[i + 1].x - positions[i].x) / dt
                vy = (positions[i + 1].y - positions[i].y) / dt
                vz = (positions[i + 1].z - positions[i].z) / dt
            else:
                vx = vy = vz = 0.0
        else:
            vx = vy = vz = 0.0
        
        velocities.append(Vector3D(vx=vx, vy=vy, vz=vz))
    
    # Calculate speed metrics
    speeds = [v.magnitude() for v in velocities]
    speed_max = max(speeds) if speeds else 0.0
    speed_avg = sum(speeds) / len(speeds) if speeds else 0.0
    
    trajectory = Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=positions[0],
        end_position=positions[-1] if positions else None,
        speed_max=speed_max,
        speed_avg=speed_avg
    )
    
    return trajectory, ball_x_at_crease


@st.composite
def batsman_detection(draw, position: Position3D):
    """Generate batsman detection from position."""
    # Create bounding box around batsman position
    # Convert 3D position to approximate 2D pixel coordinates
    pixel_x = position.x * 64.0 + 640  # Rough conversion
    pixel_y = position.z * 36.0 + 360
    
    bbox = BoundingBox(
        x=pixel_x - 50,
        y=pixel_y - 100,
        width=100,
        height=200
    )
    
    confidence = draw(st.floats(min_value=0.7, max_value=1.0))
    
    return Detection(
        class_id=DetectionClass.BATSMAN.value,
        class_name="batsman",
        bounding_box=bbox,
        confidence=confidence,
        position_3d=position
    )


@st.composite
def calibration_data_with_guidelines(draw, wide_offset=1.0):
    """Generate calibration data with wide guidelines."""
    # Create minimal calibration data
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
        "left": -wide_offset,
        "right": wide_offset
    }
    
    stump_positions = {
        "bowling": Point2D(x=640.0, y=200.0),
        "batting": Point2D(x=640.0, y=600.0)
    }
    
    # Create dummy camera calibration
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


# ============================================================================
# Property Tests
# ============================================================================

@given(
    batsman_pos=batsman_stance_position(),
    wide_offset=st.floats(min_value=0.5, max_value=2.0),
    data=st.data()
)
@settings(max_examples=100, deadline=None)
def test_property_5_wide_ball_classification(batsman_pos, wide_offset, data):
    """
    Feature: ai-auto-umpiring-system, Property 5: Wide Ball Classification
    
    **Validates: Requirements 4.1, 4.3**
    
    For any delivery trajectory that crosses the wide guideline boundary
    (defined relative to batsman stance), the Decision Engine SHALL classify
    the delivery as a Wide_Ball.
    """
    # Arrange: Create detector with calibration
    calibration = data.draw(calibration_data_with_guidelines(wide_offset=wide_offset))
    detector = WideBallDetector(calibration=calibration)
    
    # Set batsman stance
    detector.set_batsman_stance(batsman_pos)
    
    # Get wide guidelines
    guidelines = detector.get_wide_guidelines()
    assert guidelines is not None, "Guidelines should be initialized"
    left_guideline, right_guideline = guidelines
    
    # Generate trajectory that crosses OUTSIDE guidelines (wide ball)
    # Choose ball position outside guidelines
    if batsman_pos.x < 0:
        # Batsman on left, make ball go far right
        ball_x_at_crease = right_guideline + abs(wide_offset) * 0.5
    else:
        # Batsman on right, make ball go far left
        ball_x_at_crease = left_guideline - abs(wide_offset) * 0.5
    
    # Ensure ball is actually outside guidelines
    assume(ball_x_at_crease < left_guideline or ball_x_at_crease > right_guideline)
    
    trajectory, _ = data.draw(ball_trajectory_crossing_crease(
        batsman_x=batsman_pos.x,
        wide_offset=wide_offset
    ))
    
    # Manually set trajectory to cross at our chosen x position
    # We need to ensure the ball crosses the crease (z=0) at ball_x_at_crease
    # Create a simple 2-point trajectory that definitely crosses at the right position
    trajectory = Trajectory(
        positions=[
            Position3D(x=ball_x_at_crease, y=1.0, z=-1.0),  # Before crease
            Position3D(x=ball_x_at_crease, y=0.5, z=1.0),   # After crease
        ],
        timestamps=[0.0, 0.1],
        velocities=[
            Vector3D(vx=0.0, vy=-5.0, vz=20.0),
            Vector3D(vx=0.0, vy=0.0, vz=0.0),
        ],
        start_position=Position3D(x=ball_x_at_crease, y=1.0, z=-1.0),
        end_position=Position3D(x=ball_x_at_crease, y=0.5, z=1.0),
        speed_max=20.0,
        speed_avg=10.0
    )
    
    # Create batsman detection
    batsman_det = data.draw(batsman_detection(position=batsman_pos))
    detections = [batsman_det]
    
    # Act: Detect wide ball
    decision = detector.detect(trajectory, detections, calibration)
    
    # Assert: Should classify as wide ball
    assert decision is not None, (
        f"Expected wide ball decision for ball at x={ball_x_at_crease:.2f}m "
        f"with guidelines [{left_guideline:.2f}m, {right_guideline:.2f}m]"
    )
    assert decision.event_type == EventType.WIDE, (
        f"Expected WIDE event type, got {decision.event_type}"
    )
    assert 0.0 <= decision.confidence <= 1.0, (
        f"Confidence must be in [0, 1], got {decision.confidence}"
    )


@given(
    initial_stance=batsman_stance_position(),
    movement_distance=st.floats(min_value=0.6, max_value=2.0),  # > 0.5m threshold
    wide_offset=st.floats(min_value=0.5, max_value=2.0),
    data=st.data()
)
@settings(max_examples=100, deadline=None)
def test_property_6_wide_guideline_adaptation(initial_stance, movement_distance, wide_offset, data):
    """
    Feature: ai-auto-umpiring-system, Property 6: Wide Guideline Adaptation
    
    **Validates: Requirements 4.4**
    
    For any batsman movement exceeding 0.5 meters from original stance position,
    the Decision Engine SHALL adjust the wide guideline positions accordingly.
    """
    # Arrange: Create detector
    calibration = data.draw(calibration_data_with_guidelines(wide_offset=wide_offset))
    detector = WideBallDetector(calibration=calibration)
    
    # Set initial batsman stance
    detector.set_batsman_stance(initial_stance)
    
    # Get initial guidelines
    initial_guidelines = detector.get_wide_guidelines()
    assert initial_guidelines is not None
    initial_left, initial_right = initial_guidelines
    
    # Calculate new stance position (moved by movement_distance)
    # Move in x direction
    new_stance = Position3D(
        x=initial_stance.x + movement_distance,
        y=initial_stance.y,
        z=initial_stance.z
    )
    
    # Act: Update batsman stance with significant movement
    detector.set_batsman_stance(new_stance)
    
    # Get updated guidelines
    updated_guidelines = detector.get_wide_guidelines()
    assert updated_guidelines is not None
    updated_left, updated_right = updated_guidelines
    
    # Assert: Guidelines should have adapted (moved with batsman)
    # The guidelines should have shifted by approximately the movement distance
    left_shift = updated_left - initial_left
    right_shift = updated_right - initial_right
    
    # Guidelines should shift in the same direction as batsman movement
    assert abs(left_shift - movement_distance) < 0.1, (
        f"Left guideline should shift by ~{movement_distance:.2f}m, "
        f"but shifted by {left_shift:.2f}m"
    )
    assert abs(right_shift - movement_distance) < 0.1, (
        f"Right guideline should shift by ~{movement_distance:.2f}m, "
        f"but shifted by {right_shift:.2f}m"
    )
    
    # Guidelines should maintain their relative offset from batsman center
    guideline_width = updated_right - updated_left
    expected_width = 2 * wide_offset
    assert abs(guideline_width - expected_width) < 0.1, (
        f"Guideline width should remain ~{expected_width:.2f}m, "
        f"but is {guideline_width:.2f}m"
    )


@given(
    batsman_pos=batsman_stance_position(),
    wide_offset=st.floats(min_value=0.5, max_value=2.0),
    data=st.data()
)
@settings(max_examples=100, deadline=None)
def test_wide_ball_not_classified_when_inside_guidelines(batsman_pos, wide_offset, data):
    """
    Test that balls inside guidelines are NOT classified as wide.
    
    This is the inverse of Property 5 - ensures we don't have false positives.
    """
    # Arrange: Create detector
    calibration = data.draw(calibration_data_with_guidelines(wide_offset=wide_offset))
    detector = WideBallDetector(calibration=calibration)
    
    # Set batsman stance
    detector.set_batsman_stance(batsman_pos)
    
    # Get wide guidelines
    guidelines = detector.get_wide_guidelines()
    assert guidelines is not None
    left_guideline, right_guideline = guidelines
    
    # Generate trajectory that crosses INSIDE guidelines (not wide)
    # Choose ball position inside guidelines
    ball_x_at_crease = (left_guideline + right_guideline) / 2.0  # Center
    
    # Ensure ball is actually inside guidelines
    assume(left_guideline < ball_x_at_crease < right_guideline)
    
    trajectory, _ = data.draw(ball_trajectory_crossing_crease(
        batsman_x=batsman_pos.x,
        wide_offset=wide_offset
    ))
    
    # Manually set trajectory to cross at our chosen x position (center of guidelines)
    # Create a simple 2-point trajectory that definitely crosses at the right position
    trajectory = Trajectory(
        positions=[
            Position3D(x=ball_x_at_crease, y=1.0, z=-1.0),  # Before crease
            Position3D(x=ball_x_at_crease, y=0.5, z=1.0),   # After crease
        ],
        timestamps=[0.0, 0.1],
        velocities=[
            Vector3D(vx=0.0, vy=-5.0, vz=20.0),
            Vector3D(vx=0.0, vy=0.0, vz=0.0),
        ],
        start_position=Position3D(x=ball_x_at_crease, y=1.0, z=-1.0),
        end_position=Position3D(x=ball_x_at_crease, y=0.5, z=1.0),
        speed_max=20.0,
        speed_avg=10.0
    )
    
    # Create batsman detection
    batsman_det = data.draw(batsman_detection(position=batsman_pos))
    detections = [batsman_det]
    
    # Act: Detect wide ball
    decision = detector.detect(trajectory, detections, calibration)
    
    # Assert: Should NOT classify as wide ball
    assert decision is None, (
        f"Expected no wide ball decision for ball at x={ball_x_at_crease:.2f}m "
        f"with guidelines [{left_guideline:.2f}m, {right_guideline:.2f}m]"
    )


@given(
    batsman_pos=batsman_stance_position(),
    small_movement=st.floats(min_value=0.0, max_value=0.4),  # < 0.5m threshold
    wide_offset=st.floats(min_value=0.5, max_value=2.0),
    data=st.data()
)
@settings(max_examples=100, deadline=None)
def test_wide_guideline_no_adaptation_for_small_movement(batsman_pos, small_movement, wide_offset, data):
    """
    Test that guidelines do NOT adapt for small batsman movements (<0.5m).
    
    This validates the threshold behavior of Property 6.
    """
    # Arrange: Create detector
    calibration = data.draw(calibration_data_with_guidelines(wide_offset=wide_offset))
    detector = WideBallDetector(calibration=calibration)
    
    # Set initial batsman stance
    detector.set_batsman_stance(batsman_pos)
    
    # Get initial guidelines
    initial_guidelines = detector.get_wide_guidelines()
    assert initial_guidelines is not None
    initial_left, initial_right = initial_guidelines
    
    # Calculate new stance position (small movement)
    new_stance = Position3D(
        x=batsman_pos.x + small_movement,
        y=batsman_pos.y,
        z=batsman_pos.z
    )
    
    # Act: Update batsman stance with small movement
    detector.set_batsman_stance(new_stance)
    
    # Get updated guidelines
    updated_guidelines = detector.get_wide_guidelines()
    assert updated_guidelines is not None
    updated_left, updated_right = updated_guidelines
    
    # Assert: Guidelines should NOT have changed significantly
    # (small movements below threshold should not trigger adaptation)
    assert abs(updated_left - initial_left) < 0.01, (
        f"Left guideline should not change for small movement, "
        f"but changed from {initial_left:.2f}m to {updated_left:.2f}m"
    )
    assert abs(updated_right - initial_right) < 0.01, (
        f"Right guideline should not change for small movement, "
        f"but changed from {initial_right:.2f}m to {updated_right:.2f}m"
    )
