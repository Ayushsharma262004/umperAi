#!/usr/bin/env python3
"""
Script to create LBW test files automatically.
"""

import os

print("Creating LBW test files...")
print("=" * 60)

# Property tests content
property_tests = '''"""
Property-based tests for LBW (Leg Before Wicket) Detector.

These tests validate universal properties that should hold for all LBW
detection scenarios.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
import numpy as np

from umpirai.decision.lbw_detector import LBWDetector, PadContact, LBWAnalysis
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
def ball_trajectory_with_pad_contact(draw):
    """Generate ball trajectory that includes pad contact."""
    num_points = draw(st.integers(min_value=5, max_value=20))
    
    positions = []
    timestamps = []
    velocities = []
    
    # Start position (bowler's end, z < 0)
    start_x = draw(st.floats(min_value=-1.0, max_value=1.0))
    start_y = draw(st.floats(min_value=1.0, max_value=2.5))
    start_z = draw(st.floats(min_value=-15.0, max_value=-10.0))
    
    # Pad contact position (near batting crease)
    contact_x = draw(st.floats(min_value=-0.5, max_value=0.5))
    contact_y = draw(st.floats(min_value=0.3, max_value=0.8))
    contact_z = draw(st.floats(min_value=-0.5, max_value=0.5))
    
    # Generate trajectory from start to contact
    for i in range(num_points):
        t = i / (num_points - 1)
        
        x = start_x + t * (contact_x - start_x)
        y = start_y + t * (contact_y - start_y)
        z = start_z + t * (contact_z - start_z)
        
        positions.append(Position3D(x=x, y=y, z=z))
        timestamps.append(t * 0.5)
    
    # Generate velocities
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
            if i > 0:
                dt = timestamps[i] - timestamps[i - 1]
                if dt > 0:
                    vx = (positions[i].x - positions[i - 1].x) / dt
                    vy = (positions[i].y - positions[i - 1].y) / dt
                    vz = (positions[i].z - positions[i - 1].z) / dt
                else:
                    vx = vy = vz = 0.0
            else:
                vx = vy = vz = 0.0
        
        velocities.append(Vector3D(vx=vx, vy=vy, vz=vz))
    
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
    
    return trajectory


@st.composite
def batsman_detection_at_crease(draw):
    """Generate batsman detection at batting crease."""
    x = draw(st.floats(min_value=-0.5, max_value=0.5))
    y = draw(st.floats(min_value=0.8, max_value=1.8))
    z = draw(st.floats(min_value=-0.5, max_value=0.5))
    
    position = Position3D(x=x, y=y, z=z)
    
    pixel_x = x * 64.0 + 640
    pixel_y = z * 36.0 + 360
    
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
def ball_detection_at_pad(draw, pad_contact_position: Position3D):
    """Generate ball detection at pad contact position."""
    pixel_x = pad_contact_position.x * 64.0 + 640
    pixel_y = pad_contact_position.z * 36.0 + 360
    
    bbox = BoundingBox(
        x=pixel_x - 10,
        y=pixel_y - 10,
        width=20,
        height=20
    )
    
    confidence = draw(st.floats(min_value=0.7, max_value=1.0))
    
    return Detection(
        class_id=DetectionClass.BALL.value,
        class_name="ball",
        bounding_box=bbox,
        confidence=confidence,
        position_3d=pad_contact_position
    )


@st.composite
def calibration_data_with_stumps(draw):
    """Generate calibration data with stump positions."""
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
    
    wide_guidelines = {"left": -1.0, "right": 1.0}
    
    stump_positions = {
        "bowling": Point2D(x=640.0, y=200.0),
        "batting": Point2D(x=0.0, y=0.0)
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


# ============================================================================
# Property Tests
# ============================================================================

@given(
    trajectory=ball_trajectory_with_pad_contact(),
    data=st.data()
)
@settings(max_examples=50, deadline=None)
def test_property_11_lbw_trajectory_projection(trajectory, data):
    """
    Feature: ai-auto-umpiring-system, Property 11: LBW Trajectory Projection
    
    **Validates: Requirements 7.1**
    
    For any ball trajectory that contacts the batsman's pad, the Decision Engine
    SHALL calculate the projected path to determine if the ball would have hit the stumps.
    """
    calibration = data.draw(calibration_data_with_stumps())
    detector = LBWDetector(calibration=calibration)
    
    pad_contact_position = trajectory.positions[-1]
    
    ball_det = data.draw(ball_detection_at_pad(pad_contact_position=pad_contact_position))
    batsman_det = data.draw(batsman_detection_at_crease())
    detections = [ball_det, batsman_det]
    
    pad_contact = detector.detect_ball_pad_contact(trajectory, detections)
    
    assume(pad_contact is not None)
    
    stump_position = detector._get_stump_position(calibration)
    
    projected_intersection = detector.project_trajectory_to_stumps(
        trajectory,
        pad_contact,
        stump_position
    )
    
    if projected_intersection is not None:
        assert isinstance(projected_intersection, Position3D)
        assert abs(projected_intersection.z - stump_position.z) < 0.01
        assert np.isfinite(projected_intersection.x)
        assert np.isfinite(projected_intersection.y)
        assert np.isfinite(projected_intersection.z)


@given(
    trajectory=ball_trajectory_with_pad_contact(),
    data=st.data()
)
@settings(max_examples=50, deadline=None)
def test_property_12_lbw_pitching_line_determination(trajectory, data):
    """
    Feature: ai-auto-umpiring-system, Property 12: LBW Pitching Line Determination
    
    **Validates: Requirements 7.2**
    """
    calibration = data.draw(calibration_data_with_stumps())
    detector = LBWDetector(calibration=calibration)
    
    stump_position = detector._get_stump_position(calibration)
    
    pitching_point = detector.determine_pitching_point(trajectory)
    
    assert isinstance(pitching_point, Position3D)
    
    pitched_in_line = detector.is_pitched_in_line(pitching_point, stump_position)
    
    assert isinstance(pitched_in_line, bool)
    
    lateral_distance = abs(pitching_point.x - stump_position.x)
    expected_in_line = lateral_distance <= detector.LINE_TOLERANCE
    
    assert pitched_in_line == expected_in_line


@given(
    trajectory=ball_trajectory_with_pad_contact(),
    data=st.data()
)
@settings(max_examples=50, deadline=None)
def test_property_13_lbw_impact_line_determination(trajectory, data):
    """
    Feature: ai-auto-umpiring-system, Property 13: LBW Impact Line Determination
    
    **Validates: Requirements 7.3**
    """
    calibration = data.draw(calibration_data_with_stumps())
    detector = LBWDetector(calibration=calibration)
    
    impact_point = trajectory.positions[-1]
    
    stump_position = detector._get_stump_position(calibration)
    
    impact_in_line = detector.is_impact_in_line(impact_point, stump_position)
    
    assert isinstance(impact_in_line, bool)
    
    lateral_distance = abs(impact_point.x - stump_position.x)
    expected_in_line = lateral_distance <= detector.LINE_TOLERANCE
    
    assert impact_in_line == expected_in_line


@given(
    trajectory=ball_trajectory_with_pad_contact(),
    data=st.data()
)
@settings(max_examples=50, deadline=None)
def test_property_14_lbw_decision_logic(trajectory, data):
    """
    Feature: ai-auto-umpiring-system, Property 14: LBW Decision Logic
    
    **Validates: Requirements 7.4**
    """
    calibration = data.draw(calibration_data_with_stumps())
    detector = LBWDetector(calibration=calibration)
    
    pad_contact_position = trajectory.positions[-1]
    
    ball_det = data.draw(ball_detection_at_pad(pad_contact_position=pad_contact_position))
    batsman_det = data.draw(batsman_detection_at_crease())
    detections = [ball_det, batsman_det]
    
    decision = detector.detect(trajectory, detections, calibration)
    
    if decision is not None:
        assert decision.event_type == EventType.LBW
        assert 0.0 <= decision.confidence <= 1.0
        assert isinstance(decision.reasoning, str)
        assert len(decision.reasoning) > 0
        
        if detector._last_analysis is not None:
            analysis = detector._last_analysis
            
            assert analysis.pitched_in_line
            assert analysis.impact_in_line
            assert analysis.would_hit_stumps
            assert not analysis.bat_first


@given(
    trajectory=ball_trajectory_with_pad_contact(),
    data=st.data()
)
@settings(max_examples=50, deadline=None)
def test_property_15_lbw_bat_first_exclusion(trajectory, data):
    """
    Feature: ai-auto-umpiring-system, Property 15: LBW Bat-First Exclusion
    
    **Validates: Requirements 7.6**
    """
    calibration = data.draw(calibration_data_with_stumps())
    detector = LBWDetector(calibration=calibration)
    
    if len(trajectory.velocities) >= 3:
        mid_index = len(trajectory.velocities) // 2
        
        original_vel = trajectory.velocities[mid_index]
        trajectory.velocities[mid_index] = Vector3D(
            vx=-original_vel.vx * 0.8,
            vy=-original_vel.vy * 0.8,
            vz=-original_vel.vz * 0.8
        )
    
    pad_contact_position = trajectory.positions[-1]
    
    ball_det = data.draw(ball_detection_at_pad(pad_contact_position=pad_contact_position))
    batsman_det = data.draw(batsman_detection_at_crease())
    detections = [ball_det, batsman_det]
    
    bat_first = detector._check_bat_first_contact(trajectory, detections)
    
    if bat_first:
        decision = detector.detect(trajectory, detections, calibration)
        
        assert decision is None
'''

# Write property tests
with open("tests/test_lbw_detector_properties.py", "w", encoding="utf-8") as f:
    f.write(property_tests)

print("✓ Created tests/test_lbw_detector_properties.py")
print("\nDone! Files created successfully.")
print("\nVerify with:")
print("  python -m py_compile tests/test_lbw_detector_properties.py")
print("  python -m pytest tests/test_lbw_detector_properties.py -v")
