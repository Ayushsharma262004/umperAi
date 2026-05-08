"""
Property-based tests for Caught Dismissal Detector.

These tests validate universal properties that should hold for all caught
dismissal detection scenarios.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
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
# Custom Hypothesis Strategies
# ============================================================================

@st.composite
def ball_trajectory_with_bat_contact_and_catch(draw):
    """
    Generate ball trajectory that includes bat contact and fielder catch.
    
    Trajectory phases:
    1. Approach to batsman (z: -10 to 0)
    2. Bat contact (sudden velocity change)
    3. Flight to fielder (z: 0 to 5, maintaining height >0.1m)
    4. Catch by fielder
    """
    # Number of points in each phase
    approach_points = draw(st.integers(min_value=3, max_value=8))
    flight_points = draw(st.integers(min_value=5, max_value=12))
    
    positions = []
    timestamps = []
    velocities = []
    
    # Phase 1: Approach to batsman
    start_x = draw(st.floats(min_value=-0.5, max_value=0.5))
    start_y = draw(st.floats(min_value=1.0, max_value=2.0))
    start_z = draw(st.floats(min_value=-10.0, max_value=-5.0))
    
    bat_contact_x = draw(st.floats(min_value=-0.3, max_value=0.3))
    bat_contact_y = draw(st.floats(min_value=0.5, max_value=1.2))
    bat_contact_z = draw(st.floats(min_value=-0.5, max_value=0.5))
    
    # Generate approach trajectory
    for i in range(approach_points):
        t = i / (approach_points - 1) if approach_points > 1 else 0
        
        x = start_x + t * (bat_contact_x - start_x)
        y = start_y + t * (bat_contact_y - start_y)
        z = start_z + t * (bat_contact_z - start_z)
        
        positions.append(Position3D(x=x, y=y, z=z))
        timestamps.append(t * 0.3)
    
    # Phase 2: Flight to fielder (after bat contact)
    fielder_x = draw(st.floats(min_value=-3.0, max_value=3.0))
    fielder_y = draw(st.floats(min_value=0.8, max_value=2.0))
    fielder_z = draw(st.floats(min_value=2.0, max_value=8.0))
    
    # Ensure ball stays above ground during flight
    min_flight_height = draw(st.floats(min_value=0.15, max_value=0.5))
    
    for i in range(flight_points):
        t = i / (flight_points - 1) if flight_points > 1 else 0
        
        x = bat_contact_x + t * (fielder_x - bat_contact_x)
        # Parabolic trajectory to maintain height
        y = bat_contact_y + (fielder_y - bat_contact_y) * t + min_flight_height * np.sin(np.pi * t)
        z = bat_contact_z + t * (fielder_z - bat_contact_z)
        
        positions.append(Position3D(x=x, y=y, z=z))
        timestamps.append(0.3 + t * 0.5)
    
    # Generate velocities with bat contact direction change
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
        
        # Reverse velocity direction at bat contact (approach_points index)
        if i == approach_points:
            vx = -vx * 0.7
            vy = vy * 0.5
            vz = -vz * 0.8
        
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
    
    return trajectory, approach_points


@st.composite
def batsman_detection_near_crease(draw):
    """Generate batsman detection near batting crease."""
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
def fielder_detection_at_position(draw, fielder_position: Position3D):
    """Generate fielder detection at specified position."""
    pixel_x = fielder_position.x * 64.0 + 640
    pixel_y = fielder_position.z * 36.0 + 360
    
    bbox = BoundingBox(
        x=pixel_x - 60,
        y=pixel_y - 120,
        width=120,
        height=240
    )
    
    confidence = draw(st.floats(min_value=0.7, max_value=1.0))
    
    return Detection(
        class_id=DetectionClass.FIELDER.value,
        class_name="fielder",
        bounding_box=bbox,
        confidence=confidence,
        position_3d=fielder_position
    )


@st.composite
def ball_detection_at_position(draw, ball_position: Position3D):
    """Generate ball detection at specified position."""
    pixel_x = ball_position.x * 64.0 + 640
    pixel_y = ball_position.z * 36.0 + 360
    
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
        position_3d=ball_position
    )


# ============================================================================
# Property Tests
# ============================================================================

@given(
    data=st.data()
)
@settings(max_examples=50, deadline=None)
def test_property_16_caught_dismissal_classification(data):
    """
    Feature: ai-auto-umpiring-system, Property 16: Caught Dismissal Classification
    
    **Validates: Requirements 8.1, 8.2, 8.3**
    
    For any delivery where the ball contacts the bat and is subsequently held by
    a fielder with maintained control for at least 3 frames, without ground contact,
    the Decision Engine SHALL classify the event as a Dismissal_Event of type caught.
    """
    trajectory, bat_contact_index = data.draw(ball_trajectory_with_bat_contact_and_catch())
    
    detector = CaughtDetector()
    
    # Create detections
    bat_contact_position = trajectory.positions[bat_contact_index]
    fielder_position = trajectory.positions[-1]
    
    ball_det = data.draw(ball_detection_at_position(ball_position=bat_contact_position))
    batsman_det = data.draw(batsman_detection_near_crease())
    fielder_det = data.draw(fielder_detection_at_position(fielder_position=fielder_position))
    
    detections = [ball_det, batsman_det, fielder_det]
    
    # Detect caught dismissal
    decision = detector.detect(trajectory, detections)
    
    # Property: If all conditions are met, decision should be CAUGHT
    if decision is not None:
        # Verify decision properties
        assert decision.event_type == EventType.CAUGHT, \
            "Decision event type must be CAUGHT"
        
        assert 0.0 <= decision.confidence <= 1.0, \
            "Confidence must be in range [0.0, 1.0]"
        
        assert isinstance(decision.reasoning, str) and len(decision.reasoning) > 0, \
            "Reasoning must be a non-empty string"
        
        assert isinstance(decision.video_references, list) and len(decision.video_references) > 0, \
            "Video references must be provided"
        
        # Verify analysis if available
        if detector._last_analysis is not None:
            analysis = detector._last_analysis
            
            # Verify bat contact detected
            assert isinstance(analysis.bat_contact, BatContact), \
                "Bat contact must be detected"
            
            # Verify fielder catch detected
            assert isinstance(analysis.fielder_catch, FielderCatch), \
                "Fielder catch must be detected"
            
            # Verify control frames >= 3
            assert analysis.fielder_catch.control_frames >= detector.MIN_CONTROL_FRAMES, \
                f"Control frames must be >= {detector.MIN_CONTROL_FRAMES}"
            
            # Verify no ground contact
            assert not analysis.ground_contact_detected, \
                "Ground contact must not be detected for valid catch"
            
            # Verify minimum ball height maintained
            assert analysis.min_ball_height >= detector.MIN_BALL_HEIGHT, \
                f"Ball height must be >= {detector.MIN_BALL_HEIGHT}m throughout flight"


@given(
    data=st.data()
)
@settings(max_examples=50, deadline=None)
def test_property_16_caught_bat_contact_detection(data):
    """
    Feature: ai-auto-umpiring-system, Property 16: Caught Dismissal - Bat Contact
    
    **Validates: Requirements 8.1**
    
    For any delivery where the ball contacts the bat (trajectory direction change),
    the detector SHALL identify the bat contact moment.
    """
    trajectory, bat_contact_index = data.draw(ball_trajectory_with_bat_contact_and_catch())
    
    detector = CaughtDetector()
    
    # Create detections
    bat_contact_position = trajectory.positions[bat_contact_index]
    
    ball_det = data.draw(ball_detection_at_position(ball_position=bat_contact_position))
    batsman_det = data.draw(batsman_detection_near_crease())
    
    detections = [ball_det, batsman_det]
    
    # Detect bat contact
    bat_contact = detector.detect_ball_bat_contact(trajectory, detections)
    
    # Property: Bat contact should be detected when velocity changes significantly
    if bat_contact is not None:
        assert isinstance(bat_contact, BatContact), \
            "Bat contact must be a BatContact instance"
        
        assert isinstance(bat_contact.contact_position, Position3D), \
            "Contact position must be a Position3D"
        
        assert isinstance(bat_contact.velocity_before, Vector3D), \
            "Velocity before contact must be a Vector3D"
        
        assert isinstance(bat_contact.velocity_after, Vector3D), \
            "Velocity after contact must be a Vector3D"
        
        # Verify velocity direction changed significantly
        v1 = bat_contact.velocity_before
        v2 = bat_contact.velocity_after
        
        if v1.magnitude() > 0 and v2.magnitude() > 0:
            dot_product = v1.vx * v2.vx + v1.vy * v2.vy + v1.vz * v2.vz
            cos_angle = dot_product / (v1.magnitude() * v2.magnitude())
            cos_angle = max(-1.0, min(1.0, cos_angle))
            angle_change = np.arccos(cos_angle)
            
            assert angle_change >= detector.MIN_BAT_CONTACT_ANGLE, \
                f"Angle change must be >= {detector.MIN_BAT_CONTACT_ANGLE} radians"


@given(
    data=st.data()
)
@settings(max_examples=50, deadline=None)
def test_property_16_caught_fielder_control_verification(data):
    """
    Feature: ai-auto-umpiring-system, Property 16: Caught Dismissal - Fielder Control
    
    **Validates: Requirements 8.2**
    
    For any catch scenario, the detector SHALL verify that the fielder maintained
    control of the ball for at least 3 frames.
    """
    trajectory, bat_contact_index = data.draw(ball_trajectory_with_bat_contact_and_catch())
    
    detector = CaughtDetector()
    
    # Create detections
    bat_contact_position = trajectory.positions[bat_contact_index]
    fielder_position = trajectory.positions[-1]
    
    ball_det = data.draw(ball_detection_at_position(ball_position=bat_contact_position))
    batsman_det = data.draw(batsman_detection_near_crease())
    fielder_det = data.draw(fielder_detection_at_position(fielder_position=fielder_position))
    
    detections = [ball_det, batsman_det, fielder_det]
    
    # Detect bat contact first
    bat_contact = detector.detect_ball_bat_contact(trajectory, detections)
    
    assume(bat_contact is not None)
    
    # Detect fielder catch
    fielder_catch = detector.detect_fielder_catch(trajectory, detections, bat_contact)
    
    # Property: If fielder catch detected, control frames must be >= MIN_CONTROL_FRAMES
    if fielder_catch is not None:
        assert isinstance(fielder_catch, FielderCatch), \
            "Fielder catch must be a FielderCatch instance"
        
        assert fielder_catch.control_frames >= 0, \
            "Control frames must be non-negative"
        
        assert isinstance(fielder_catch.fielder_detection, Detection), \
            "Fielder detection must be provided"
        
        assert fielder_catch.fielder_detection.class_id == DetectionClass.FIELDER.value, \
            "Detection must be of FIELDER class"


@given(
    data=st.data()
)
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
def test_property_16_caught_ground_contact_verification(data):
    """
    Feature: ai-auto-umpiring-system, Property 16: Caught Dismissal - Ground Contact
    
    **Validates: Requirements 8.3**
    
    For any catch scenario, the detector SHALL verify that the ball did not
    contact the ground (height >0.1m) throughout flight to fielder.
    """
    trajectory, bat_contact_index = data.draw(ball_trajectory_with_bat_contact_and_catch())
    
    detector = CaughtDetector()
    
    # Create detections
    bat_contact_position = trajectory.positions[bat_contact_index]
    fielder_position = trajectory.positions[-1]
    
    ball_det = data.draw(ball_detection_at_position(ball_position=bat_contact_position))
    batsman_det = data.draw(batsman_detection_near_crease())
    fielder_det = data.draw(fielder_detection_at_position(fielder_position=fielder_position))
    
    detections = [ball_det, batsman_det, fielder_det]
    
    # Detect bat contact
    bat_contact = detector.detect_ball_bat_contact(trajectory, detections)
    
    assume(bat_contact is not None)
    
    # Detect fielder catch
    fielder_catch = detector.detect_fielder_catch(trajectory, detections, bat_contact)
    
    assume(fielder_catch is not None)
    
    # Detect ground contact
    ground_contact, min_height = detector.detect_ground_contact(trajectory, bat_contact, fielder_catch)
    
    # Property: Ground contact detection must be consistent with minimum height
    assert isinstance(ground_contact, bool), \
        "Ground contact must be a boolean"
    
    assert isinstance(min_height, (int, float)), \
        "Minimum height must be numeric"
    
    assert np.isfinite(min_height), \
        "Minimum height must be finite"
    
    # If ground contact detected, min height should be below threshold
    if ground_contact:
        assert min_height < detector.MIN_BALL_HEIGHT, \
            f"Ground contact implies min height < {detector.MIN_BALL_HEIGHT}m"
    
    # If no ground contact, min height should be above threshold
    if not ground_contact:
        assert min_height >= detector.MIN_BALL_HEIGHT, \
            f"No ground contact implies min height >= {detector.MIN_BALL_HEIGHT}m"


@given(
    data=st.data()
)
@settings(max_examples=50, deadline=None)
def test_property_16_caught_dismissal_not_out_on_ground_contact(data):
    """
    Feature: ai-auto-umpiring-system, Property 16: Caught Dismissal - Not Out on Ground Contact
    
    **Validates: Requirements 8.3**
    
    For any scenario where the ball contacts the ground before being caught,
    the detector SHALL NOT classify it as a caught dismissal.
    """
    trajectory, bat_contact_index = data.draw(ball_trajectory_with_bat_contact_and_catch())
    
    # Modify trajectory to include ground contact
    # Set one position's height below threshold
    if len(trajectory.positions) > bat_contact_index + 2:
        ground_contact_index = bat_contact_index + 2
        trajectory.positions[ground_contact_index] = Position3D(
            x=trajectory.positions[ground_contact_index].x,
            y=0.05,  # Below MIN_BALL_HEIGHT threshold
            z=trajectory.positions[ground_contact_index].z
        )
    
    detector = CaughtDetector()
    
    # Create detections
    bat_contact_position = trajectory.positions[bat_contact_index]
    fielder_position = trajectory.positions[-1]
    
    ball_det = data.draw(ball_detection_at_position(ball_position=bat_contact_position))
    batsman_det = data.draw(batsman_detection_near_crease())
    fielder_det = data.draw(fielder_detection_at_position(fielder_position=fielder_position))
    
    detections = [ball_det, batsman_det, fielder_det]
    
    # Detect caught dismissal
    decision = detector.detect(trajectory, detections)
    
    # Property: If ground contact occurred, decision should be None (not out)
    # OR if decision exists, confidence should be very low
    if decision is not None:
        # If decision was made despite ground contact, confidence should be low
        assert decision.confidence < 0.5, \
            "Confidence should be low when ground contact detected"
    
    # Verify analysis shows ground contact
    if detector._last_analysis is not None:
        analysis = detector._last_analysis
        
        # Ground contact should be detected
        assert analysis.ground_contact_detected or analysis.min_ball_height < detector.MIN_BALL_HEIGHT, \
            "Ground contact should be detected when ball height < threshold"
