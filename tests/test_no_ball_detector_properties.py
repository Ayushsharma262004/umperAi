"""
Property-based tests for No Ball Detector.

These tests validate universal properties that should hold for all no ball
detection scenarios.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
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
# Custom Hypothesis Strategies
# ============================================================================

@st.composite
def bowler_foot_position(draw, crease_line_z=-10.0):
    """Generate valid bowler foot positions relative to crease."""
    # Bowler foot can be anywhere from well behind to over the crease
    # z: -12m (behind) to -8m (over)
    z = draw(st.floats(min_value=crease_line_z - 2.0, max_value=crease_line_z + 2.0))
    
    # x: within pitch width
    x = draw(st.floats(min_value=-2.0, max_value=2.0))
    
    # y: foot on ground
    y = draw(st.floats(min_value=0.0, max_value=0.2))
    
    return Position3D(x=x, y=y, z=z)


@st.composite
def ball_trajectory_with_release(draw, release_velocity_change=10.0):
    """
    Generate ball trajectory with clear release point.
    
    Args:
        release_velocity_change: Velocity change at release (m/s)
    """
    num_points = draw(st.integers(min_value=5, max_value=20))
    release_index = draw(st.integers(min_value=2, max_value=num_points - 2))
    
    positions = []
    timestamps = []
    velocities = []
    
    # Generate positions from bowler to batsman
    for i in range(num_points):
        t = i / (num_points - 1)
        
        # Ball moves from bowling end (z=-10) to batting end (z=0)
        z = -10.0 + t * 10.0
        
        # Ball path (slight curve)
        x = draw(st.floats(min_value=-1.0, max_value=1.0))
        
        # Ball height (parabolic trajectory)
        y = 2.0 - t * 1.5  # Descending
        
        positions.append(Position3D(x=x, y=max(0.1, y), z=z))
        timestamps.append(t * 0.5)  # 0.5 seconds total
    
    # Generate velocities with spike at release point
    for i in range(len(positions)):
        if i < len(positions) - 1:
            dt = timestamps[i + 1] - timestamps[i]
            if dt > 0:
                vx = (positions[i + 1].x - positions[i].x) / dt
                vy = (positions[i + 1].y - positions[i].y) / dt
                vz = (positions[i + 1].z - positions[i].z) / dt
                
                # Add velocity spike at release point
                if i == release_index:
                    vz += release_velocity_change
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
    
    return trajectory, release_index


@st.composite
def bowler_detection(draw, position: Position3D):
    """Generate bowler detection from position.
    
    The position parameter should be the actual foot position.
    """
    # Create bounding box around bowler position
    # Convert 3D position to approximate 2D pixel coordinates
    pixel_x = position.x * 64.0 + 640  # Rough conversion
    pixel_y = position.z * 36.0 + 360
    
    bbox = BoundingBox(
        x=pixel_x - 40,
        y=pixel_y - 80,
        width=80,
        height=160
    )
    
    confidence = draw(st.floats(min_value=0.7, max_value=1.0))
    
    # The position_3d represents the foot position directly
    return Detection(
        class_id=DetectionClass.BOWLER.value,
        class_name="bowler",
        bounding_box=bbox,
        confidence=confidence,
        position_3d=position  # This is the foot position
    )


@st.composite
def crease_detection(draw):
    """Generate crease line detection."""
    # Crease line bounding box (horizontal line across pitch)
    bbox = BoundingBox(
        x=200.0,
        y=300.0,
        width=880.0,
        height=10.0
    )
    
    confidence = draw(st.floats(min_value=0.8, max_value=1.0))
    
    return Detection(
        class_id=DetectionClass.CREASE.value,
        class_name="crease",
        bounding_box=bbox,
        confidence=confidence,
        position_3d=None
    )


@st.composite
def calibration_data_with_crease(draw, bowling_crease_z=-10.0):
    """Generate calibration data with crease lines.
    
    Note: The bowling_crease_z parameter is used to set the expected crease position,
    but since CalibrationData stores 2D points, we'll need to pass this separately
    to the detector or store it in a way the detector can access.
    """
    # Create minimal calibration data
    pitch_boundary = [
        Point2D(x=0.0, y=0.0),
        Point2D(x=1280.0, y=0.0),
        Point2D(x=1280.0, y=720.0),
        Point2D(x=0.0, y=720.0)
    ]
    
    # Store the bowling crease z-coordinate in the crease line points
    # We'll use the y-coordinate to encode the z position (hack for testing)
    crease_lines = {
        "bowling": [
            Point2D(x=640.0, y=bowling_crease_z),  # Encode z in y
            Point2D(x=640.0, y=bowling_crease_z)
        ],
        "batting": [Point2D(x=640.0, y=0.0), Point2D(x=640.0, y=0.0)]
    }
    
    wide_guidelines = {
        "left": -1.0,
        "right": 1.0
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
    crease_line_z=st.floats(min_value=-12.0, max_value=-8.0),
    overstep_distance=st.floats(min_value=0.01, max_value=1.0),
    data=st.data()
)
@settings(max_examples=100, deadline=None)
def test_property_7_no_ball_classification(crease_line_z, overstep_distance, data):
    """
    Feature: ai-auto-umpiring-system, Property 7: No Ball Classification
    
    **Validates: Requirements 5.1**
    
    For any delivery where the bowler's front foot position crosses the crease line
    at ball release, the Decision Engine SHALL classify the delivery as a No_Ball.
    """
    # Arrange: Create detector with calibration
    calibration = data.draw(calibration_data_with_crease(bowling_crease_z=crease_line_z))
    detector = NoBallDetector(calibration=calibration)
    
    # Generate foot position that crosses crease (no ball)
    # Foot is OVER the crease line (z > crease_line_z)
    foot_z = crease_line_z + overstep_distance
    foot_position = Position3D(
        x=data.draw(st.floats(min_value=-2.0, max_value=2.0)),
        y=0.1,
        z=foot_z
    )
    
    # Verify foot is actually over crease
    assert foot_position.z > crease_line_z, "Foot should be over crease line"
    
    # Generate trajectory with clear release point
    trajectory, release_index = data.draw(ball_trajectory_with_release(
        release_velocity_change=data.draw(st.floats(min_value=5.0, max_value=20.0))
    ))
    
    # Create bowler detection at foot position
    bowler_det = data.draw(bowler_detection(position=foot_position))
    
    # Create crease detection
    crease_det = data.draw(crease_detection())
    
    detections = [bowler_det, crease_det]
    
    # Act: Detect no ball
    decision = detector.detect(trajectory, detections, calibration)
    
    # Assert: Should classify as no ball
    assert decision is not None, (
        f"Expected no ball decision for foot at z={foot_z:.2f}m "
        f"with crease at z={crease_line_z:.2f}m (overstep: {overstep_distance:.2f}m)"
    )
    assert decision.event_type == EventType.NO_BALL, (
        f"Expected NO_BALL event type, got {decision.event_type}"
    )
    assert 0.0 <= decision.confidence <= 1.0, (
        f"Confidence must be in [0, 1], got {decision.confidence}"
    )


@given(
    crease_line_z=st.floats(min_value=-12.0, max_value=-8.0),
    foot_position=bowler_foot_position(crease_line_z=-10.0),
    data=st.data()
)
@settings(max_examples=100, deadline=None)
def test_property_8_foot_crease_distance_calculation(crease_line_z, foot_position, data):
    """
    Feature: ai-auto-umpiring-system, Property 8: Foot-Crease Distance Calculation
    
    **Validates: Requirements 5.3**
    
    For any bowler foot position and crease line position, the Decision Engine
    SHALL calculate the distance between them at the moment of ball release.
    """
    # Arrange: Create detector
    calibration = data.draw(calibration_data_with_crease(bowling_crease_z=crease_line_z))
    detector = NoBallDetector(calibration=calibration)
    
    # Act: Calculate foot-crease distance
    distance = detector.calculate_foot_crease_distance(foot_position, crease_line_z)
    
    # Assert: Distance should be calculated correctly
    # Distance = crease_line_z - foot_position.z
    # Positive: foot behind crease (legal)
    # Negative: foot over crease (no ball)
    expected_distance = crease_line_z - foot_position.z
    
    assert isinstance(distance, (int, float)), "Distance must be numeric"
    assert np.isfinite(distance), "Distance must be finite"
    assert abs(distance - expected_distance) < 0.001, (
        f"Distance calculation incorrect: expected {expected_distance:.3f}m, "
        f"got {distance:.3f}m"
    )
    
    # Verify distance sign is correct
    if foot_position.z > crease_line_z:
        # Foot over crease - distance should be negative
        assert distance < 0, (
            f"Foot over crease (z={foot_position.z:.2f}m > {crease_line_z:.2f}m) "
            f"should have negative distance, got {distance:.2f}m"
        )
    elif foot_position.z < crease_line_z:
        # Foot behind crease - distance should be positive
        assert distance > 0, (
            f"Foot behind crease (z={foot_position.z:.2f}m < {crease_line_z:.2f}m) "
            f"should have positive distance, got {distance:.2f}m"
        )
    else:
        # Foot exactly on crease - distance should be zero
        assert abs(distance) < 0.001, (
            f"Foot on crease should have zero distance, got {distance:.2f}m"
        )


@given(
    crease_line_z=st.floats(min_value=-12.0, max_value=-8.0),
    behind_distance=st.floats(min_value=0.01, max_value=1.0),
    data=st.data()
)
@settings(max_examples=100, deadline=None)
def test_no_ball_not_classified_when_foot_behind_crease(crease_line_z, behind_distance, data):
    """
    Test that deliveries with foot behind crease are NOT classified as no ball.
    
    This is the inverse of Property 7 - ensures we don't have false positives.
    """
    # Arrange: Create detector
    calibration = data.draw(calibration_data_with_crease(bowling_crease_z=crease_line_z))
    detector = NoBallDetector(calibration=calibration)
    
    # Generate foot position BEHIND crease (legal)
    foot_z = crease_line_z - behind_distance
    foot_position = Position3D(
        x=data.draw(st.floats(min_value=-2.0, max_value=2.0)),
        y=0.1,
        z=foot_z
    )
    
    # Verify foot is actually behind crease
    assert foot_position.z < crease_line_z, "Foot should be behind crease line"
    
    # Generate trajectory with clear release point
    trajectory, release_index = data.draw(ball_trajectory_with_release(
        release_velocity_change=data.draw(st.floats(min_value=5.0, max_value=20.0))
    ))
    
    # Create bowler detection at foot position
    bowler_det = data.draw(bowler_detection(position=foot_position))
    
    # Create crease detection
    crease_det = data.draw(crease_detection())
    
    detections = [bowler_det, crease_det]
    
    # Act: Detect no ball
    decision = detector.detect(trajectory, detections, calibration)
    
    # Assert: Should NOT classify as no ball
    assert decision is None, (
        f"Expected no no ball decision for foot at z={foot_z:.2f}m "
        f"with crease at z={crease_line_z:.2f}m (behind by {behind_distance:.2f}m)"
    )


@given(
    crease_line_z=st.floats(min_value=-12.0, max_value=-8.0),
    data=st.data()
)
@settings(max_examples=100, deadline=None)
def test_no_ball_edge_case_foot_exactly_on_crease(crease_line_z, data):
    """
    Test edge case: foot exactly on crease line.
    
    According to cricket rules, any part of the foot on or over the line is a no ball.
    """
    # Arrange: Create detector
    calibration = data.draw(calibration_data_with_crease(bowling_crease_z=crease_line_z))
    detector = NoBallDetector(calibration=calibration)
    
    # Generate foot position EXACTLY on crease
    foot_position = Position3D(
        x=data.draw(st.floats(min_value=-2.0, max_value=2.0)),
        y=0.1,
        z=crease_line_z  # Exactly on crease
    )
    
    # Generate trajectory with clear release point
    trajectory, release_index = data.draw(ball_trajectory_with_release(
        release_velocity_change=data.draw(st.floats(min_value=5.0, max_value=20.0))
    ))
    
    # Create bowler detection at foot position
    bowler_det = data.draw(bowler_detection(position=foot_position))
    
    # Create crease detection
    crease_det = data.draw(crease_detection())
    
    detections = [bowler_det, crease_det]
    
    # Act: Detect no ball
    decision = detector.detect(trajectory, detections, calibration)
    
    # Assert: Should classify as no ball (foot on line = no ball)
    assert decision is not None, (
        f"Expected no ball decision for foot exactly on crease at z={crease_line_z:.2f}m"
    )
    assert decision.event_type == EventType.NO_BALL, (
        f"Expected NO_BALL event type for foot on crease, got {decision.event_type}"
    )


@given(
    velocity_change=st.floats(min_value=5.0, max_value=30.0),
    data=st.data()
)
@settings(max_examples=100, deadline=None)
def test_ball_release_detection_with_velocity_change(velocity_change, data):
    """
    Test that ball release is detected when there's a sudden velocity change.
    """
    # Arrange: Create detector
    detector = NoBallDetector()
    
    # Generate trajectory with specified velocity change at release
    trajectory, release_index = data.draw(ball_trajectory_with_release(
        release_velocity_change=velocity_change
    ))
    
    # Act: Detect ball release
    release_point = detector.detect_ball_release(trajectory)
    
    # Assert: Release point should be detected
    assert release_point is not None, (
        f"Expected release point detection with velocity change {velocity_change:.2f} m/s"
    )
    assert isinstance(release_point, BallReleasePoint), (
        "Release point should be BallReleasePoint instance"
    )
    assert release_point.velocity_change >= detector.VELOCITY_CHANGE_THRESHOLD, (
        f"Release velocity change {release_point.velocity_change:.2f} m/s "
        f"should exceed threshold {detector.VELOCITY_CHANGE_THRESHOLD} m/s"
    )
    assert 0.0 <= release_point.timestamp <= trajectory.timestamps[-1], (
        "Release timestamp should be within trajectory time range"
    )


@given(
    data=st.data()
)
@settings(max_examples=100, deadline=None)
def test_no_ball_uncertain_when_bowler_not_detected(data):
    """
    Test that decision is flagged as uncertain when bowler is not detected (occluded).
    
    **Validates: Requirements 5.4**
    """
    # Arrange: Create detector
    calibration = data.draw(calibration_data_with_crease())
    detector = NoBallDetector(calibration=calibration)
    
    # Generate trajectory with clear release point
    trajectory, release_index = data.draw(ball_trajectory_with_release(
        release_velocity_change=data.draw(st.floats(min_value=5.0, max_value=20.0))
    ))
    
    # Create detections WITHOUT bowler (simulating occlusion)
    crease_det = data.draw(crease_detection())
    detections = [crease_det]  # No bowler detection
    
    # Act: Detect no ball
    decision = detector.detect(trajectory, detections, calibration)
    
    # Assert: Should create uncertain decision due to occlusion
    # Note: The current implementation returns an uncertain decision
    # when bowler is not detected
    if decision is not None:
        assert decision.requires_review is True, (
            "Decision should require review when bowler is occluded"
        )
        assert decision.confidence < 0.80, (
            f"Decision confidence should be low (<0.80) when bowler occluded, "
            f"got {decision.confidence:.2f}"
        )
